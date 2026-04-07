"""
Lc0 Transformer loader for PyTorch.

Supports NETWORK_ATTENTIONBODY (format 7): 15-layer transformer encoder
with Smolgen attention biases, attention policy head, WDL value head.

Architecture (BT4-1024x15x32h):
  Input:  112 planes -> dense positional encoding -> embed(1024) -> gate -> FFN -> LN
  Encoder: 15x [LN1 -> MHA(32 heads, smolgen) -> LN2 -> FFN(1536)] (post-norm + DeepNorm)
  Policy:  attention-based (Q*K^T + promotions) -> 1858 moves
  Value:   embed(128) -> FC(128) -> FC(3) WDL
"""

import gzip
import math
import os

import chess
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import net_pb2

# ---------------------------------------------------------------------------
# Weight decoding
# ---------------------------------------------------------------------------

def _decode(layer):
    if len(layer.params) == 0:
        return None
    raw = np.frombuffer(layer.params, dtype=np.uint16).astype(np.float32)
    return raw / 65535.0 * (layer.max_val - layer.min_val) + layer.min_val


def _t(arr):
    """Return as torch tensor."""
    return torch.from_numpy(arr) if arr is not None else None


def mish(x):
    return x * torch.tanh(F.softplus(x))


def swish(x):
    return x * torch.sigmoid(x)


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

class Smolgen(nn.Module):
    """Generates per-head attention biases from encoder input."""

    def __init__(self, embed, heads, hidden_ch, gen_sz, smolgen_act=swish):
        super().__init__()
        self.heads = heads
        self.gen_sz = gen_sz
        self.act = smolgen_act
        self.compress = nn.Linear(embed, hidden_ch, bias=False)  # 1024->32
        self.dense1 = nn.Linear(64 * hidden_ch, 256)             # 2048->256
        self.ln1 = nn.LayerNorm(256, eps=1e-3)
        self.dense2 = nn.Linear(256, heads * gen_sz)             # 256->heads*gen_sz
        self.ln2 = nn.LayerNorm(heads * gen_sz, eps=1e-3)
        # global_w is set externally (shared across layers)
        self.global_w = None  # (gen_sz, 4096)

    def forward(self, x, B):
        # x: (B*64, embed)
        c = self.compress(x)                          # (B*64, hidden_ch)
        c = c.reshape(B, -1)                          # (B, 64*hidden_ch)
        h = self.act(self.dense1(c))                  # (B, 256)
        h = self.ln1(h)
        g = self.act(self.dense2(h))                  # (B, heads*gen_sz)
        g = self.ln2(g)
        g = g.reshape(B, self.heads, self.gen_sz)     # (B, heads, gen_sz)
        out = g @ self.global_w                       # (B, heads, 4096)
        return out.reshape(B, self.heads, 64, 64)     # (B, heads, 64, 64)


class EncoderLayer(nn.Module):
    def __init__(self, embed, heads, ffn_dim, alpha, smol_hidden, smol_gen_sz,
                 smolgen_act=swish):
        super().__init__()
        self.embed = embed
        self.heads = heads
        self.depth = embed // heads
        self.alpha = alpha

        # MHA
        self.q = nn.Linear(embed, embed)
        self.k = nn.Linear(embed, embed)
        self.v = nn.Linear(embed, embed)
        self.dense = nn.Linear(embed, embed)
        self.ln1 = nn.LayerNorm(embed, eps=1e-3)

        # FFN
        self.ffn1 = nn.Linear(embed, ffn_dim)
        self.ffn2 = nn.Linear(ffn_dim, embed)
        self.ln2 = nn.LayerNorm(embed, eps=1e-3)

        # Smolgen
        self.smolgen = Smolgen(embed, heads, smol_hidden, smol_gen_sz,
                               smolgen_act=smolgen_act)

    def forward(self, x, B):
        # x: (B*64, embed)
        residual = x

        # MHA
        Q = self.q(x).reshape(B, 64, self.heads, self.depth).permute(0, 2, 1, 3)
        K = self.k(x).reshape(B, 64, self.heads, self.depth).permute(0, 2, 1, 3)
        V = self.v(x).reshape(B, 64, self.heads, self.depth).permute(0, 2, 1, 3)

        attn = (Q @ K.transpose(-2, -1)) / math.sqrt(self.depth)

        # Smolgen bias
        smol_bias = self.smolgen(x, B)
        attn = attn + smol_bias

        attn = F.softmax(attn, dim=-1)
        out = (attn @ V).permute(0, 2, 1, 3).reshape(B * 64, self.embed)
        out = self.dense(out)

        # Post-norm with DeepNorm
        x = self.ln1(out * self.alpha + residual)

        # FFN
        residual = x
        out = mish(self.ffn1(x))
        out = self.ffn2(out)
        x = self.ln2(out * self.alpha + residual)

        return x


class LeelaTransformer(nn.Module):
    def __init__(self, n_enc, embed, heads, ffn_dim,
                 smol_hidden, smol_gen_sz, emb_dense_sz,
                 smolgen_act=swish):
        super().__init__()
        self.n_enc = n_enc
        self.embed = embed
        self.heads = heads
        alpha = (2.0 * n_enc) ** -0.25

        # Input embedding
        self.preproc = nn.Linear(64 * 12, 64 * emb_dense_sz)
        self.emb = nn.Linear(112 + emb_dense_sz, embed)
        self.emb_ln = nn.LayerNorm(embed, eps=1e-3)

        # Gating
        self.mult_gate = nn.Parameter(torch.ones(64, embed))
        self.add_gate = nn.Parameter(torch.zeros(64, embed))

        # Embedding FFN
        self.emb_ffn1 = nn.Linear(embed, ffn_dim)
        self.emb_ffn2 = nn.Linear(ffn_dim, embed)
        self.emb_ffn_ln = nn.LayerNorm(embed, eps=1e-3)
        self.emb_alpha = alpha

        # Encoder
        self.encoders = nn.ModuleList([
            EncoderLayer(embed, heads, ffn_dim, alpha, smol_hidden, smol_gen_sz,
                         smolgen_act=smolgen_act)
            for _ in range(n_enc)
        ])

        # Global smolgen weight (shared)
        self.smolgen_w = nn.Parameter(torch.zeros(smol_gen_sz, 4096))

        # Policy attention head
        self.pol_emb = nn.Linear(embed, embed)
        self.pol_q = nn.Linear(embed, embed)
        self.pol_k = nn.Linear(embed, embed)
        self.pol_ppo = nn.Linear(embed, 4)  # promotion offsets

        # Value WDL head
        self.val_emb = nn.Linear(embed, 128)
        self.val_fc1 = nn.Linear(128 * 64, 128)
        self.val_fc2 = nn.Linear(128, 3)

        # Moves left head
        self.ml_emb = nn.Linear(embed, 32)
        self.ml_fc1 = nn.Linear(32 * 64, 128)
        self.ml_fc2 = nn.Linear(128, 1)

    def forward(self, planes):
        """Forward pass. planes: (B, 112, 8, 8)."""
        B = planes.shape[0]

        # 1. Input embedding
        x = planes.permute(0, 2, 3, 1).reshape(B, 64, 112)

        # Dense positional encoding from pieces (first 12 planes)
        pos = x[:, :, :12].reshape(B, 768)
        pos = self.preproc(pos)                                 # (B, 64*emb_dense)
        emb_dense_sz = pos.shape[1] // 64
        pos = pos.reshape(B, 64, emb_dense_sz)
        x = torch.cat([x, pos], dim=2)                         # (B, 64, 112+emb_dense)

        # Embed + activation + LN
        x = x.reshape(B * 64, -1)
        x = mish(self.emb(x))
        x = self.emb_ln(x)
        x = x.reshape(B, 64, self.embed)

        # Gating
        x = x * self.mult_gate + self.add_gate                 # (B, 64, embed)
        x = x.reshape(B * 64, self.embed)

        # Embedding FFN (post-norm + DeepNorm)
        residual = x
        x = mish(self.emb_ffn1(x))
        x = self.emb_ffn2(x)
        x = self.emb_ffn_ln(x * self.emb_alpha + residual)

        # 2. Encoder
        for enc in self.encoders:
            enc.smolgen.global_w = self.smolgen_w
            x = enc(x, B)

        # 3. Policy head (attention-based)
        pol = mish(self.pol_emb(x))                             # (B*64, embed)
        Q = self.pol_q(pol).reshape(B, 64, self.embed)
        K = self.pol_k(pol).reshape(B, 64, self.embed)
        attn = (Q @ K.transpose(-1, -2)) / math.sqrt(self.embed)  # (B, 64, 64)

        # Promotion offsets
        K_last = K[:, 56:64, :]                                 # (B, 8, embed)
        prom = self.pol_ppo(K_last)                             # (B, 8, 4)
        prom = prom.permute(0, 2, 1)                            # (B, 4, 8)
        # Knight offset added to Q/R/B
        prom_offsets = prom[:, :3, :] + prom[:, 3:4, :]         # (B, 3, 8)

        base_prom = attn[:, 48:56, 56:64]                       # (B, 8, 8)
        promo_logits = torch.cat([
            (base_prom + prom_offsets[:, i:i+1, :]).unsqueeze(1)
            for i in range(3)
        ], dim=1)                                                # (B, 3, 8, 8)
        promo_logits = promo_logits.reshape(B, 3 * 8 * 8)       # (B, 192)

        flat_attn = attn.reshape(B, 64 * 64)                    # (B, 4096)
        raw_policy = torch.cat([flat_attn, promo_logits], dim=1) # (B, 4288)

        # Map 4288 -> 1858 via policy map (set externally)
        policy = raw_policy[:, self.policy_map]                  # (B, 1858)

        # 4. Value WDL head
        v = mish(self.val_emb(x))                                # (B*64, 128)
        v = v.reshape(B, 128 * 64)
        v = mish(self.val_fc1(v))
        v = self.val_fc2(v)                                      # (B, 3) WDL logits

        return policy, v


# ---------------------------------------------------------------------------
# Weight loading
# ---------------------------------------------------------------------------

def _load_linear(module, w_layer, b_layer):
    w = _decode(w_layer)
    b = _decode(b_layer)
    module.weight.data = torch.from_numpy(w.reshape(module.weight.shape))
    if b is not None:
        module.bias.data = torch.from_numpy(b)


def _load_ln(module, g_layer, b_layer):
    module.weight.data = _t(_decode(g_layer))
    module.bias.data = _t(_decode(b_layer))


def _load_smolgen(smol_module, smol_pb):
    smol_module.compress.weight.data = _t(
        _decode(smol_pb.compress).reshape(smol_module.compress.weight.shape))
    _load_linear(smol_module.dense1, smol_pb.dense1_w, smol_pb.dense1_b)
    _load_ln(smol_module.ln1, smol_pb.ln1_gammas, smol_pb.ln1_betas)
    _load_linear(smol_module.dense2, smol_pb.dense2_w, smol_pb.dense2_b)
    _load_ln(smol_module.ln2, smol_pb.ln2_gammas, smol_pb.ln2_betas)


def load_transformer(path):
    """Load an Lc0 transformer network from .pb.gz. Returns model."""
    net = net_pb2.Net()
    with gzip.open(path, "rb") as f:
        net.ParseFromString(f.read())
    w = net.weights
    fmt = net.format.network_format

    n_enc = len(w.encoder)
    heads = w.headcount
    q_w = _decode(w.encoder[0].mha.q_w)
    embed = int(math.sqrt(len(q_w)))
    ffn_dim = len(np.frombuffer(w.encoder[0].ffn.dense1_b.params, np.uint16))

    # Smolgen dimensions
    smol_hidden = len(np.frombuffer(w.encoder[0].mha.smolgen.compress.params, np.uint16)) // embed
    smol_dense2_b = len(np.frombuffer(w.encoder[0].mha.smolgen.dense2_b.params, np.uint16))
    smol_gen_sz = smol_dense2_b // heads

    # Embedding dense size
    preproc_b_sz = len(np.frombuffer(w.ip_emb_preproc_b.params, np.uint16))
    emb_dense_sz = preproc_b_sz // 64

    # Determine activation functions from network format
    _ACT_MAP = {0: None, 1: mish, 2: F.relu, 3: None, 4: torch.tanh,
                5: torch.sigmoid, 6: F.selu, 7: swish}
    default_act = mish if fmt.default_activation == 1 else F.relu
    smol_act_id = fmt.smolgen_activation
    smolgen_act = _ACT_MAP.get(smol_act_id, default_act) or default_act
    ffn_act_id = fmt.ffn_activation
    ffn_act = _ACT_MAP.get(ffn_act_id, default_act) or default_act

    print(f"  Transformer: {n_enc}x{embed}, {heads} heads, FFN={ffn_dim}")
    print(f"  Smolgen: hidden={smol_hidden}, gen_sz={smol_gen_sz}, act={smolgen_act.__name__}")
    print(f"  FFN act: {ffn_act.__name__}, default act: {default_act.__name__}")
    print(f"  Emb dense: {emb_dense_sz}")

    model = LeelaTransformer(
        n_enc, embed, heads, ffn_dim, smol_hidden, smol_gen_sz, emb_dense_sz,
        smolgen_act=smolgen_act)

    # --- Input embedding ---
    _load_linear(model.preproc, w.ip_emb_preproc_w, w.ip_emb_preproc_b)
    _load_linear(model.emb, w.ip_emb_w, w.ip_emb_b)
    _load_ln(model.emb_ln, w.ip_emb_ln_gammas, w.ip_emb_ln_betas)

    # Gates (stored transposed: (embed, 64) -> need (64, embed))
    mg = _decode(w.ip_mult_gate).reshape(embed, 64).T
    ag = _decode(w.ip_add_gate).reshape(embed, 64).T
    model.mult_gate.data = torch.from_numpy(mg.copy())
    model.add_gate.data = torch.from_numpy(ag.copy())

    # Embedding FFN
    _load_linear(model.emb_ffn1, w.ip_emb_ffn.dense1_w, w.ip_emb_ffn.dense1_b)
    _load_linear(model.emb_ffn2, w.ip_emb_ffn.dense2_w, w.ip_emb_ffn.dense2_b)
    _load_ln(model.emb_ffn_ln, w.ip_emb_ffn_ln_gammas, w.ip_emb_ffn_ln_betas)

    # Global smolgen weight (stored as (4096, gen_sz) in Lc0, transposed for matmul)
    smol_w = _decode(w.smolgen_w).reshape(4096, smol_gen_sz).T.copy()
    model.smolgen_w.data = torch.from_numpy(smol_w)

    # --- Encoder layers ---
    for i, epb in enumerate(w.encoder):
        enc = model.encoders[i]
        _load_linear(enc.q, epb.mha.q_w, epb.mha.q_b)
        _load_linear(enc.k, epb.mha.k_w, epb.mha.k_b)
        _load_linear(enc.v, epb.mha.v_w, epb.mha.v_b)
        _load_linear(enc.dense, epb.mha.dense_w, epb.mha.dense_b)
        _load_ln(enc.ln1, epb.ln1_gammas, epb.ln1_betas)
        _load_linear(enc.ffn1, epb.ffn.dense1_w, epb.ffn.dense1_b)
        _load_linear(enc.ffn2, epb.ffn.dense2_w, epb.ffn.dense2_b)
        _load_ln(enc.ln2, epb.ln2_gammas, epb.ln2_betas)
        _load_smolgen(enc.smolgen, epb.mha.smolgen)

    # --- Policy head ---
    ph = w.policy_heads
    _load_linear(model.pol_emb, ph.ip_pol_w, ph.ip_pol_b)
    v = ph.vanilla
    _load_linear(model.pol_q, v.ip2_pol_w, v.ip2_pol_b)
    _load_linear(model.pol_k, v.ip3_pol_w, v.ip3_pol_b)
    # ppo has no bias in proto (4096 params = embed*4 = 1024*4)
    ppo_w = _decode(v.ip4_pol_w).reshape(4, embed).T  # (embed, 4) for Linear
    model.pol_ppo.weight.data = torch.from_numpy(ppo_w.T.copy())

    # --- Value WDL head ---
    vh = w.value_heads.winner
    _load_linear(model.val_emb, vh.ip_val_w, vh.ip_val_b)
    _load_linear(model.val_fc1, vh.ip1_val_w, vh.ip1_val_b)
    _load_linear(model.val_fc2, vh.ip2_val_w, vh.ip2_val_b)

    # --- Moves left head ---
    _load_linear(model.ml_emb, w.ip_mov_w, w.ip_mov_b)
    _load_linear(model.ml_fc1, w.ip1_mov_w, w.ip1_mov_b)
    _load_linear(model.ml_fc2, w.ip2_mov_w, w.ip2_mov_b)

    return model, n_enc, embed


# ---------------------------------------------------------------------------
# Board encoding (same as ResNet - reuse from leela_net)
# ---------------------------------------------------------------------------

from leela_net import board_to_planes  # noqa: E402
