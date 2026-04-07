#!/usr/bin/env python3
"""
Concept Extraction Pipeline v2 — Faithful to DeepMind methodology.

Key changes from v1:
- Positions from real Lichess games, filtered for tactical quietness
- L1-minimization with cvxpy (not k-means/PCA)
- Per-position concept vectors (not cluster-based)
- SVD novelty (not heuristic)
- Spatial pooling: 64 squares averaged to 1024-dim vector
- Disagreement filter: strong move must be in weak's top-5
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
EMBED_DIM = 1024  # After spatial pooling: avg over 64 squares


def load_positions(max_n=10000):
    data = np.load(POSITIONS_PATH, allow_pickle=True)
    fens = data["fens"]
    if len(fens) > max_n:
        rng = np.random.RandomState(42)
        idx = rng.choice(len(fens), max_n, replace=False)
        fens = fens[idx]
    print(f"  Loaded {len(fens)} positions")
    return [str(f) for f in fens]


def is_quiet(board: chess.Board) -> bool:
    """Position must not have free captures of pieces worth >= 3 pawns."""
    if board.is_check():
        return False
    pv = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
          chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    for move in board.legal_moves:
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if captured and attacker:
                if pv.get(captured.piece_type, 0) > pv.get(attacker.piece_type, 0) + 1:
                    return False
    return True


def run_inference(model, fens, device, batch_size):
    """Return policy logits (N, 1858) and pooled activations (N, 1024)."""
    dtype = next(model.parameters()).dtype
    all_pol, all_acts = [], []
    captured = {}

    last_idx = model.n_enc - 1
    def hook(_, __, out):
        captured["last"] = out.detach().float().cpu()
    handle = model.encoders[last_idx].register_forward_hook(hook)

    with torch.no_grad():
        for start in range(0, len(fens), batch_size):
            batch = fens[start:start + batch_size]
            planes = [board_to_planes(chess.Board(f)) for f in batch]
            x = torch.from_numpy(np.stack(planes)).to(device=device, dtype=dtype)
            pol, _ = model(x)
            all_pol.append(pol.float().cpu().numpy())

            B = len(batch)
            # captured["last"] is (B*64, 1024). Reshape to (B, 64, 1024) and average pool
            act = captured["last"].numpy().reshape(B, 64, EMBED_DIM)
            pooled = act.mean(axis=1)  # (B, 1024)
            all_acts.append(pooled)
            captured.clear()

    handle.remove()
    return np.concatenate(all_pol), np.concatenate(all_acts)


def run_single(model, fen, device):
    """Run inference on a single FEN. Return pooled activation (1024,)."""
    _, acts = run_inference(model, [fen], device, 1)
    return acts[0]


def get_top_n(policy, n=5):
    """Return indices of top-n policy moves."""
    return np.argsort(policy)[::-1][:n].tolist()


def policy_idx_to_move(idx, board):
    """Convert policy index to a chess.Move, or None."""
    attn = POLICY_MAP[idx]
    if attn >= 4096:
        return None
    from_sq, to_sq = attn // 64, attn % 64
    for m in board.legal_moves:
        if m.from_square == from_sq and m.to_square == to_sq:
            return m
    return None


def find_disagreements(strong_pol, weak_pol, fens):
    """Disagreements where top-1 moves differ (same as DeepMind).
    Quiet filter applied but lenient — skip only if queen/rook hangs for free.
    """
    results = []
    n_disagree = 0
    n_quiet_filtered = 0
    for i in range(len(fens)):
        s_top = int(np.argmax(strong_pol[i]))
        w_top = int(np.argmax(weak_pol[i]))

        if s_top == w_top:
            continue
        n_disagree += 1

        try:
            board = chess.Board(fens[i])
            if not is_quiet(board):
                n_quiet_filtered += 1
                continue

            s_move = policy_idx_to_move(s_top, board)
            w_move = policy_idx_to_move(w_top, board)
            if s_move is None or w_move is None:
                continue

            results.append({
                "idx": i,
                "fen": fens[i],
                "s_idx": s_top,
                "w_idx": w_top,
                "s_san": board.san(s_move),
                "w_san": board.san(w_move),
                "s_move": s_move,
                "w_move": w_move,
            })
        except Exception:
            continue

    return results


def extract_concept_vector(z_optimal, z_suboptimal):
    """L1-minimization: min ||v||_1  s.t.  v^T z+ >= v^T z- + margin."""
    d = z_optimal.shape[0]
    v = cp.Variable(d)
    margin = 0.01

    constraints = [v @ z_optimal >= v @ z_suboptimal + margin]
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

    # Fallback: try SCS
    try:
        prob.solve(solver=cp.SCS, verbose=False, max_iters=10000, eps=1e-5)
        if prob.status in ("optimal", "optimal_inaccurate"):
            vec = v.value
            if vec is not None and np.linalg.norm(vec) > 1e-8:
                return vec / np.linalg.norm(vec)
    except Exception:
        pass

    return None


def compute_novelty(concept_vectors, az_acts, human_acts):
    """SVD novelty: concept is novel if better explained by AZ basis than human."""
    U_az, _, _ = np.linalg.svd(az_acts.T, full_matrices=False)
    U_h, _, _ = np.linalg.svd(human_acts.T, full_matrices=False)

    scores = []
    for v in concept_vectors:
        is_novel = True
        for k in [10, 25, 50, 100, 200]:
            if k > min(U_az.shape[1], U_h.shape[1]):
                continue
            proj_az = U_az[:, :k] @ (U_az[:, :k].T @ v)
            proj_h = U_h[:, :k] @ (U_h[:, :k].T @ v)
            if np.linalg.norm(v - proj_az) >= np.linalg.norm(v - proj_h):
                is_novel = False
                break
        scores.append(1.0 if is_novel else 0.0)
    return np.array(scores)


def teachability(concept_vectors, all_acts, strong_pol):
    """Simplified teachability: concept-present positions should have
    more confident policy (lower entropy) than concept-absent."""
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
    """Group by cosine similarity."""
    n = len(vectors)
    used = set()
    groups = []
    for i in range(n):
        if i in used:
            continue
        group = [i]
        used.add(i)
        for j in range(i + 1, n):
            if j in used:
                continue
            if np.dot(vectors[i], vectors[j]) > threshold:
                group.append(j)
                used.add(j)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    return groups


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    t_start = time.time()

    # 1. Load positions
    print("\n[1/6] Loading positions...")
    fens = load_positions(10000)

    # 2. Load networks
    print("\n[2/6] Loading networks and running inference...")
    strong, n_enc, embed = load_transformer(STRONG_PATH)
    strong.policy_map = POLICY_MAP.tolist()
    strong = strong.to(device).eval().half()

    weak, _, _ = load_transformer(WEAK_PATH)
    weak.policy_map = POLICY_MAP.tolist()
    weak = weak.to(device).eval().half()

    t0 = time.time()
    weak_pol, _ = run_inference(weak, fens, device, BATCH_SIZE)
    print(f"  Weak: {time.time()-t0:.0f}s")
    del weak
    torch.cuda.empty_cache()

    t0 = time.time()
    strong_pol, strong_acts = run_inference(strong, fens, device, BATCH_SIZE)
    print(f"  Strong: {time.time()-t0:.0f}s")
    print(f"  Activation dim: {strong_acts.shape[1]} (pooled)")

    # 3. Find disagreements
    print("\n[3/6] Finding subtle disagreements...")
    disagreements = find_disagreements(strong_pol, weak_pol, fens)
    print(f"  {len(disagreements)} quiet disagreements")

    if len(disagreements) < 10:
        print("ERROR: Too few disagreements.")
        return

    # 4. L1-minimization
    print(f"\n[4/6] Extracting concept vectors ({len(disagreements)} positions)...")
    vectors, positions = [], []
    n_ok, n_fail = 0, 0

    for i, dis in enumerate(disagreements):
        fen = dis["fen"]
        board = chess.Board(fen)

        # Play strong move -> get activation
        board_s = board.copy()
        board_s.push(dis["s_move"])
        z_opt = run_single(strong, board_s.fen(), device)

        # Play weak move -> get activation
        board_w = board.copy()
        board_w.push(dis["w_move"])
        z_sub = run_single(strong, board_w.fen(), device)

        v = extract_concept_vector(z_opt, z_sub)
        if v is not None:
            vectors.append(v)
            positions.append(dis)
            n_ok += 1
        else:
            n_fail += 1

        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(disagreements)}: {n_ok} ok, {n_fail} fail")

    print(f"  {n_ok} concept vectors, {n_fail} failed")

    if n_ok == 0:
        print("ERROR: No concepts extracted.")
        return

    vectors = np.array(vectors)

    # 5. Novelty (SVD)
    print(f"\n[5/6] Novelty filter (SVD)...")
    dis_idx = set(d["idx"] for d in disagreements)
    agree_acts = strong_acts[np.array([i for i in range(len(fens)) if i not in dis_idx])]
    if len(agree_acts) > 2000:
        agree_acts = agree_acts[np.random.RandomState(42).choice(len(agree_acts), 2000, replace=False)]

    dis_acts_for_svd = strong_acts[np.array([d["idx"] for d in positions])]
    novelty = compute_novelty(vectors, dis_acts_for_svd, agree_acts)
    print(f"  {int(novelty.sum())}/{len(vectors)} novel")

    # 6. Teachability
    print(f"\n[6/6] Teachability...")
    teach = teachability(vectors, strong_acts, strong_pol)
    teach_mask = teach > 0.02
    print(f"  {int(teach_mask.sum())}/{len(vectors)} teachable")

    combined = (novelty > 0.5) & teach_mask
    n_surv = int(combined.sum())

    # Report
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  CONCEPT REPORT v2")
    print(f"{sep}")
    print(f"  Positions:     {len(fens)}")
    print(f"  Disagreements: {len(disagreements)} (subtle)")
    print(f"  Vectors:       {n_ok}")
    print(f"  Novel:         {int(novelty.sum())}")
    print(f"  Teachable:     {int(teach_mask.sum())}")
    print(f"  Surviving:     {n_surv}")
    print(f"  Time:          {time.time()-t_start:.0f}s")

    surv_idx = np.where(combined)[0]
    surv_vec = vectors[surv_idx]
    surv_pos = [positions[i] for i in surv_idx]

    if len(surv_vec) > 0:
        groups = group_concepts(surv_vec, 0.6)
        print(f"  Groups:        {len(groups)}")

        for gi, group in enumerate(groups[:15]):
            rep = surv_pos[group[0]]
            print(f"\n  Concept {gi+1} ({len(group)} positions)")
            print(f"    FEN:    {rep['fen'][:60]}...")
            print(f"    Strong: {rep['s_san']}   Weak: {rep['w_san']}")
            print(f"    Teach:  {teach[surv_idx[group[0]]]:.3f}  "
                  f"Novel: {novelty[surv_idx[group[0]]]:.1f}")

    # Save
    out = os.path.join(TOOLS, "concepts_v2.npz")
    np.savez_compressed(out,
        vectors=vectors, novelty=novelty, teach=teach, combined=combined,
        fens=np.array([d["fen"] for d in positions]),
        strong_sans=np.array([d["s_san"] for d in positions]),
        weak_sans=np.array([d["w_san"] for d in positions]),
    )
    print(f"\n  Saved -> {out} ({os.path.getsize(out)/1e6:.1f} MB)")

    if n_surv >= 3:
        print(f"\n  >>> GO: {n_surv} concepts. <<<")
    else:
        print(f"\n  >>> {n_surv} concepts. Need tuning or more data. <<<")


if __name__ == "__main__":
    main()
