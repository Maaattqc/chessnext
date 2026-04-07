#!/usr/bin/env python3
"""Convert pipeline_v4 output into concepts_for_seed.json for name_concepts.py."""

import json
import os

import chess
import numpy as np

TOOLS = os.path.dirname(__file__)

# Load pipeline outputs
data = np.load(os.path.join(TOOLS, "concepts_v4.npz"), allow_pickle=True)
vectors = data["vectors"]
teach = data["teach"]
teach_mask = data["teach_mask"]

with open(os.path.join(TOOLS, "concepts_v4_positions.json")) as f:
    positions = json.load(f)

# Use ALL concepts (not just teachable) — teachability is stored as metadata
surv_idx = list(range(len(vectors)))
surv_vec = vectors
surv_pos = positions
surv_teach = teach

# Group by similarity
def group_concepts(vecs, threshold=0.35):
    n = len(vecs)
    used, groups = set(), []
    for i in range(n):
        if i in used:
            continue
        g = [i]
        used.add(i)
        for j in range(i + 1, n):
            if j not in used and np.dot(vecs[i], vecs[j]) > threshold:
                g.append(j)
                used.add(j)
        groups.append(g)
    groups.sort(key=len, reverse=True)
    return groups

groups = group_concepts(surv_vec, 0.35) if len(surv_vec) > 0 else []

# Build concepts_for_seed.json
PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

seed_concepts = []
for gi, group in enumerate(groups):
    group_positions = []
    total_pieces = 0
    total_material = 0
    phases = {"opening": 0, "middlegame": 0, "endgame": 0}

    for idx in group:
        p = surv_pos[idx]
        board = chess.Board(p["fen"])
        n_pieces = len(board.piece_map())
        total_pieces += n_pieces

        wm = sum(PIECE_VALUES.get(pc.piece_type, 0)
                 for pc in board.piece_map().values() if pc.color == chess.WHITE)
        bm = sum(PIECE_VALUES.get(pc.piece_type, 0)
                 for pc in board.piece_map().values() if pc.color == chess.BLACK)
        total_material += wm - bm

        if n_pieces > 28:
            phases["opening"] += 1
        elif n_pieces > 16:
            phases["middlegame"] += 1
        else:
            phases["endgame"] += 1

        group_positions.append({
            "fen": p["fen"],
            "strong": p["opt_line"][0] if p["opt_line"] else "?",
            "weak": p["sub_line"][0] if p["sub_line"] else "?",
            "strong_line": p["opt_line"],
            "weak_line": p["sub_line"],
        })

    n = len(group)
    avg_t = float(np.mean([surv_teach[i] for i in group]))
    is_teachable = bool(np.any([teach_mask[i] for i in group]))
    seed_concepts.append({
        "size": n,
        "avg_pieces": total_pieces / n,
        "avg_material": total_material / n,
        "avg_teach": avg_t,
        "teachable": is_teachable,
        "phases": phases,
        "positions": group_positions,
    })

out_path = os.path.join(TOOLS, "concepts_for_seed.json")
with open(out_path, "w") as f:
    json.dump(seed_concepts, f, indent=2)

print(f"Created {len(seed_concepts)} concept groups in {out_path}")
for i, c in enumerate(seed_concepts):
    print(f"  Group {i+1}: {c['size']} positions, teach={c['avg_teach']:.3f}, "
          f"pieces={c['avg_pieces']:.0f}")
