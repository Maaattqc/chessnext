#!/usr/bin/env python3
"""
Phase 0: Extract hidden layer activations from Leela Chess Zero.

Loads a 20x256 SE-ResNet network, runs 100 chess positions through it,
and captures the output of every residual block. These activations are
the raw material for concept extraction (next step).

Usage:
    .venv/Scripts/python.exe extract_activations.py
"""

import gzip
import os
import random
import sys
import time

import chess
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import net_pb2

NETWORK_PATH = os.path.join(os.path.dirname(__file__),
                            "networks", "t60-24x320.pb.gz")

# ---------------------------------------------------------------------------
# Weight decoding (LINEAR16 → float32)
# ---------------------------------------------------------------------------

def decode_layer(layer):
    """Decode an Lc0 LINEAR16-encoded weight tensor."""
    if len(layer.params) == 0:
        return None
    raw = np.frombuffer(layer.params, dtype=np.uint16).astype(np.float32)
    return raw / 65535.0 * (layer.max_val - layer.min_val) + layer.min_val


# ---------------------------------------------------------------------------
# PyTorch SE-ResNet matching Lc0's architecture
# ---------------------------------------------------------------------------

class ConvBlock(nn.Module):
    """Conv2d + batch-norm (manual, matching Lc0 stored params)."""

    def __init__(self, in_ch, out_ch, kernel=3, use_relu=True):
        super().__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, kernel,
                              padding=kernel // 2, bias=False)
        self.bn_means = nn.Parameter(torch.zeros(out_ch), requires_grad=False)
        self.bn_stddivs = nn.Parameter(torch.ones(out_ch), requires_grad=False)
        self.bn_gammas = nn.Parameter(torch.ones(out_ch), requires_grad=False)
        self.bn_betas = nn.Parameter(torch.zeros(out_ch), requires_grad=False)
        self.use_relu = use_relu

    def forward(self, x):
        x = self.conv(x)
        # Lc0 stores bn_stddivs = variance.  BN = gamma/sqrt(var+eps) * (x-mean) + beta
        v = self.bn_stddivs.view(1, -1, 1, 1)   # variance
        m = self.bn_means.view(1, -1, 1, 1)
        g = self.bn_gammas.view(1, -1, 1, 1)
        b = self.bn_betas.view(1, -1, 1, 1)
        x = g * (x - m) / torch.sqrt(v + 1e-5) + b
        if self.use_relu:
            x = F.relu(x)
        return x


class SEBlock(nn.Module):
    """Squeeze-and-Excitation: pool → fc1 → relu → fc2 → sigmoid·x + bias."""

    def __init__(self, channels, se_channels):
        super().__init__()
        self.channels = channels
        self.fc1 = nn.Linear(channels, se_channels)
        self.fc2 = nn.Linear(se_channels, 2 * channels)

    def forward(self, x):
        b, c, _, _ = x.shape
        pooled = x.mean(dim=(2, 3))                       # [B, C]
        se = F.relu(self.fc1(pooled))                      # [B, SE]
        se = self.fc2(se)                                  # [B, 2C]
        gammas = torch.sigmoid(se[:, :c]).view(b, c, 1, 1)
        betas = se[:, c:].view(b, c, 1, 1)
        return gammas * x + betas


class ResBlock(nn.Module):
    """One residual block: conv1 → conv2 → SE → skip → relu."""

    def __init__(self, channels, se_channels):
        super().__init__()
        self.conv1 = ConvBlock(channels, channels, 3, use_relu=True)
        self.conv2 = ConvBlock(channels, channels, 3, use_relu=False)
        self.se = SEBlock(channels, se_channels)

    def forward(self, x):
        skip = x
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.se(x)
        return F.relu(x + skip)


class LeelaNet(nn.Module):
    """Full Lc0 SE-ResNet with classical policy+value heads."""

    def __init__(self, n_blocks, n_filters, se_ch, pol_ch):
        super().__init__()
        self.input_conv = ConvBlock(112, n_filters, 3)
        self.blocks = nn.ModuleList(
            [ResBlock(n_filters, se_ch) for _ in range(n_blocks)]
        )
        # Classical policy head
        self.pol_conv = ConvBlock(n_filters, pol_ch, 1)
        self.pol_fc = nn.Linear(pol_ch * 64, 1858)
        # Classical value head
        self.val_conv = ConvBlock(n_filters, 32, 1)
        self.val_fc1 = nn.Linear(32 * 64, 128)
        self.val_fc2 = nn.Linear(128, 1)

    def forward(self, x):
        x = self.input_conv(x)
        for block in self.blocks:
            x = block(x)
        # Policy
        p = self.pol_conv(x)
        p = self.pol_fc(p.flatten(1))
        # Value
        v = self.val_conv(x)
        v = F.relu(self.val_fc1(v.flatten(1)))
        v = torch.tanh(self.val_fc2(v))
        return p, v


# ---------------------------------------------------------------------------
# Load protobuf weights into PyTorch model
# ---------------------------------------------------------------------------

def _load_conv(module, pb):
    """Copy protobuf ConvBlock weights into our ConvBlock."""
    w = decode_layer(pb.weights)
    if w is not None:
        module.conv.weight.data = torch.from_numpy(
            w.reshape(module.conv.weight.shape))
    for attr in ("bn_means", "bn_stddivs", "bn_gammas", "bn_betas"):
        arr = decode_layer(getattr(pb, attr))
        if arr is not None:
            getattr(module, attr).data = torch.from_numpy(arr)


def _load_fc(module, w_layer, b_layer):
    """Copy protobuf FC weights (flat) into nn.Linear."""
    w = decode_layer(w_layer)
    b = decode_layer(b_layer)
    module.weight.data = torch.from_numpy(w.reshape(module.weight.shape))
    module.bias.data = torch.from_numpy(b)


def load_network(path):
    """Parse .pb.gz and return a loaded LeelaNet on CPU."""
    net = net_pb2.Net()
    with gzip.open(path, "rb") as f:
        net.ParseFromString(f.read())
    w = net.weights

    n_blocks = len(w.residual)
    n_filters = len(np.frombuffer(w.input.weights.params, np.uint16)) // (112*9)
    se_ch = len(np.frombuffer(w.residual[0].se.w1.params, np.uint16)) // n_filters
    pol_ch = len(np.frombuffer(w.policy.weights.params, np.uint16)) // n_filters

    model = LeelaNet(n_blocks, n_filters, se_ch, pol_ch)

    # Input conv
    _load_conv(model.input_conv, w.input)

    # Residual tower
    for i, rpb in enumerate(w.residual):
        blk = model.blocks[i]
        _load_conv(blk.conv1, rpb.conv1)
        _load_conv(blk.conv2, rpb.conv2)
        # SE FC layers
        se_w1 = decode_layer(rpb.se.w1).reshape(se_ch, n_filters)
        se_b1 = decode_layer(rpb.se.b1)
        se_w2 = decode_layer(rpb.se.w2).reshape(2 * n_filters, se_ch)
        se_b2 = decode_layer(rpb.se.b2)
        blk.se.fc1.weight.data = torch.from_numpy(se_w1)
        blk.se.fc1.bias.data = torch.from_numpy(se_b1)
        blk.se.fc2.weight.data = torch.from_numpy(se_w2)
        blk.se.fc2.bias.data = torch.from_numpy(se_b2)

    # Heads
    _load_conv(model.pol_conv, w.policy)
    _load_fc(model.pol_fc, w.ip_pol_w, w.ip_pol_b)
    _load_conv(model.val_conv, w.value)
    _load_fc(model.val_fc1, w.ip1_val_w, w.ip1_val_b)
    _load_fc(model.val_fc2, w.ip2_val_w, w.ip2_val_b)

    return model, n_blocks, n_filters


# ---------------------------------------------------------------------------
# Chess position → 112-plane tensor
# ---------------------------------------------------------------------------

PIECE_INDEX = {
    chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 2,
    chess.ROOK: 3, chess.QUEEN: 4, chess.KING: 5,
}

def board_to_planes(board: chess.Board) -> np.ndarray:
    """Encode a board as (112, 8, 8) float32 — Lc0 classical 112-plane format.

    Only the current position is encoded (history planes 1-7 are zero).
    The board is always oriented from the side-to-move's perspective.
    """
    planes = np.zeros((112, 8, 8), dtype=np.float32)
    us = board.turn

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        # Flip board for black-to-move so "our" side is always at bottom
        oriented = sq if us == chess.WHITE else chess.square_mirror(sq)
        row, col = divmod(oriented, 8)
        idx = PIECE_INDEX[piece.piece_type]
        if piece.color == us:
            planes[idx, row, col] = 1.0
        else:
            planes[6 + idx, row, col] = 1.0

    # Castling (planes 104-107)
    our, their = (chess.WHITE, chess.BLACK) if us == chess.WHITE else (chess.BLACK, chess.WHITE)
    planes[104] = float(board.has_queenside_castling_rights(our))
    planes[105] = float(board.has_kingside_castling_rights(our))
    planes[106] = float(board.has_queenside_castling_rights(their))
    planes[107] = float(board.has_kingside_castling_rights(their))

    # Black-to-move flag
    planes[108] = float(us == chess.BLACK)

    # 50-move counter (normalised)
    planes[109] = board.halfmove_clock / 99.0

    # Plane 111 = all ones
    planes[111] = 1.0

    return planes


# ---------------------------------------------------------------------------
# Generate 100 diverse positions
# ---------------------------------------------------------------------------

def generate_positions(n: int = 100, seed: int = 42) -> list:
    """Return a list of (fen, chess.Board) by playing random games."""
    rng = random.Random(seed)
    positions = []
    seen = set()

    # Seed with a few recognisable openings
    openers = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
        "rnbqkb1r/pppppp1p/5np1/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3",
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    ]
    for fen in openers:
        b = chess.Board(fen)
        positions.append((fen, b))
        seen.add(fen)

    while len(positions) < n:
        b = chess.Board()
        depth = rng.randint(6, 50)
        for _ in range(depth):
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(rng.choice(moves))
        fen = b.fen()
        if fen not in seen and not b.is_game_over():
            positions.append((fen, b.copy()))
            seen.add(fen)

    return positions[:n]


# ---------------------------------------------------------------------------
# Main: load model, hook layers, run inference, save activations
# ---------------------------------------------------------------------------

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU:    {torch.cuda.get_device_name(0)}")
        print(f"VRAM:   {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # ---- Load network ----
    print("\nLoading Leela network...")
    t0 = time.time()
    model, n_blocks, n_filters = load_network(NETWORK_PATH)
    model = model.to(device).eval().half()   # FP16 — plenty accurate, saves VRAM
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Architecture : {n_blocks}x{n_filters} SE-ResNet")
    print(f"  Parameters   : {total_params:,}")
    print(f"  Loaded in    : {time.time()-t0:.1f}s")

    # ---- Register forward hooks ----
    captured = {}

    def hook(name):
        def fn(_, __, output):
            captured[name] = output.detach().float().cpu()
        return fn

    model.input_conv.register_forward_hook(hook("input_conv"))
    for i, blk in enumerate(model.blocks):
        blk.register_forward_hook(hook(f"block_{i}"))
    model.val_conv.register_forward_hook(hook("val_conv"))
    model.pol_conv.register_forward_hook(hook("pol_conv"))

    layer_names = (["input_conv"]
                   + [f"block_{i}" for i in range(n_blocks)]
                   + ["val_conv", "pol_conv"])

    # ---- Generate positions ----
    print("\nGenerating 100 test positions...")
    positions = generate_positions(100)
    print(f"  {len(positions)} positions ready")

    # ---- Inference ----
    all_acts = {k: [] for k in layer_names}
    values, fens = [], []

    print("\nRunning inference...")
    t0 = time.time()

    with torch.no_grad():
        for i, (fen, board) in enumerate(positions):
            x = torch.from_numpy(board_to_planes(board)).unsqueeze(0)
            x = x.to(device).half()

            policy, value = model(x)

            for name in layer_names:
                all_acts[name].append(captured[name])

            values.append(value.float().cpu().item())
            fens.append(fen)

            if (i + 1) % 25 == 0:
                print(f"  {i+1:>3}/100")

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.2f}s  ({len(positions)/elapsed:.0f} pos/s)")

    # ---- Stack and save ----
    stacked = {}
    print("\nActivation shapes:")
    for name in layer_names:
        arr = torch.cat(all_acts[name], dim=0).numpy()
        stacked[name] = arr
        print(f"  {name:>12s}  {str(arr.shape):>24s}  "
              f"mean={arr.mean():+.4f}  std={arr.std():.4f}")

    out_path = os.path.join(os.path.dirname(__file__),
                            "activations_100pos.npz")
    np.savez_compressed(out_path, fens=np.array(fens),
                        values=np.array(values), **stacked)
    mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\nSaved -> {out_path}  ({mb:.1f} MB)")

    # ---- Sanity checks ----
    print(f"\nSanity checks:")
    print(f"  Value range        : [{min(values):.3f}, {max(values):.3f}]")
    print(f"  Starting pos value : {values[0]:.4f}  (expect ~0)")
    last = stacked[f"block_{n_blocks-1}"]
    print(f"  Last block act norm: {np.linalg.norm(last, axis=1).mean():.1f}")
    print(f"\nPhase 0 step 1 complete. Ready for concept extraction.")


if __name__ == "__main__":
    main()
