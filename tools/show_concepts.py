#!/usr/bin/env python3
"""Show the 3 most representative positions for each concept."""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import chess

TOOLS = os.path.dirname(__file__)

# Load data
concepts = np.load(os.path.join(TOOLS, "concepts.npz"), allow_pickle=True)
disagree = np.load(os.path.join(TOOLS, "disagreements.npz"), allow_pickle=True)

labels = concepts["labels"]
aucs = concepts["aucs"]
cluster_ids = concepts["cluster_ids"]
fens = concepts["fens"]
strong_moves = disagree["strong_moves"]
weak_moves = disagree["weak_moves"]
acts = disagree["activations"]

# Late blocks for centroid distances
BLOCK_SIZE = 256 * 64
late_acts = np.zeros((len(acts), 10 * BLOCK_SIZE), dtype=np.float32)
for j, blk in enumerate(range(10, 20)):
    s, d = blk * BLOCK_SIZE, j * BLOCK_SIZE
    late_acts[:, d:d + BLOCK_SIZE] = acts[:, s:s + BLOCK_SIZE]

pca_components = concepts["pca_components"]
pca_mean = concepts["pca_mean"]
X_pca = (late_acts - pca_mean) @ pca_components.T

# Sort by AUC descending (same order as report)
concept_order = np.argsort(aucs)[::-1]

SEP = "=" * 70

for rank, cidx in enumerate(concept_order):
    cid = cluster_ids[cidx]
    auc = aucs[cidx]
    mask = labels == cid
    n_pos = int(mask.sum())
    indices = np.where(mask)[0]

    # Centroid + closest 3
    cluster_pca = X_pca[indices]
    centroid = cluster_pca.mean(axis=0)
    dists = np.linalg.norm(cluster_pca - centroid, axis=1)
    closest = np.argsort(dists)[:3]

    # Gather all strong moves in cluster for pattern analysis
    cluster_smoves = strong_moves[indices]
    unique, counts = np.unique(cluster_smoves, return_counts=True)
    top3 = np.argsort(counts)[::-1][:3]
    move_summary = ", ".join(f"{unique[i]}({counts[i]})" for i in top3)

    # Material and phase stats
    materials = []
    piece_totals = []
    for idx in indices:
        try:
            b = chess.Board(str(fens[idx]))
            pv = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                  chess.ROOK: 5, chess.QUEEN: 9}
            wm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if p.color)
            bm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if not p.color)
            materials.append(wm - bm)
            piece_totals.append(len(b.piece_map()))
        except Exception:
            pass

    avg_mat = np.mean(materials) if materials else 0
    avg_pieces = np.mean(piece_totals) if piece_totals else 0

    print(SEP)
    print(f"  CONCEPT {rank + 1}  |  cluster {cid}  |  {n_pos} positions  |  AUC {auc:.3f}")
    print(SEP)
    print(f"  Top strong moves: {move_summary}")
    print(f"  Avg material balance: {avg_mat:+.1f}  |  Avg pieces on board: {avg_pieces:.0f}")
    print()

    for j, ci in enumerate(closest):
        idx = indices[ci]
        fen = str(fens[idx])
        sm = str(strong_moves[idx])
        wm = str(weak_moves[idx])

        board = chess.Board(fen)
        turn = "White" if board.turn else "Black"

        print(f"  --- Position {j + 1} (dist to centroid: {dists[ci]:.1f}) ---")
        print(f"  FEN: {fen}")
        print(f"  STRONG: {sm}   vs   WEAK: {wm}   (to move: {turn})")
        print()

        rows = str(board).split("\n")
        for ri, row in enumerate(rows):
            print(f"    {8 - ri}  {row}")
        print(f"       a b c d e f g h")
        print()

    print()


print(SEP)
print("  LEGEND")
print(SEP)
print("  K/k = King   Q/q = Queen   R/r = Rook")
print("  B/b = Bishop N/n = Knight  P/p = Pawn")
print("  UPPERCASE = White, lowercase = Black")
print("  STRONG = move chosen by T60 SE-ResNet (stronger)")
print("  WEAK   = move chosen by classical 20x256 (weaker)")
