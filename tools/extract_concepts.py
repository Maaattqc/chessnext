#!/usr/bin/env python3
"""
Phase 0, Step 3: Extract concept vectors from disagreement activations.

Takes the disagreement positions and their strong-network activations,
uses PCA + clustering + linear probes to discover concept directions
in the activation space.

Method (simplified from DeepMind PNAS 2025):
1. Focus on late residual blocks (10-19) where high-level concepts live
2. PCA to reduce 163K dims -> manageable space
3. K-means clustering to find groups of similar disagreements
4. For each cluster, train a logistic regression probe on full activations
5. The probe weight vector = concept activation vector (CAV)
6. Score concepts by probe accuracy, cluster coherence, and size

Usage:
    .venv/Scripts/python.exe extract_concepts.py
"""

import os
import sys
import time

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

TOOLS = os.path.dirname(__file__)
INPUT_PATH = os.path.join(TOOLS, "disagreements.npz")
OUTPUT_PATH = os.path.join(TOOLS, "concepts.npz")

# Hyperparameters
N_BLOCKS = 20
N_FILTERS = 256
BLOCK_SIZE = N_FILTERS * 64        # 16384 per block
LATE_BLOCKS = range(10, 20)         # Focus on blocks 10-19
LATE_DIM = len(LATE_BLOCKS) * BLOCK_SIZE  # 163,840
PCA_COMPONENTS = 200                # Reduce to 200 dims
N_CLUSTERS_RANGE = range(5, 25)     # Try 5-24 clusters
MIN_CLUSTER_SIZE = 20               # Minimum positions per concept


def load_data():
    """Load disagreement data and extract late-block activations."""
    print("Loading disagreements...")
    data = np.load(INPUT_PATH, allow_pickle=True)
    fens = data["fens"]
    strong_moves = data["strong_moves"]
    weak_moves = data["weak_moves"]
    values = data["values"]

    # Full activations: (N, 327680) = 20 blocks * 256 * 64
    acts_full = data["activations"]
    n = len(fens)
    print(f"  {n} positions, activation shape: {acts_full.shape}")

    # Extract late blocks only (blocks 10-19)
    late_acts = np.zeros((n, LATE_DIM), dtype=np.float32)
    for j, blk in enumerate(LATE_BLOCKS):
        start_full = blk * BLOCK_SIZE
        start_late = j * BLOCK_SIZE
        late_acts[:, start_late:start_late + BLOCK_SIZE] = \
            acts_full[:, start_full:start_full + BLOCK_SIZE]

    print(f"  Late-block activations: {late_acts.shape}")
    return fens, strong_moves, weak_moves, values, late_acts, acts_full


def find_optimal_clusters(X_pca, n_range):
    """Use silhouette score to pick best k for K-means."""
    from sklearn.metrics import silhouette_score

    best_k, best_score = n_range.start, -1
    scores = []

    for k in n_range:
        km = KMeans(n_clusters=k, n_init=5, random_state=42, max_iter=100)
        labels = km.fit_predict(X_pca)
        score = silhouette_score(X_pca, labels, sample_size=min(2000, len(X_pca)))
        scores.append((k, score))
        if score > best_score:
            best_k, best_score = k, score

    print(f"  Best k={best_k} (silhouette={best_score:.3f})")
    for k, s in scores:
        bar = "#" * int(s * 50) if s > 0 else ""
        marker = " <--" if k == best_k else ""
        print(f"    k={k:2d}  sil={s:.3f}  {bar}{marker}")

    return best_k


def extract_concepts(X_late, X_pca, labels, n_clusters, fens, strong_moves):
    """For each cluster, train a linear probe and extract the concept vector."""
    concepts = []
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_pca)  # Use PCA features (200D) not raw (163K)

    for c in range(n_clusters):
        mask = (labels == c)
        n_pos = mask.sum()

        if n_pos < MIN_CLUSTER_SIZE:
            continue

        # Binary classification: this cluster vs rest
        y = mask.astype(int)

        # Logistic regression probe on PCA-reduced features
        probe = LogisticRegression(
            C=1.0, max_iter=300, solver="lbfgs", random_state=42
        )

        # Cross-validated accuracy
        cv_scores = cross_val_score(probe, X_scaled, y, cv=5, scoring="roc_auc")
        mean_auc = cv_scores.mean()

        # Fit on all data to get the concept vector (in PCA space)
        probe.fit(X_scaled, y)
        cav_pca = probe.coef_[0]  # Concept direction in PCA space
        cav_norm = cav_pca / (np.linalg.norm(cav_pca) + 1e-8)

        # Cluster statistics
        cluster_acts = X_pca[mask]
        centroid = cluster_acts.mean(axis=0)
        spread = np.linalg.norm(cluster_acts - centroid, axis=1).mean()

        # What moves does this cluster prefer?
        cluster_moves = strong_moves[mask]
        unique_moves, counts = np.unique(cluster_moves, return_counts=True)
        top_move_idx = np.argsort(counts)[::-1][:3]
        top_moves = [(unique_moves[i], counts[i]) for i in top_move_idx]

        # Positions in this cluster
        cluster_fens = fens[mask]

        concepts.append({
            "cluster_id": c,
            "n_positions": int(n_pos),
            "probe_auc": float(mean_auc),
            "spread": float(spread),
            "cav": cav_norm,
            "top_moves": top_moves,
            "fens": cluster_fens,
        })

    # Sort by probe quality
    concepts.sort(key=lambda x: x["probe_auc"], reverse=True)
    return concepts


def main():
    t_start = time.time()

    # Load data
    fens, strong_moves, weak_moves, values, X_late, X_full = load_data()
    n = len(fens)

    # PCA
    print(f"\nPCA: {LATE_DIM} -> {PCA_COMPONENTS} dimensions...")
    t0 = time.time()
    pca = PCA(n_components=PCA_COMPONENTS, random_state=42)
    X_pca = pca.fit_transform(X_late)
    var_explained = pca.explained_variance_ratio_.sum()
    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"  Variance explained: {var_explained:.1%}")

    # Optimal clustering
    print(f"\nFinding optimal number of clusters...")
    best_k = find_optimal_clusters(X_pca, N_CLUSTERS_RANGE)

    # Final clustering
    print(f"\nClustering with k={best_k}...")
    km = KMeans(n_clusters=best_k, n_init=10, random_state=42)
    labels = km.fit_predict(X_pca)

    # Cluster sizes
    print("  Cluster sizes:")
    for c in range(best_k):
        n_c = (labels == c).sum()
        print(f"    Cluster {c:2d}: {n_c:4d} positions")

    # Extract concepts
    print(f"\nExtracting concept vectors (logistic regression probes)...")
    t0 = time.time()
    concepts = extract_concepts(X_late, X_pca, labels, best_k,
                                fens, strong_moves)
    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"  {len(concepts)} concepts found (min size={MIN_CLUSTER_SIZE})")

    # Report
    print(f"\n{'='*70}")
    print(f"  CONCEPT REPORT")
    print(f"{'='*70}")
    for i, con in enumerate(concepts):
        quality = "STRONG" if con["probe_auc"] > 0.85 else \
                  "MEDIUM" if con["probe_auc"] > 0.75 else "WEAK"
        print(f"\n  Concept {i+1} [{quality}]")
        print(f"    Cluster:    {con['cluster_id']}")
        print(f"    Positions:  {con['n_positions']}")
        print(f"    Probe AUC:  {con['probe_auc']:.3f}")
        print(f"    Spread:     {con['spread']:.2f}")
        print(f"    Top moves:  {', '.join(f'{m}({c})' for m, c in con['top_moves'])}")
        print(f"    Sample FEN: {con['fens'][0][:60]}...")

    strong_concepts = [c for c in concepts if c["probe_auc"] > 0.80]
    print(f"\n{'='*70}")
    print(f"  SUMMARY: {len(strong_concepts)} strong concepts "
          f"(AUC > 0.80) out of {len(concepts)} total")
    print(f"{'='*70}")

    # Save concepts
    cavs = np.stack([c["cav"] for c in concepts])
    cluster_ids = np.array([c["cluster_id"] for c in concepts])
    aucs = np.array([c["probe_auc"] for c in concepts])
    sizes = np.array([c["n_positions"] for c in concepts])

    np.savez_compressed(OUTPUT_PATH,
                        cavs=cavs,
                        cluster_ids=cluster_ids,
                        aucs=aucs,
                        sizes=sizes,
                        pca_components=pca.components_,
                        pca_mean=pca.mean_,
                        labels=labels,
                        fens=fens,
                        strong_moves=strong_moves,
                        weak_moves=weak_moves)
    mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"\nSaved -> {OUTPUT_PATH}  ({mb:.1f} MB)")
    print(f"Total time: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
