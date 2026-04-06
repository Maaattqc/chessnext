#!/usr/bin/env python3
"""
Phase 0, Step 2: Find disagreement positions between strong and weak Lc0 networks.

Generates 10,000 random positions, runs both networks, identifies positions
where the two networks disagree on the best move. Captures the strong
network's hidden activations at those positions for concept extraction.

Usage:
    .venv/Scripts/python.exe find_disagreements.py
"""

import os
import random
import sys
import time

import chess
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(__file__))
from leela_net import (load_network, board_to_planes, get_top_moves,
                        LeelaNet)

TOOLS = os.path.dirname(__file__)
STRONG_PATH = os.path.join(TOOLS, "networks", "t60-24x320.pb.gz")
WEAK_PATH = os.path.join(TOOLS, "networks", "weak-256x20.pb.gz")
NUM_POSITIONS = 10_000
BATCH_SIZE = 64


# ---------------------------------------------------------------------------
# Position generation
# ---------------------------------------------------------------------------

def generate_positions(n: int, seed: int = 42):
    """Generate n diverse mid-game positions via random play."""
    rng = random.Random(seed)
    positions = []
    seen = set()

    while len(positions) < n:
        board = chess.Board()
        depth = rng.randint(8, 60)
        for _ in range(depth):
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(rng.choice(moves))

        if board.is_game_over():
            continue
        fen = board.fen()
        if fen in seen:
            continue
        # Skip trivial positions (< 4 legal moves)
        if len(list(board.legal_moves)) < 4:
            continue
        seen.add(fen)
        positions.append((fen, board.copy()))

    return positions[:n]


# ---------------------------------------------------------------------------
# Batched inference
# ---------------------------------------------------------------------------

def encode_batch(positions, device, dtype):
    """Encode a list of (fen, board) into a batched tensor."""
    planes = [board_to_planes(b) for _, b in positions]
    return torch.from_numpy(np.stack(planes)).to(device=device, dtype=dtype)


def run_batched(model, positions, device, batch_size, capture_blocks=False):
    """Run model on all positions in batches. Returns policies, values,
    and optionally block activations."""
    dtype = next(model.parameters()).dtype
    all_pol, all_val = [], []
    all_acts = [] if capture_blocks else None

    # Set up hooks if capturing
    hooks = []
    captured = {}
    if capture_blocks:
        for i, blk in enumerate(model.blocks):
            name = f"block_{i}"
            def make_hook(n):
                def fn(_, __, out):
                    captured[n] = out.detach().float().cpu()
                return fn
            hooks.append(blk.register_forward_hook(make_hook(name)))

    with torch.no_grad():
        for start in range(0, len(positions), batch_size):
            batch = positions[start:start + batch_size]
            x = encode_batch(batch, device, dtype)
            pol, val = model(x)
            all_pol.append(pol.float().cpu().numpy())
            all_val.append(val.float().cpu().numpy().flatten())

            if capture_blocks:
                block_acts = np.concatenate(
                    [captured[f"block_{i}"].numpy().reshape(len(batch), -1)
                     for i in range(model.n_blocks)],
                    axis=1)
                all_acts.append(block_acts)
                captured.clear()

    for h in hooks:
        h.remove()

    policies = np.concatenate(all_pol, axis=0)
    values = np.concatenate(all_val, axis=0)
    acts = np.concatenate(all_acts, axis=0) if capture_blocks else None
    return policies, values, acts


# ---------------------------------------------------------------------------
# Disagreement detection
# ---------------------------------------------------------------------------

def find_disagreements(strong_pol, weak_pol, positions, min_prob_gap=0.05):
    """Find positions where strong and weak networks pick different top moves.

    Returns indices of disagreement positions and metadata.
    """
    disagree_idx = []
    disagree_info = []

    for i, (fen, board) in enumerate(positions):
        strong_moves = get_top_moves(strong_pol[i], board, k=3)
        weak_moves = get_top_moves(weak_pol[i], board, k=3)

        if not strong_moves or not weak_moves:
            continue

        strong_best = strong_moves[0][0]
        weak_best = weak_moves[0][0]

        if strong_best != weak_best:
            # Quality filter: strong net should be confident
            strong_prob = strong_moves[0][1]
            if strong_prob >= min_prob_gap:
                disagree_idx.append(i)
                disagree_info.append({
                    "fen": fen,
                    "strong_move": strong_best.uci(),
                    "weak_move": weak_best.uci(),
                    "strong_prob": strong_prob,
                    "weak_prob": weak_moves[0][1],
                })

    return disagree_idx, disagree_info


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load both networks
    print("\nLoading strong network (T60 SE)...")
    t0 = time.time()
    strong, nb_s, nf_s, se_s = load_network(STRONG_PATH)
    strong = strong.to(device).eval().half()
    print(f"  {nb_s}x{nf_s} SE={se_s}  ({time.time()-t0:.1f}s)")

    print("Loading weak network (classical)...")
    t0 = time.time()
    weak, nb_w, nf_w, se_w = load_network(WEAK_PATH)
    weak = weak.to(device).eval().half()
    print(f"  {nb_w}x{nf_w} SE={se_w}  ({time.time()-t0:.1f}s)")

    # Generate positions
    print(f"\nGenerating {NUM_POSITIONS:,} positions...")
    t0 = time.time()
    positions = generate_positions(NUM_POSITIONS)
    print(f"  {len(positions):,} positions in {time.time()-t0:.1f}s")

    # Run weak network (policy only, no activations needed)
    print("\nRunning weak network...")
    t0 = time.time()
    weak_pol, weak_val, _ = run_batched(weak, positions, device, BATCH_SIZE)
    print(f"  Done in {time.time()-t0:.1f}s  "
          f"({len(positions)/(time.time()-t0):.0f} pos/s)")

    # Free weak network VRAM
    del weak
    torch.cuda.empty_cache()

    # Run strong network (policy only first pass)
    print("Running strong network...")
    t0 = time.time()
    strong_pol, strong_val, _ = run_batched(
        strong, positions, device, BATCH_SIZE)
    print(f"  Done in {time.time()-t0:.1f}s  "
          f"({len(positions)/(time.time()-t0):.0f} pos/s)")

    # Find disagreements
    print("\nFinding disagreements...")
    disagree_idx, disagree_info = find_disagreements(
        strong_pol, weak_pol, positions)
    n_dis = len(disagree_idx)
    print(f"  {n_dis} disagreements out of {len(positions)} "
          f"({100*n_dis/len(positions):.1f}%)")

    if n_dis == 0:
        print("No disagreements found. Try lowering min_prob_gap or "
              "using more positions.")
        return

    # Show some examples
    print("\n  Sample disagreements:")
    for info in disagree_info[:10]:
        print(f"    {info['fen'][:50]}...")
        print(f"      strong={info['strong_move']} ({info['strong_prob']:.1%})  "
              f"weak={info['weak_move']} ({info['weak_prob']:.1%})")

    # Second pass: capture strong-net activations only at disagreement positions
    print(f"\nCapturing activations for {n_dis} disagreement positions...")
    dis_positions = [positions[i] for i in disagree_idx]
    t0 = time.time()
    _, dis_values, dis_acts = run_batched(
        strong, dis_positions, device, BATCH_SIZE, capture_blocks=True)
    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"  Activation matrix: {dis_acts.shape}  "
          f"({dis_acts.nbytes / 1024 / 1024:.1f} MB)")

    # Also capture strong policy at disagreement positions
    dis_strong_pol = strong_pol[disagree_idx]

    # Save everything
    out_path = os.path.join(TOOLS, "disagreements.npz")
    fens = np.array([info["fen"] for info in disagree_info])
    strong_moves = np.array([info["strong_move"] for info in disagree_info])
    weak_moves = np.array([info["weak_move"] for info in disagree_info])

    np.savez_compressed(out_path,
                        fens=fens,
                        strong_moves=strong_moves,
                        weak_moves=weak_moves,
                        activations=dis_acts,
                        values=dis_values,
                        strong_policies=dis_strong_pol)
    mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\nSaved -> {out_path}  ({mb:.1f} MB)")
    print(f"  {n_dis} disagreement positions with activations")

    # Value comparison
    all_strong_vals = strong_val
    dis_strong_vals = dis_values
    print(f"\n  Strong net values (all):          "
          f"mean={all_strong_vals.mean():.3f}  std={all_strong_vals.std():.3f}")
    print(f"  Strong net values (disagreements): "
          f"mean={dis_strong_vals.mean():.3f}  std={dis_strong_vals.std():.3f}")

    print(f"\nPhase 0 step 2 complete. Ready for concept extraction.")


if __name__ == "__main__":
    main()
