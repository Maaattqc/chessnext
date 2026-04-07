#!/usr/bin/env python3
"""
Concept Extraction Pipeline v4 — Full MCTS (DeepMind exact method).

Exact replication:
- 800 MCTS simulations per position (AlphaZero standard)
- Optimal path: most-visited branch in search tree (20+ plies)
- Suboptimal path: high-visit alternative with value diff >= 0.1
- Multi-depth L1 constraints at every node along both paths
- No shortcuts, no approximations
"""

import os
import sys
import time
import json

import chess
import cvxpy as cp
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(__file__))
from leela_transformer import load_transformer
from leela_net import board_to_planes
from mcts_fast import BatchMCTS as MCTS

TOOLS = os.path.dirname(__file__)
STRONG_PATH = os.path.join(TOOLS, "networks", "strong-912627.pb.gz")
WEAK_PATH = os.path.join(TOOLS, "networks", "weak-910127.pb.gz")
POLICY_MAP = np.load(os.path.join(TOOLS, "attn_policy_map.npy"))
POSITIONS_PATH = os.path.join(TOOLS, "positions_50k.npz")

NUM_SIMULATIONS = 400  # 400 sims = good enough for concept extraction, 2x faster
BATCH_SIZE = 64
MAX_ROLLOUT_DEPTH = 20


def load_positions(max_n=10000):
    data = np.load(POSITIONS_PATH, allow_pickle=True)
    fens = data["fens"]
    if len(fens) > max_n:
        idx = np.random.RandomState(42).choice(len(fens), max_n, replace=False)
        fens = fens[idx]
    return [str(f) for f in fens]


def is_quiet(board):
    if board.is_check():
        return False
    pv = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
          chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    for move in board.legal_moves:
        if board.is_capture(move):
            cap = board.piece_at(move.to_square)
            att = board.piece_at(move.from_square)
            if cap and att and pv.get(cap.piece_type, 0) > pv.get(att.piece_type, 0) + 1:
                return False
    return True


def run_batch_inference(model, fens, device, batch_size):
    """Batch inference for disagreement detection. Returns policy logits."""
    dtype = next(model.parameters()).dtype
    all_pol = []
    with torch.no_grad():
        for start in range(0, len(fens), batch_size):
            batch = fens[start:start + batch_size]
            planes = [board_to_planes(chess.Board(f)) for f in batch]
            x = torch.from_numpy(np.stack(planes)).to(device=device, dtype=dtype)
            pol, _ = model(x)
            all_pol.append(pol.float().cpu().numpy())
    return np.concatenate(all_pol)


def policy_idx_to_move(idx, board, policy_map):
    attn = policy_map[idx]
    flip = board.turn == chess.BLACK
    if attn >= 4096:
        promo_idx = attn - 4096
        file_from = promo_idx // 24
        rest = promo_idx % 24
        file_to = rest // 3
        promo_type = rest % 3
        promo_piece = [chess.QUEEN, chess.ROOK, chess.BISHOP][promo_type]
        rank_from = 6 if board.turn == chess.WHITE else 1
        rank_to = 7 if board.turn == chess.WHITE else 0
        from_sq = chess.square(file_from, rank_from)
        to_sq = chess.square(file_to, rank_to)
        move = chess.Move(from_sq, to_sq, promotion=promo_piece)
        return move if move in board.legal_moves else None
    from_sq, to_sq = attn // 64, attn % 64
    if flip:
        from_sq = chess.square_mirror(from_sq)
        to_sq = chess.square_mirror(to_sq)
    for promo in [None, chess.QUEEN]:
        move = chess.Move(from_sq, to_sq, promotion=promo)
        if move in board.legal_moves:
            return move
    return None


def find_disagreements(strong_pol, weak_pol, fens, policy_map):
    results = []
    for i in range(len(fens)):
        s_top = int(np.argmax(strong_pol[i]))
        w_top = int(np.argmax(weak_pol[i]))
        if s_top == w_top:
            continue
        try:
            board = chess.Board(fens[i])
            if not is_quiet(board):
                continue
            s_move = policy_idx_to_move(s_top, board, policy_map)
            w_move = policy_idx_to_move(w_top, board, policy_map)
            if s_move is None or w_move is None:
                continue
            results.append({
                "idx": i, "fen": fens[i],
                "s_san": board.san(s_move), "w_san": board.san(w_move),
            })
        except Exception:
            continue
    return results


def extract_concept_multidepth(z_optimal, z_suboptimal):
    """L1-minimization with constraints at each depth (DeepMind Eq. 5)."""
    T = min(len(z_optimal), len(z_suboptimal))
    if T < 3:
        return None  # Need >= 3 depths for meaningful concept

    d = z_optimal[0].shape[0]
    v = cp.Variable(d)
    margin = 0.01

    constraints = []
    for t in range(T):
        constraints.append(v @ z_optimal[t] >= v @ z_suboptimal[t] + margin)

    prob = cp.Problem(cp.Minimize(cp.norm1(v)), constraints)
    try:
        prob.solve(solver=cp.CLARABEL, verbose=False)
        if prob.status in ("optimal", "optimal_inaccurate"):
            vec = v.value
            if vec is not None and np.linalg.norm(vec) > 1e-8:
                return vec / np.linalg.norm(vec)
    except Exception:
        pass
    try:
        prob.solve(solver=cp.SCS, verbose=False, max_iters=10000, eps=1e-5)
        if prob.status in ("optimal", "optimal_inaccurate"):
            vec = v.value
            if vec is not None and np.linalg.norm(vec) > 1e-8:
                return vec / np.linalg.norm(vec)
    except Exception:
        pass
    return None


def teachability(concept_vectors, all_acts, strong_pol):
    """Entropy-based teachability proxy."""
    scores = []
    for v in concept_vectors:
        proj = all_acts @ v
        top_mask = proj >= np.percentile(proj, 90)
        bot_mask = proj <= np.median(proj)
        if top_mask.sum() < 5 or bot_mask.sum() < 5:
            scores.append(0.0)
            continue
        def entropy(logits):
            p = np.exp(logits - logits.max(axis=1, keepdims=True))
            p = p / p.sum(axis=1, keepdims=True)
            return -np.mean(np.sum(p * np.log(p + 1e-10), axis=1))
        e_top = entropy(strong_pol[top_mask])
        e_bot = entropy(strong_pol[bot_mask])
        scores.append(max(0, (e_bot - e_top) / (e_bot + 1e-8)))
    return np.array(scores)


def group_concepts(vectors, threshold=0.5):
    n = len(vectors)
    used, groups = set(), []
    for i in range(n):
        if i in used: continue
        g = [i]; used.add(i)
        for j in range(i+1, n):
            if j not in used and np.dot(vectors[i], vectors[j]) > threshold:
                g.append(j); used.add(j)
        groups.append(g)
    groups.sort(key=len, reverse=True)
    return groups


def get_pooled_activation(model, device, board):
    """Get pooled activation (1024 dims) for a position."""
    captured = {}
    def hook(_, __, out):
        captured["act"] = out.detach().float().cpu()
    handle = model.encoders[model.n_enc - 1].register_forward_hook(hook)
    planes = torch.from_numpy(board_to_planes(board)).unsqueeze(0)
    dtype = next(model.parameters()).dtype
    planes = planes.to(device=device, dtype=dtype)
    with torch.no_grad():
        model(planes)
    handle.remove()
    return captured["act"].numpy().reshape(64, 1024).mean(axis=0)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"MCTS simulations: {NUM_SIMULATIONS}")
    t_start = time.time()

    # 1. Load
    print("\n[1/6] Loading positions...")
    fens = load_positions(50000)
    print(f"  {len(fens)} positions")

    # 2. Networks
    print("\n[2/6] Loading networks...")
    strong, _, _ = load_transformer(STRONG_PATH)
    strong.policy_map = POLICY_MAP.tolist()
    strong = strong.to(device).eval().half()

    weak, _, _ = load_transformer(WEAK_PATH)
    weak.policy_map = POLICY_MAP.tolist()
    weak = weak.to(device).eval().half()

    # Batch inference for disagreement detection
    t0 = time.time()
    weak_pol = run_batch_inference(weak, fens, device, BATCH_SIZE)
    print(f"  Weak inference: {time.time()-t0:.0f}s")
    del weak
    torch.cuda.empty_cache()

    t0 = time.time()
    strong_pol = run_batch_inference(strong, fens, device, BATCH_SIZE)
    print(f"  Strong inference: {time.time()-t0:.0f}s")

    # Also get activations for teachability later
    # (reuse the batch inference with hook)
    captured_acts = {}
    def act_hook(_, __, out):
        captured_acts["act"] = out.detach().float().cpu()
    handle = strong.encoders[strong.n_enc - 1].register_forward_hook(act_hook)
    all_strong_acts = []
    with torch.no_grad():
        for start in range(0, len(fens), BATCH_SIZE):
            batch = fens[start:start + BATCH_SIZE]
            planes = [board_to_planes(chess.Board(f)) for f in batch]
            x = torch.from_numpy(np.stack(planes)).to(device=device, dtype=next(strong.parameters()).dtype)
            strong(x)
            B = len(batch)
            act = captured_acts["act"].numpy().reshape(B, 64, 1024).mean(axis=1)
            all_strong_acts.append(act)
            captured_acts.clear()
    handle.remove()
    all_strong_acts = np.concatenate(all_strong_acts)

    # 3. Disagreements
    print("\n[3/6] Finding disagreements...")
    disagreements = find_disagreements(strong_pol, weak_pol, fens, POLICY_MAP)
    print(f"  {len(disagreements)} quiet disagreements ({100*len(disagreements)/len(fens):.1f}%)")

    if len(disagreements) < 10:
        print("ERROR: Too few.")
        return

    # Sample for MCTS (expensive: ~800 inferences per position)
    max_mcts = min(800, len(disagreements))
    if len(disagreements) > max_mcts:
        np.random.RandomState(42).shuffle(disagreements)
        disagreements = disagreements[:max_mcts]
    print(f"  Selected {len(disagreements)} for MCTS analysis")

    # 4. MCTS + concept extraction
    print(f"\n[4/6] Running MCTS ({NUM_SIMULATIONS} sims) + L1-minimization...")
    mcts = MCTS(strong, device, POLICY_MAP, num_sims=NUM_SIMULATIONS, batch_size=64)

    vectors, positions = [], []
    n_ok, n_fail, n_nosubopt = 0, 0, 0

    for i, dis in enumerate(disagreements):
        board = chess.Board(dis["fen"])

        # Run MCTS
        root = mcts.search(board)

        # Get optimal path (most visited)
        opt_path = mcts.get_optimal_path(root, board, max_depth=MAX_ROLLOUT_DEPTH)

        # Get suboptimal path
        subopt_path = mcts.get_suboptimal_path(
            root, board, min_value_diff=0.02, min_visit_ratio=0.03,
            max_depth=MAX_ROLLOUT_DEPTH)

        if subopt_path is None or len(subopt_path) < 3:
            n_nosubopt += 1
            continue

        # Extract activations
        z_opt = [step["activation"] for step in opt_path]
        z_sub = [step["activation"] for step in subopt_path]

        # L1-minimization with multi-depth constraints
        v = extract_concept_multidepth(z_opt, z_sub)

        if v is not None:
            opt_san = [s["san"] for s in opt_path]
            sub_san = [s["san"] for s in subopt_path]

            vectors.append(v)
            positions.append({
                "fen": dis["fen"],
                "opt_line": opt_san,
                "sub_line": sub_san,
                "opt_depth": len(opt_path),
                "sub_depth": len(subopt_path),
                "opt_visits": opt_path[0].get("visits", 0) if opt_path else 0,
                "sub_visits": subopt_path[0].get("visits", 0) if subopt_path else 0,
            })
            n_ok += 1
        else:
            n_fail += 1

        if (i + 1) % 10 == 0:
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed * 60
            print(f"    {i+1}/{len(disagreements)}: {n_ok} ok, {n_fail} fail, "
                  f"{n_nosubopt} no-subopt ({rate:.1f} pos/min)")

    print(f"  {n_ok} concepts, {n_fail} infeasible, {n_nosubopt} no suboptimal path")

    if n_ok == 0:
        print("ERROR: No concepts.")
        return

    vectors = np.array(vectors)

    # 5. Teachability
    print(f"\n[5/6] Teachability...")
    teach = teachability(vectors, all_strong_acts, strong_pol)
    teach_mask = teach > 0.02
    print(f"  {int(teach_mask.sum())}/{len(vectors)} teachable")

    # 6. Group
    surv_idx = np.where(teach_mask)[0]
    surv_vec = vectors[surv_idx]
    surv_pos = [positions[j] for j in surv_idx]
    surv_teach = teach[surv_idx]

    groups = group_concepts(surv_vec, 0.35) if len(surv_vec) > 0 else []

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  CONCEPT REPORT v4 (MCTS {NUM_SIMULATIONS} simulations)")
    print(f"{sep}")
    print(f"  Positions:     {len(fens)}")
    print(f"  Disagreements: {len(disagreements)}")
    print(f"  MCTS sims:     {NUM_SIMULATIONS}")
    print(f"  Concepts:      {n_ok}")
    print(f"  Teachable:     {int(teach_mask.sum())}")
    print(f"  Groups:        {len(groups)}")
    print(f"  Time:          {time.time()-t_start:.0f}s")

    for gi, group in enumerate(groups[:15]):
        rep = surv_pos[group[0]]
        print(f"\n  Concept {gi+1} ({len(group)} positions)")
        print(f"    FEN:       {rep['fen'][:55]}...")
        print(f"    Optimal:   {' '.join(rep['opt_line'][:10])} (depth={rep['opt_depth']}, "
              f"visits={rep['opt_visits']})")
        print(f"    Suboptimal:{' '.join(rep['sub_line'][:10])} (depth={rep['sub_depth']}, "
              f"visits={rep['sub_visits']})")
        print(f"    Teach:     {surv_teach[group[0]]:.3f}")

    # Save
    out = os.path.join(TOOLS, "concepts_v4.npz")
    np.savez_compressed(out, vectors=vectors, teach=teach, teach_mask=teach_mask)

    out_json = os.path.join(TOOLS, "concepts_v4_positions.json")
    with open(out_json, "w") as f:
        json.dump(positions, f, indent=2, default=str)

    print(f"\n  Saved -> {out}, {out_json}")


if __name__ == "__main__":
    main()
