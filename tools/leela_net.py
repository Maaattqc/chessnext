"""
Shared module: load any Lc0 classical/SE-ResNet into PyTorch.

Handles both NETWORK_CLASSICAL (no SE) and NETWORK_SE architectures.
Provides board encoding and weight decoding utilities.
"""

import gzip
import numpy as np
import chess
import torch
import torch.nn as nn
import torch.nn.functional as F

import net_pb2

# ---------------------------------------------------------------------------
# Weight decoding
# ---------------------------------------------------------------------------

def decode_layer(layer):
    """Decode an Lc0 LINEAR16-encoded weight tensor to float32."""
    if len(layer.params) == 0:
        return None
    raw = np.frombuffer(layer.params, dtype=np.uint16).astype(np.float32)
    return raw / 65535.0 * (layer.max_val - layer.min_val) + layer.min_val


# ---------------------------------------------------------------------------
# PyTorch modules
# ---------------------------------------------------------------------------

class ConvBlock(nn.Module):
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
        v = self.bn_stddivs.view(1, -1, 1, 1)
        m = self.bn_means.view(1, -1, 1, 1)
        g = self.bn_gammas.view(1, -1, 1, 1)
        b = self.bn_betas.view(1, -1, 1, 1)
        x = g * (x - m) / torch.sqrt(v + 1e-5) + b
        if self.use_relu:
            x = F.relu(x)
        return x


class SEBlock(nn.Module):
    def __init__(self, channels, se_channels):
        super().__init__()
        self.channels = channels
        self.fc1 = nn.Linear(channels, se_channels)
        self.fc2 = nn.Linear(se_channels, 2 * channels)

    def forward(self, x):
        b, c, _, _ = x.shape
        pooled = x.mean(dim=(2, 3))
        se = F.relu(self.fc1(pooled))
        se = self.fc2(se)
        gammas = torch.sigmoid(se[:, :c]).view(b, c, 1, 1)
        betas = se[:, c:].view(b, c, 1, 1)
        return gammas * x + betas


class ResBlock(nn.Module):
    def __init__(self, channels, se_channels=0):
        super().__init__()
        self.conv1 = ConvBlock(channels, channels, 3, use_relu=True)
        self.conv2 = ConvBlock(channels, channels, 3, use_relu=False)
        self.has_se = se_channels > 0
        if self.has_se:
            self.se = SEBlock(channels, se_channels)

    def forward(self, x):
        skip = x
        x = self.conv1(x)
        x = self.conv2(x)
        if self.has_se:
            x = self.se(x)
        return F.relu(x + skip)


class LeelaNet(nn.Module):
    def __init__(self, n_blocks, n_filters, se_ch, pol_ch):
        super().__init__()
        self.n_blocks = n_blocks
        self.n_filters = n_filters
        self.input_conv = ConvBlock(112, n_filters, 3)
        self.blocks = nn.ModuleList(
            [ResBlock(n_filters, se_ch) for _ in range(n_blocks)]
        )
        self.pol_conv = ConvBlock(n_filters, pol_ch, 1)
        self.pol_fc = nn.Linear(pol_ch * 64, 1858)
        self.val_conv = ConvBlock(n_filters, 32, 1)
        self.val_fc1 = nn.Linear(32 * 64, 128)
        self.val_fc2 = nn.Linear(128, 1)

    def forward(self, x):
        x = self.input_conv(x)
        for block in self.blocks:
            x = block(x)
        p = self.pol_fc(self.pol_conv(x).flatten(1))
        v = torch.tanh(self.val_fc2(F.relu(self.val_fc1(
            self.val_conv(x).flatten(1)))))
        return p, v


# ---------------------------------------------------------------------------
# Weight loading
# ---------------------------------------------------------------------------

def _load_conv(module, pb):
    w = decode_layer(pb.weights)
    if w is not None:
        module.conv.weight.data = torch.from_numpy(
            w.reshape(module.conv.weight.shape))
    for attr in ("bn_means", "bn_stddivs", "bn_gammas", "bn_betas"):
        arr = decode_layer(getattr(pb, attr))
        if arr is not None:
            getattr(module, attr).data = torch.from_numpy(arr)


def _load_fc(module, w_layer, b_layer):
    w = decode_layer(w_layer)
    b = decode_layer(b_layer)
    module.weight.data = torch.from_numpy(w.reshape(module.weight.shape))
    module.bias.data = torch.from_numpy(b)


def load_network(path):
    """Load any classical/SE Lc0 .pb.gz network. Returns (model, n_blocks, n_filters, se_ch)."""
    net = net_pb2.Net()
    with gzip.open(path, "rb") as f:
        net.ParseFromString(f.read())
    w = net.weights

    n_blocks = len(w.residual)
    n_filters = len(np.frombuffer(w.input.weights.params, np.uint16)) // (112 * 9)
    se_raw = np.frombuffer(w.residual[0].se.w1.params, np.uint16)
    se_ch = len(se_raw) // n_filters if len(se_raw) > 0 else 0
    pol_ch = len(np.frombuffer(w.policy.weights.params, np.uint16)) // n_filters

    model = LeelaNet(n_blocks, n_filters, se_ch, pol_ch)

    _load_conv(model.input_conv, w.input)

    for i, rpb in enumerate(w.residual):
        blk = model.blocks[i]
        _load_conv(blk.conv1, rpb.conv1)
        _load_conv(blk.conv2, rpb.conv2)
        if se_ch > 0:
            blk.se.fc1.weight.data = torch.from_numpy(
                decode_layer(rpb.se.w1).reshape(se_ch, n_filters))
            blk.se.fc1.bias.data = torch.from_numpy(decode_layer(rpb.se.b1))
            blk.se.fc2.weight.data = torch.from_numpy(
                decode_layer(rpb.se.w2).reshape(2 * n_filters, se_ch))
            blk.se.fc2.bias.data = torch.from_numpy(decode_layer(rpb.se.b2))

    _load_conv(model.pol_conv, w.policy)
    _load_fc(model.pol_fc, w.ip_pol_w, w.ip_pol_b)
    _load_conv(model.val_conv, w.value)
    _load_fc(model.val_fc1, w.ip1_val_w, w.ip1_val_b)
    _load_fc(model.val_fc2, w.ip2_val_w, w.ip2_val_b)

    return model, n_blocks, n_filters, se_ch


# ---------------------------------------------------------------------------
# Board encoding
# ---------------------------------------------------------------------------

PIECE_INDEX = {
    chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 2,
    chess.ROOK: 3, chess.QUEEN: 4, chess.KING: 5,
}


def board_to_planes(board: chess.Board) -> np.ndarray:
    """Encode a board as (112, 8, 8) float32 in Lc0 input format.

    Planes layout (T = 8 time steps × 13 planes + 8 meta):
      T1 planes 0-11:  current pieces (6 ours + 6 theirs)
      T1 plane 12:     repetition count
      T2 planes 13-24: 1 ply ago pieces
      T2 plane 25:     repetition
      ...  (8 time steps total)
      T8 planes 91-102: 7 plies ago pieces
      T8 plane 103:     repetition
      Planes 104-111:   meta (castling, side, halfmove, etc.)

    When no move history is available, the current position is repeated
    for all 8 time steps (standard Lc0 convention for single-position
    analysis).  Repetition planes stay 0.
    """
    planes = np.zeros((112, 8, 8), dtype=np.float32)
    us = board.turn

    # Encode current piece placement into planes 0-11
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        oriented = sq if us == chess.WHITE else chess.square_mirror(sq)
        row, col = divmod(oriented, 8)
        idx = PIECE_INDEX[piece.piece_type]
        if piece.color == us:
            planes[idx, row, col] = 1.0
        else:
            planes[6 + idx, row, col] = 1.0

    # Fill history slots (T2-T8) by repeating the current position.
    # Each time step is 13 planes: 12 piece planes + 1 repetition plane.
    # Repetition planes (12, 25, 38, ...) stay 0.
    current_pieces = planes[0:12].copy()
    for t in range(1, 8):
        offset = t * 13
        planes[offset:offset + 12] = current_pieces

    # Meta planes (104-111)
    our, their = (chess.WHITE, chess.BLACK) if us == chess.WHITE else (chess.BLACK, chess.WHITE)
    planes[104] = float(board.has_queenside_castling_rights(our))
    planes[105] = float(board.has_kingside_castling_rights(our))
    planes[106] = float(board.has_queenside_castling_rights(their))
    planes[107] = float(board.has_kingside_castling_rights(their))
    planes[108] = float(us == chess.BLACK)
    planes[109] = board.halfmove_clock / 99.0
    planes[111] = 1.0

    return planes


# ---------------------------------------------------------------------------
# Lc0 move encoding (index <-> UCI)
# ---------------------------------------------------------------------------

def _build_move_table():
    """Build the 1858-index move encoding table used by Lc0 classical policy."""
    moves = []
    # Queen moves (56 planes * 64 squares) — but Lc0 uses a specific encoding
    # Directions: N, NE, E, SE, S, SW, W, NW (8 dirs) x 7 distances = 56
    dirs = [(0, 1), (1, 1), (1, 0), (1, -1),
            (0, -1), (-1, -1), (-1, 0), (-1, 1)]
    for from_sq in range(64):
        fr, fc = divmod(from_sq, 8)
        for di, (dc, dr) in enumerate(dirs):
            for dist in range(1, 8):
                tr, tc = fr + dr * dist, fc + dc * dist
                if 0 <= tr < 8 and 0 <= tc < 8:
                    moves.append((from_sq, tr * 8 + tc))
    # Knight moves (8 planes * 64 squares)
    knight_deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                     (1, -2), (1, 2), (2, -1), (2, 1)]
    for from_sq in range(64):
        fr, fc = divmod(from_sq, 8)
        for dr, dc in knight_deltas:
            tr, tc = fr + dr, fc + dc
            if 0 <= tr < 8 and 0 <= tc < 8:
                moves.append((from_sq, tr * 8 + tc))
    # Under-promotions (3 pieces x 3 directions x 8 files)
    for piece in range(3):  # knight=0, bishop=1, rook=2
        for dc in [-1, 0, 1]:
            for fc in range(8):
                tc = fc + dc
                if 0 <= tc < 8:
                    moves.append((6 * 8 + fc, 7 * 8 + tc))  # rank 7 -> rank 8
    return moves

_MOVE_TABLE = _build_move_table()


def policy_index_to_move(idx: int, board: chess.Board) -> chess.Move:
    """Convert a policy index to a chess.Move for the given board."""
    us = board.turn
    from_sq, to_sq = _MOVE_TABLE[idx]
    if us == chess.BLACK:
        from_sq = chess.square_mirror(from_sq)
        to_sq = chess.square_mirror(to_sq)
    # Check for queen promotion (normal pawn push to back rank)
    piece = board.piece_at(from_sq)
    promo = None
    if piece and piece.piece_type == chess.PAWN:
        to_rank = chess.square_rank(to_sq)
        if to_rank == 0 or to_rank == 7:
            promo = chess.QUEEN
    return chess.Move(from_sq, to_sq, promotion=promo)


def get_top_moves(policy_logits: np.ndarray, board: chess.Board, k: int = 5):
    """Return top-k (move, probability) from policy logits, filtered to legal moves."""
    legal = set(board.legal_moves)
    probs = np.exp(policy_logits - policy_logits.max())
    probs /= probs.sum()

    ranked = np.argsort(probs)[::-1]
    results = []
    for idx in ranked:
        if len(results) >= k:
            break
        try:
            move = policy_index_to_move(int(idx), board)
            if move in legal:
                results.append((move, float(probs[idx])))
        except (IndexError, ValueError):
            continue
    return results
