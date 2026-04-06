#!/usr/bin/env python3
"""
Phase 0 v2: Full concept extraction pipeline with transformer networks.

1. Load both transformer networks (strong=912627, weak=910127)
2. Generate 10K positions, find policy disagreements
3. Capture encoder activations at disagreement positions
4. PCA + clustering + logistic probes -> concepts
5. Filter by teachability + novelty -> GO/NO-GO
"""

import os
import random
import sys
import time

import chess
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import silhouette_score
from sklearn.model_selection import cross_val_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(__file__))
from leela_transformer import load_transformer, mish
from leela_net import board_to_planes

TOOLS = os.path.dirname(__file__)
STRONG_PATH = os.path.join(TOOLS, "networks", "strong-912627.pb.gz")
WEAK_PATH = os.path.join(TOOLS, "networks", "weak-910127.pb.gz")
POLICY_MAP = np.load(os.path.join(TOOLS, "attn_policy_map.npy"))

NUM_POSITIONS = 10_000
BATCH_SIZE = 32  # Smaller batch for transformer VRAM
PCA_COMPONENTS = 150
MIN_CLUSTER_SIZE = 20


# ---------------------------------------------------------------------------
# Position generation
# ---------------------------------------------------------------------------

def generate_positions(n, seed=42):
    rng = random.Random(seed)
    positions, seen = [], set()
    while len(positions) < n:
        board = chess.Board()
        for _ in range(rng.randint(8, 60)):
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(rng.choice(moves))
        if board.is_game_over():
            continue
        fen = board.fen()
        if fen in seen or len(list(board.legal_moves)) < 4:
            continue
        seen.add(fen)
        positions.append((fen, board.copy()))
    return positions[:n]


# ---------------------------------------------------------------------------
# Batched inference
# ---------------------------------------------------------------------------

def run_batched(model, positions, device, batch_size, capture_layers=False):
    """Run model on positions. Returns policies, and optionally encoder activations."""
    dtype = next(model.parameters()).dtype
    all_pol = []
    all_acts = [] if capture_layers else None

    # Hook last 5 encoder layers if capturing
    hooks, captured = [], {}
    if capture_layers:
        for i in range(model.n_enc - 5, model.n_enc):
            name = f"enc_{i}"
            def make_hook(n):
                def fn(_, __, out):
                    captured[n] = out.detach().float().cpu()
                return fn
            hooks.append(model.encoders[i].register_forward_hook(make_hook(name)))

    layer_names = [f"enc_{i}" for i in range(model.n_enc - 5, model.n_enc)]

    with torch.no_grad():
        for start in range(0, len(positions), batch_size):
            batch = positions[start:start + batch_size]
            planes = [board_to_planes(b) for _, b in batch]
            x = torch.from_numpy(np.stack(planes)).to(device=device, dtype=dtype)

            pol, _ = model(x)
            all_pol.append(pol.float().cpu().numpy())

            if capture_layers:
                # Each captured[name] is (B*64, embed) -> reshape to (B, 64*embed)
                B = len(batch)
                enc_acts = np.concatenate(
                    [captured[n].numpy().reshape(B, -1) for n in layer_names],
                    axis=1)
                all_acts.append(enc_acts)
                captured.clear()

    for h in hooks:
        h.remove()

    policies = np.concatenate(all_pol, axis=0)
    acts = np.concatenate(all_acts, axis=0) if capture_layers else None
    return policies, acts


# ---------------------------------------------------------------------------
# Disagreement detection (using raw policy logits)
# ---------------------------------------------------------------------------

def get_top_move_idx(policy_logits, board, policy_map):
    """Get the index of the best legal move from policy logits."""
    probs = np.exp(policy_logits - policy_logits.max())
    probs /= probs.sum()
    # Sort by probability
    ranked = np.argsort(probs)[::-1]
    # Return first legal move (simplified - just return top policy index)
    return int(ranked[0]), float(probs[ranked[0]])


def find_disagreements(strong_pol, weak_pol, positions):
    disagree_idx, disagree_info = [], []
    for i in range(len(positions)):
        s_top, s_prob = get_top_move_idx(strong_pol[i], None, None)
        w_top, w_prob = get_top_move_idx(weak_pol[i], None, None)
        if s_top != w_top and s_prob > 0.02:
            disagree_idx.append(i)
            disagree_info.append({
                "fen": positions[i][0],
                "strong_idx": s_top,
                "weak_idx": w_top,
                "strong_prob": s_prob,
            })
    return disagree_idx, disagree_info


# ---------------------------------------------------------------------------
# Concept extraction
# ---------------------------------------------------------------------------

def extract_and_filter_concepts(activations, fens, labels, n_clusters):
    """PCA + probes + teachability + novelty in one pass."""
    n = len(fens)

    # PCA
    print(f"  PCA: {activations.shape[1]} -> {PCA_COMPONENTS} dims...", end=" ", flush=True)
    pca = PCA(n_components=PCA_COMPONENTS, random_state=42)
    X_pca = pca.fit_transform(activations)
    print(f"({pca.explained_variance_ratio_.sum():.0%} var)")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_pca)

    concepts = []
    for c in range(n_clusters):
        mask = labels == c
        n_pos = int(mask.sum())
        if n_pos < MIN_CLUSTER_SIZE:
            continue

        y = mask.astype(int)

        # Probe AUC
        probe = LogisticRegression(C=1.0, max_iter=300, solver="lbfgs", random_state=42)
        auc = float(cross_val_score(probe, X_scaled, y, cv=5, scoring="roc_auc").mean())

        # Teachability
        mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=200, random_state=42,
                            early_stopping=True, validation_fraction=0.15)
        teach = float(cross_val_score(mlp, X_pca, y, cv=5, scoring="roc_auc").mean())

        # Novelty heuristic
        cluster_fens = fens[mask]
        materials, phases = [], []
        for fen in cluster_fens:
            try:
                b = chess.Board(str(fen))
                pv = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                      chess.ROOK: 5, chess.QUEEN: 9}
                wm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if p.color)
                bm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if not p.color)
                materials.append(wm - bm)
                pieces = len(b.piece_map())
                phases.append(0 if pieces > 28 else (1 if pieces > 14 else 2))
            except Exception:
                pass

        mat_div = min(np.std(materials) / 5.0, 1.0) if materials else 0
        ph_arr = np.array(phases)
        ph_counts = np.bincount(ph_arr, minlength=3).astype(float)
        ph_probs = ph_counts / (ph_counts.sum() + 1e-8)
        ph_ent = -sum(p * np.log2(p + 1e-8) for p in ph_probs) / np.log2(3)
        nontrivial = 1.0 if (mat_div > 0.1 and len(set(phases)) > 1) else 0.3
        novelty = 0.4 * mat_div + 0.3 * ph_ent + 0.3 * nontrivial

        combined = 0.4 * auc + 0.3 * teach + 0.3 * novelty

        concepts.append({
            "cluster": c, "n_pos": n_pos, "auc": auc,
            "teach": teach, "novelty": novelty, "combined": combined,
        })

    concepts.sort(key=lambda x: x["combined"], reverse=True)
    return concepts, pca


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # ---- Load both networks ----
    print("\n[1/5] Loading networks...")
    t0 = time.time()
    strong, n_enc_s, embed_s = load_transformer(STRONG_PATH)
    strong.policy_map = POLICY_MAP.tolist()
    strong = strong.to(device).eval().half()
    print(f"  Strong loaded ({time.time()-t0:.1f}s, {torch.cuda.memory_allocated()/1e9:.2f} GB)")

    t0 = time.time()
    weak, n_enc_w, embed_w = load_transformer(WEAK_PATH)
    weak.policy_map = POLICY_MAP.tolist()
    weak = weak.to(device).eval().half()
    print(f"  Weak loaded ({time.time()-t0:.1f}s, {torch.cuda.memory_allocated()/1e9:.2f} GB)")

    # ---- Generate positions ----
    print(f"\n[2/5] Generating {NUM_POSITIONS:,} positions...")
    t0 = time.time()
    positions = generate_positions(NUM_POSITIONS)
    print(f"  {len(positions):,} positions in {time.time()-t0:.1f}s")

    # ---- Run both networks (policy only) ----
    print("\n[3/5] Running inference...")
    t0 = time.time()
    weak_pol, _ = run_batched(weak, positions, device, BATCH_SIZE)
    print(f"  Weak: {time.time()-t0:.1f}s ({len(positions)/(time.time()-t0):.0f} pos/s)")
    del weak
    torch.cuda.empty_cache()

    t0 = time.time()
    strong_pol, _ = run_batched(strong, positions, device, BATCH_SIZE)
    print(f"  Strong: {time.time()-t0:.1f}s ({len(positions)/(time.time()-t0):.0f} pos/s)")

    # ---- Find disagreements ----
    disagree_idx, disagree_info = find_disagreements(strong_pol, weak_pol, positions)
    n_dis = len(disagree_idx)
    print(f"  Disagreements: {n_dis}/{len(positions)} ({100*n_dis/len(positions):.1f}%)")

    if n_dis < 50:
        print("ERROR: Too few disagreements. Networks may be too similar or broken.")
        return

    # ---- Capture activations at disagreement positions ----
    print(f"\n[4/5] Capturing encoder activations for {n_dis} positions...")
    dis_positions = [positions[i] for i in disagree_idx]
    t0 = time.time()
    _, dis_acts = run_batched(strong, dis_positions, device, BATCH_SIZE, capture_layers=True)
    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"  Activation matrix: {dis_acts.shape} ({dis_acts.nbytes/1e6:.0f} MB)")

    del strong
    torch.cuda.empty_cache()

    # ---- Clustering + concept extraction ----
    print(f"\n[5/5] Extracting concepts...")
    fens = np.array([d["fen"] for d in disagree_info])

    # Find best k
    print("  Finding optimal clusters...", flush=True)
    pca_quick = PCA(n_components=PCA_COMPONENTS, random_state=42)
    X_quick = pca_quick.fit_transform(dis_acts)
    best_k, best_sil = 5, -1
    for k in range(5, 20):
        km = KMeans(n_clusters=k, n_init=5, random_state=42, max_iter=100)
        lbl = km.fit_predict(X_quick)
        s = silhouette_score(X_quick, lbl, sample_size=min(2000, len(X_quick)))
        if s > best_sil:
            best_k, best_sil = k, s
    print(f"  Best k={best_k} (silhouette={best_sil:.3f})")

    km = KMeans(n_clusters=best_k, n_init=10, random_state=42)
    labels = km.fit_predict(X_quick)

    # Extract + filter concepts
    concepts, pca = extract_and_filter_concepts(dis_acts, fens, labels, best_k)

    # ---- Final report ----
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  CONCEPT REPORT (Transformer 15x1024, 69 Elo gap)")
    print(f"{sep}")
    print(f"  {'#':>2}  {'Pos':>4}  {'AUC':>5}  {'Teach':>5}  {'Novel':>5}  {'Score':>5}  Grade")
    print(f"  {'--':>2}  {'---':>4}  {'---':>5}  {'-----':>5}  {'-----':>5}  {'-----':>5}  -----")

    viable = 0
    for i, c in enumerate(concepts):
        grade = "A" if c["combined"] > 0.70 else ("B" if c["combined"] > 0.55 else "C")
        if c["combined"] > 0.60 and c["teach"] > 0.50:
            viable += 1
            grade += " *"
        print(f"  {i+1:>2}  {c['n_pos']:>4}  {c['auc']:.3f}  {c['teach']:.3f}  "
              f"{c['novelty']:.3f}  {c['combined']:.3f}  {grade}")

    print(f"\n  Viable concepts: {viable}")
    if viable >= 3:
        print(f"  >>> GO: {viable} concepts. Phase 0 PASSED. <<<")
    else:
        print(f"  >>> Need 3+ viable. Got {viable}. <<<")

    # Save
    out = os.path.join(TOOLS, "transformer_concepts.npz")
    np.savez_compressed(out, fens=fens, labels=labels, activations=dis_acts,
                        pca_components=pca.components_, pca_mean=pca.mean_)
    print(f"\n  Saved -> {out} ({os.path.getsize(out)/1e6:.0f} MB)")


if __name__ == "__main__":
    main()
