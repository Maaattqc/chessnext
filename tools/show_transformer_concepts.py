#!/usr/bin/env python3
"""Show representative positions for each transformer concept."""

import sys
import os
import time
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(__file__))
import chess
from leela_transformer import load_transformer
from leela_net import board_to_planes

TOOLS = os.path.dirname(__file__)
POLICY_MAP = np.load(os.path.join(TOOLS, "attn_policy_map.npy"))


def policy_idx_to_uci(idx, policy_map):
    """Convert policy index to approximate from/to squares."""
    attn_idx = policy_map[idx]
    if attn_idx < 4096:
        from_sq = attn_idx // 64
        to_sq = attn_idx % 64
        return chess.square_name(from_sq) + chess.square_name(to_sq)
    else:
        # Promotion
        promo_idx = attn_idx - 4096
        file_from = promo_idx // 24
        rest = promo_idx % 24
        file_to = rest // 3
        promo_type = rest % 3  # 0=Q, 1=R, 2=B
        promo_char = ['q', 'r', 'b'][promo_type]
        return (chess.square_name(chess.square(file_from, 6)) +
                chess.square_name(chess.square(file_to, 7)) + promo_char)


def get_top_moves(policy_logits, board, k=3):
    """Get top-k moves with probabilities, filtered to legal."""
    probs = np.exp(policy_logits - policy_logits.max())
    probs /= probs.sum()
    ranked = np.argsort(probs)[::-1]
    legal = set(m.uci() for m in board.legal_moves)
    results = []
    for idx in ranked:
        uci = policy_idx_to_uci(int(idx), POLICY_MAP)
        # Try matching to legal moves (exact or with promotion)
        if uci in legal or uci + 'q' in legal:
            results.append((uci if uci in legal else uci + 'q', float(probs[idx])))
        if len(results) >= k:
            break
    return results


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load concepts data
    data = np.load(os.path.join(TOOLS, "transformer_concepts.npz"), allow_pickle=True)
    fens = data["fens"]
    labels = data["labels"]
    activations = data["activations"]
    pca_components = data["pca_components"]
    pca_mean = data["pca_mean"]

    X_pca = (activations - pca_mean) @ pca_components.T

    # Load both networks for move comparison
    print("Loading networks...")
    strong, _, _ = load_transformer(os.path.join(TOOLS, "networks", "strong-912627.pb.gz"))
    strong.policy_map = POLICY_MAP.tolist()
    strong = strong.to(device).eval().half()

    weak, _, _ = load_transformer(os.path.join(TOOLS, "networks", "weak-910127.pb.gz"))
    weak.policy_map = POLICY_MAP.tolist()
    weak = weak.to(device).eval().half()

    # Get cluster info sorted by concept quality (same order as pipeline report)
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    unique_labels = sorted(set(labels))
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_pca)

    cluster_scores = []
    for c in unique_labels:
        mask = labels == c
        if mask.sum() < 20:
            continue
        y = mask.astype(int)
        probe = LogisticRegression(C=1.0, max_iter=300, solver="lbfgs", random_state=42)
        auc = float(cross_val_score(probe, X_scaled, y, cv=5, scoring="roc_auc").mean())
        cluster_scores.append((c, auc, int(mask.sum())))

    cluster_scores.sort(key=lambda x: x[1], reverse=True)

    # For each concept, find 3 closest to centroid and get moves
    print("Analyzing concepts...\n")

    for rank, (cid, auc, n_pos) in enumerate(cluster_scores[:4]):
        mask = labels == cid
        indices = np.where(mask)[0]
        cluster_pca = X_pca[indices]
        centroid = cluster_pca.mean(axis=0)
        dists = np.linalg.norm(cluster_pca - centroid, axis=1)
        closest = np.argsort(dists)[:3]

        # Gather material and phase stats
        materials, phases, piece_counts = [], [], []
        for idx in indices:
            try:
                b = chess.Board(str(fens[idx]))
                pv = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                      chess.ROOK: 5, chess.QUEEN: 9}
                wm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if p.color)
                bm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if not p.color)
                materials.append(wm - bm)
                pc = len(b.piece_map())
                piece_counts.append(pc)
                phases.append("opening" if pc > 28 else ("middle" if pc > 14 else "endgame"))
            except Exception:
                pass

        phase_dist = {}
        for p in phases:
            phase_dist[p] = phase_dist.get(p, 0) + 1

        sep = "=" * 70
        print(sep)
        print(f"  CONCEPT {rank+1}  |  {n_pos} positions  |  AUC {auc:.3f}")
        print(sep)
        print(f"  Material balance: mean={np.mean(materials):+.1f}, std={np.std(materials):.1f}")
        print(f"  Pieces on board:  mean={np.mean(piece_counts):.0f}")
        print(f"  Game phase:       {phase_dist}")
        print()

        for j, ci in enumerate(closest):
            idx = indices[ci]
            fen = str(fens[idx])
            board = chess.Board(fen)
            turn = "White" if board.turn else "Black"

            # Get moves from both networks
            planes = torch.from_numpy(board_to_planes(board)).unsqueeze(0).to(device).half()
            with torch.no_grad():
                s_pol, s_val = strong(planes)
                w_pol, w_val = weak(planes)

            s_moves = get_top_moves(s_pol[0].float().cpu().numpy(), board, k=3)
            w_moves = get_top_moves(w_pol[0].float().cpu().numpy(), board, k=3)

            s_wdl = torch.softmax(s_val.float(), dim=1)[0].cpu().numpy()
            w_wdl = torch.softmax(w_val.float(), dim=1)[0].cpu().numpy()

            print(f"  --- Position {j+1} (dist={dists[ci]:.1f}) ---")
            print(f"  FEN: {fen}")
            print(f"  To move: {turn}")
            print()
            rows = str(board).split("\n")
            for ri, row in enumerate(rows):
                print(f"    {8-ri}  {row}")
            print(f"       a b c d e f g h")
            print()
            if s_moves:
                s_str = ", ".join(f"{m}({p:.0%})" for m, p in s_moves)
                print(f"  STRONG: {s_str}")
            if w_moves:
                w_str = ", ".join(f"{m}({p:.0%})" for m, p in w_moves)
                print(f"  WEAK:   {w_str}")
            print(f"  Strong eval: W={s_wdl[0]:.0%} D={s_wdl[1]:.0%} L={s_wdl[2]:.0%}")
            print(f"  Weak eval:   W={w_wdl[0]:.0%} D={w_wdl[1]:.0%} L={w_wdl[2]:.0%}")
            print()

        print()


if __name__ == "__main__":
    main()
