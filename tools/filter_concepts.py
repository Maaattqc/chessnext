#!/usr/bin/env python3
"""
Phase 0, Step 4: Filter concepts by teachability and novelty.

Teachability: Can a small network learn to recognise the concept?
  - Train a tiny MLP on the concept labels
  - If it learns quickly (high accuracy), the concept is teachable

Novelty: Is this concept already known in human chess?
  - Check if the positions cluster around known opening/endgame patterns
  - Measure how "surprising" the strong network's move is to Stockfish
  - Concepts where Leela sees something Stockfish/humans don't = novel

GO/NO-GO: Need 3+ concepts with teachability > 0.70 AND novelty > 0.50

Usage:
    .venv/Scripts/python.exe filter_concepts.py
"""

import os
import sys
import time

import chess
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.neural_network import MLPClassifier

TOOLS = os.path.dirname(__file__)
CONCEPTS_PATH = os.path.join(TOOLS, "concepts.npz")
OUTPUT_PATH = os.path.join(TOOLS, "filtered_concepts.npz")


def load_concepts():
    data = np.load(CONCEPTS_PATH, allow_pickle=True)
    return data


def teachability_score(activations, labels, cluster_id):
    """How easily can a small network learn this concept?

    Train a tiny MLP (1 hidden layer, 32 units) to classify
    cluster membership from raw activations.
    High CV accuracy = teachable concept.
    """
    y = (labels == cluster_id).astype(int)
    n_pos = y.sum()

    if n_pos < 20:
        return 0.0

    # Use PCA-reduced features for speed
    mlp = MLPClassifier(
        hidden_layer_sizes=(32,),
        max_iter=200,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
    )

    scores = cross_val_score(mlp, activations, y, cv=5, scoring="roc_auc")
    return float(scores.mean())


def novelty_score(fens, labels, cluster_id):
    """How novel is this concept compared to known chess patterns?

    Heuristic approach (no Stockfish needed for Phase 0):
    1. Material balance diversity: if cluster has diverse material,
       it's about a positional concept, not just material
    2. Move diversity: if the strong net plays many different moves
       across cluster positions, the concept is structural (novel)
    3. Game phase diversity: if concept spans opening/middle/endgame,
       it's a deep positional concept

    Returns 0-1 score where higher = more novel.
    """
    mask = (labels == cluster_id)
    cluster_fens = fens[mask]

    if len(cluster_fens) < 10:
        return 0.0

    material_balances = []
    piece_counts = []
    phases = []  # 0=opening, 1=middlegame, 2=endgame

    for fen in cluster_fens:
        try:
            board = chess.Board(str(fen))
        except ValueError:
            continue

        # Material balance
        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                       chess.ROOK: 5, chess.QUEEN: 9}
        white_mat = sum(piece_values.get(p.piece_type, 0)
                       for p in board.piece_map().values() if p.color)
        black_mat = sum(piece_values.get(p.piece_type, 0)
                       for p in board.piece_map().values() if not p.color)
        material_balances.append(white_mat - black_mat)

        # Piece count (for game phase)
        total_pieces = len(board.piece_map())
        piece_counts.append(total_pieces)

        if total_pieces > 28:
            phases.append(0)   # opening
        elif total_pieces > 14:
            phases.append(1)   # middlegame
        else:
            phases.append(2)   # endgame

    if not material_balances:
        return 0.0

    material_balances = np.array(material_balances)
    phases = np.array(phases)

    # Score components
    # 1. Material diversity (std of material balance)
    mat_diversity = min(np.std(material_balances) / 5.0, 1.0)

    # 2. Phase diversity (entropy of phase distribution)
    phase_counts = np.bincount(phases, minlength=3).astype(float)
    phase_probs = phase_counts / phase_counts.sum()
    phase_entropy = -sum(p * np.log2(p + 1e-8) for p in phase_probs)
    phase_diversity = phase_entropy / np.log2(3)  # normalize to 0-1

    # 3. Not a trivial pattern (not all same material, not all same phase)
    non_trivial = 1.0 if (mat_diversity > 0.1 and len(set(phases)) > 1) else 0.3

    novelty = 0.4 * mat_diversity + 0.3 * phase_diversity + 0.3 * non_trivial
    return float(min(novelty, 1.0))


def main():
    print("Loading concepts...")
    data = load_concepts()

    cavs = data["cavs"]
    cluster_ids = data["cluster_ids"]
    aucs = data["aucs"]
    sizes = data["sizes"]
    labels = data["labels"]
    fens = data["fens"]
    strong_moves = data["strong_moves"]
    weak_moves = data["weak_moves"]

    # Reconstruct PCA-reduced activations for teachability
    pca_components = data["pca_components"]
    pca_mean = data["pca_mean"]

    n_concepts = len(cavs)
    print(f"  {n_concepts} concepts to evaluate")

    # Load disagreement activations for teachability testing
    dis_data = np.load(os.path.join(TOOLS, "disagreements.npz"))
    acts_full = dis_data["activations"]

    # Extract late blocks (10-19) for teachability
    BLOCK_SIZE = 256 * 64
    late_acts = np.zeros((len(acts_full), 10 * BLOCK_SIZE), dtype=np.float32)
    for j, blk in enumerate(range(10, 20)):
        s_full = blk * BLOCK_SIZE
        s_late = j * BLOCK_SIZE
        late_acts[:, s_late:s_late + BLOCK_SIZE] = \
            acts_full[:, s_full:s_full + BLOCK_SIZE]

    # PCA transform
    X_pca = (late_acts - pca_mean) @ pca_components.T

    print("\nEvaluating each concept...")
    results = []

    for i in range(n_concepts):
        cid = cluster_ids[i]
        auc = aucs[i]
        size = sizes[i]

        print(f"\n  Concept {i+1}/{n_concepts} (cluster {cid}, {size} pos, AUC={auc:.3f})")

        # Teachability
        t0 = time.time()
        teach = teachability_score(X_pca, labels, cid)
        print(f"    Teachability: {teach:.3f}  ({time.time()-t0:.1f}s)")

        # Novelty
        novel = novelty_score(fens, labels, cid)
        print(f"    Novelty:      {novel:.3f}")

        # Combined score
        combined = 0.4 * auc + 0.3 * teach + 0.3 * novel
        print(f"    Combined:     {combined:.3f}")

        results.append({
            "concept_idx": i,
            "cluster_id": int(cid),
            "n_positions": int(size),
            "probe_auc": float(auc),
            "teachability": float(teach),
            "novelty": float(novel),
            "combined": float(combined),
        })

    # Sort by combined score
    results.sort(key=lambda x: x["combined"], reverse=True)

    # Final report
    print(f"\n{'='*70}")
    print(f"  FINAL CONCEPT RANKING")
    print(f"{'='*70}")
    print(f"  {'#':>2}  {'Pos':>4}  {'AUC':>5}  {'Teach':>5}  {'Novel':>5}  {'Score':>5}  Grade")
    print(f"  {'--':>2}  {'---':>4}  {'---':>5}  {'-----':>5}  {'-----':>5}  {'-----':>5}  -----")

    go_concepts = 0
    for rank, r in enumerate(results):
        grade = "A" if r["combined"] > 0.70 else \
                "B" if r["combined"] > 0.55 else "C"
        if r["combined"] > 0.60 and r["teachability"] > 0.50:
            go_concepts += 1
            grade += " *"

        print(f"  {rank+1:>2}  {r['n_positions']:>4}  {r['probe_auc']:>.3f}  "
              f"{r['teachability']:>.3f}  {r['novelty']:>.3f}  "
              f"{r['combined']:>.3f}  {grade}")

    print(f"\n  * = viable concept (combined > 0.60, teachability > 0.50)")
    print(f"  Viable concepts: {go_concepts}")

    if go_concepts >= 3:
        print(f"\n  >>> GO: {go_concepts} viable concepts found. <<<")
        print(f"  >>> Phase 0 validation PASSED. Proceed to Phase 1. <<<")
    else:
        print(f"\n  >>> CAUTION: Only {go_concepts} viable concepts. <<<")
        print(f"  >>> Need 3+ for GO. Consider more positions or different networks. <<<")

    # Save
    np.savez_compressed(OUTPUT_PATH,
                        results=np.array([(r["concept_idx"], r["cluster_id"],
                                          r["n_positions"], r["probe_auc"],
                                          r["teachability"], r["novelty"],
                                          r["combined"])
                                         for r in results]),
                        cavs=cavs)
    mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"\n  Saved -> {OUTPUT_PATH}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
