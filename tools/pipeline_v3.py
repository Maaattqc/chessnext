#!/usr/bin/env python3
"""
Concept Extraction Pipeline v3 — Multi-depth rollouts (DeepMind Eq. 5).

Changes from v2:
- Multi-depth rollouts (5 plies): play top-1 moves for both networks,
  compare activations at EACH depth → multiple constraints per concept
- Full spatial activations (65,536 dims) instead of pooled 1024
- This captures "WHY" the strong move is better, not just the immediate effect

Method (DeepMind Eq. 5):
  min ||v||_1
  s.t. v^T z_t+ >= v^T z_t-  for all t = 1..T

Where z_t+ = activation after t plies of the optimal (strong) line
      z_t- = activation after t plies of the suboptimal (weak) line
"""

import os
import sys
import time

import chess
import cvxpy as cp
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(__file__))
from leela_transformer import load_transformer
from leela_net import board_to_planes

TOOLS = os.path.dirname(__file__)
STRONG_PATH = os.path.join(TOOLS, "networks", "strong-912627.pb.gz")
WEAK_PATH = os.path.join(TOOLS, "networks", "weak-910127.pb.gz")
POLICY_MAP = np.load(os.path.join(TOOLS, "attn_policy_map.npy"))
POSITIONS_PATH = os.path.join(TOOLS, "positions_50k.npz")

BATCH_SIZE = 64
ROLLOUT_DEPTH = 5  # Play 5 plies for each line
ACT_DIM = 1024     # Pooled for LP speed (65K makes LP too slow for 5 constraints)


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


def run_inference(model, fens, device, batch_size):
    """Return policy (N, 1858) and pooled activations (N, ACT_DIM)."""
    dtype = next(model.parameters()).dtype
    all_pol, all_acts = [], []
    captured = {}

    def hook(_, __, out):
        captured["last"] = out.detach().float().cpu()
    handle = model.encoders[model.n_enc - 1].register_forward_hook(hook)

    with torch.no_grad():
        for start in range(0, len(fens), batch_size):
            batch = fens[start:start + batch_size]
            planes = [board_to_planes(chess.Board(f)) for f in batch]
            x = torch.from_numpy(np.stack(planes)).to(device=device, dtype=dtype)
            pol, _ = model(x)
            all_pol.append(pol.float().cpu().numpy())
            B = len(batch)
            act = captured["last"].numpy().reshape(B, 64, 1024)
            all_acts.append(act.mean(axis=1))  # (B, 1024) pooled
            captured.clear()

    handle.remove()
    return np.concatenate(all_pol), np.concatenate(all_acts)


def get_activation(model, fen, device):
    """Get pooled activation for a single position."""
    _, acts = run_inference(model, [fen], device, 1)
    return acts[0]


def get_top_move(model, fen, device):
    """Get the best legal policy move. Tries top-10 candidates."""
    pol, _ = run_inference(model, [fen], device, 1)
    board = chess.Board(fen)
    ranked = np.argsort(pol[0])[::-1]

    for idx in ranked[:10]:
        move = policy_idx_to_move(int(idx), board)
        if move is not None:
            return move
    return None


def play_rollout(model, start_fen, depth, device):
    """Play `depth` plies using top-1 policy moves.
    Returns list of (fen, activation) at each step, and the line of moves."""
    board = chess.Board(start_fen)
    steps = []
    moves = []

    for t in range(depth):
        if board.is_game_over() or len(list(board.legal_moves)) == 0:
            break

        fen = board.fen()
        act = get_activation(model, fen, device)

        move = get_top_move(model, fen, device)
        if move is None or move not in board.legal_moves:
            break

        steps.append((fen, act))
        moves.append(board.san(move))
        board.push(move)

    # Final position activation
    if not board.is_game_over():
        steps.append((board.fen(), get_activation(model, board.fen(), device)))

    return steps, moves


def extract_concept_multidepth(z_optimal_steps, z_suboptimal_steps):
    """L1-minimization with constraints at EACH depth (DeepMind Eq. 5).

    min ||v||_1
    s.t. v^T z_t+ >= v^T z_t- + margin   for all t
    """
    # Use the minimum depth available
    T = min(len(z_optimal_steps), len(z_suboptimal_steps))
    if T < 2:
        return None  # Need at least 2 depths for meaningful concept

    d = z_optimal_steps[0].shape[0]
    v = cp.Variable(d)
    margin = 0.01

    constraints = []
    for t in range(T):
        constraints.append(v @ z_optimal_steps[t] >= v @ z_suboptimal_steps[t] + margin)

    objective = cp.Minimize(cp.norm1(v))
    prob = cp.Problem(objective, constraints)

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


def policy_idx_to_move(idx, board):
    """Convert policy index to chess.Move, handling board orientation."""
    attn = POLICY_MAP[idx]
    flip = board.turn == chess.BLACK  # Policy is from side-to-move perspective

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


def find_disagreements(strong_pol, weak_pol, fens):
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
            s_move = policy_idx_to_move(s_top, board)
            w_move = policy_idx_to_move(w_top, board)
            if s_move is None or w_move is None:
                continue
            results.append({
                "idx": i, "fen": fens[i],
                "s_move": s_move, "w_move": w_move,
                "s_san": board.san(s_move), "w_san": board.san(w_move),
            })
        except Exception:
            continue
    return results


def teachability(concept_vectors, all_acts, strong_pol):
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


def group_concepts(vectors, threshold=0.6):
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


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    t_start = time.time()

    # 1. Load
    print("\n[1/6] Loading positions...")
    fens = load_positions(10000)
    print(f"  {len(fens)} positions")

    # 2. Networks
    print("\n[2/6] Loading networks...")
    strong, n_enc, embed = load_transformer(STRONG_PATH)
    strong.policy_map = POLICY_MAP.tolist()
    strong = strong.to(device).eval().half()

    weak, _, _ = load_transformer(WEAK_PATH)
    weak.policy_map = POLICY_MAP.tolist()
    weak = weak.to(device).eval().half()

    t0 = time.time()
    weak_pol, _ = run_inference(weak, fens, device, BATCH_SIZE)
    print(f"  Weak: {time.time()-t0:.0f}s")

    t0 = time.time()
    strong_pol, strong_acts = run_inference(strong, fens, device, BATCH_SIZE)
    print(f"  Strong: {time.time()-t0:.0f}s")

    # 3. Disagreements
    print("\n[3/6] Finding disagreements...")
    disagreements = find_disagreements(strong_pol, weak_pol, fens)
    print(f"  {len(disagreements)} quiet disagreements")

    if len(disagreements) < 10:
        print("ERROR: Too few.")
        return

    # Limit to 200 for speed (rollouts are expensive: 5 inferences per position per network)
    if len(disagreements) > 200:
        np.random.RandomState(42).shuffle(disagreements)
        disagreements = disagreements[:200]
        print(f"  Sampled 200 for rollout analysis")

    # 4. Multi-depth rollouts + L1
    print(f"\n[4/6] Multi-depth rollouts (depth={ROLLOUT_DEPTH}) + L1-minimization...")
    vectors, positions = [], []
    n_ok, n_fail, n_short = 0, 0, 0

    for i, dis in enumerate(disagreements):
        fen = dis["fen"]
        board = chess.Board(fen)

        # Play strong line: strong's first move, then STRONG continues
        board_s = board.copy()
        board_s.push(dis["s_move"])
        strong_steps, strong_line = play_rollout(strong, board_s.fen(), ROLLOUT_DEPTH - 1, device)

        # Play weak line: weak's first move, then STRONG continues
        # (same network for continuation — isolates the effect of the first move)
        board_w = board.copy()
        board_w.push(dis["w_move"])
        weak_steps, weak_line = play_rollout(strong, board_w.fen(), ROLLOUT_DEPTH - 1, device)

        # Need at least 2 steps for multi-depth constraint
        if len(strong_steps) < 2 or len(weak_steps) < 2:
            n_short += 1
            continue

        z_opt = [s[1] for s in strong_steps]
        z_sub = [s[1] for s in weak_steps]

        v = extract_concept_multidepth(z_opt, z_sub)
        if v is not None:
            vectors.append(v)
            positions.append({
                **dis,
                "strong_line": [dis["s_san"]] + strong_line,
                "weak_line": [dis["w_san"]] + weak_line,
                "depth": min(len(z_opt), len(z_sub)),
            })
            n_ok += 1
        else:
            n_fail += 1

        if (i + 1) % 25 == 0:
            print(f"    {i+1}/{len(disagreements)}: {n_ok} ok, {n_fail} fail, {n_short} short")

    print(f"  {n_ok} concepts, {n_fail} infeasible, {n_short} too short")

    if n_ok == 0:
        print("ERROR: No concepts.")
        return

    vectors = np.array(vectors)

    # 5. Teachability
    print(f"\n[5/6] Teachability...")
    teach = teachability(vectors, strong_acts, strong_pol)
    teach_mask = teach > 0.02
    print(f"  {int(teach_mask.sum())}/{len(vectors)} teachable")

    # 6. Group
    surv_idx = np.where(teach_mask)[0]
    surv_vec = vectors[surv_idx]
    surv_pos = [positions[j] for j in surv_idx]
    surv_teach = teach[surv_idx]

    if len(surv_vec) > 0:
        groups = group_concepts(surv_vec, 0.5)
    else:
        groups = []

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  CONCEPT REPORT v3 (multi-depth rollouts)")
    print(f"{sep}")
    print(f"  Positions:     {len(fens)}")
    print(f"  Disagreements: {len(disagreements)}")
    print(f"  Rollout depth: {ROLLOUT_DEPTH}")
    print(f"  Concepts:      {n_ok}")
    print(f"  Teachable:     {int(teach_mask.sum())}")
    print(f"  Groups:        {len(groups)}")
    print(f"  Time:          {time.time()-t_start:.0f}s")

    for gi, group in enumerate(groups[:15]):
        rep = surv_pos[group[0]]
        print(f"\n  Concept {gi+1} ({len(group)} positions, depth={rep['depth']})")
        print(f"    FEN:         {rep['fen'][:55]}...")
        print(f"    Strong line: {' '.join(rep['strong_line'])}")
        print(f"    Weak line:   {' '.join(rep['weak_line'])}")
        print(f"    Teach:       {surv_teach[group[0]]:.3f}")

    # Save
    import json
    out = os.path.join(TOOLS, "concepts_v3.npz")
    np.savez_compressed(out, vectors=vectors, teach=teach, teach_mask=teach_mask)

    out_json = os.path.join(TOOLS, "concepts_v3_positions.json")
    with open(out_json, "w") as f:
        json.dump([{
            "fen": p["fen"], "s_san": p["s_san"], "w_san": p["w_san"],
            "strong_line": p["strong_line"], "weak_line": p["weak_line"],
            "depth": p["depth"], "teach": float(teach[i]),
        } for i, p in enumerate(positions)], f, indent=2)

    print(f"\n  Saved -> {out}, {out_json}")

    if len(groups) >= 3:
        print(f"\n  >>> {len(groups)} concept groups found. <<<")
    else:
        print(f"\n  >>> {len(groups)} groups. May need more data. <<<")


if __name__ == "__main__":
    main()
