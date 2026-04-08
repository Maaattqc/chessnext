"""
Batched MCTS — 10-20x faster than naive implementation.

Key optimization: instead of evaluating one leaf at a time (800 individual
GPU calls), we run "virtual loss" MCTS that selects multiple leaves per
batch, evaluates them together in one GPU call, then backpropagates.

800 simulations with batch_size=32 = only 25 GPU calls instead of 800.
"""

import math
from typing import Optional

import chess
import numpy as np
import torch

C_PUCT = 2.5
FPU_VALUE = 0.0
DIRICHLET_ALPHA = 0.3
DIRICHLET_EPSILON = 0.25


class Node:
    __slots__ = ["parent", "move", "prior", "children",
                 "visits", "value_sum", "expanded"]

    def __init__(self, parent, move, prior):
        self.parent = parent
        self.move = move
        self.prior = prior
        self.children: list["Node"] = []
        self.visits = 0
        self.value_sum = 0.0
        self.expanded = False

    @property
    def value(self):
        return self.value_sum / self.visits if self.visits > 0 else FPU_VALUE

    def ucb(self, parent_visits):
        # Negate self.value: child stores value from ITS side-to-move (opponent),
        # but we need Q from the PARENT's perspective (AlphaZero PUCT formula).
        return -self.value + C_PUCT * self.prior * math.sqrt(parent_visits) / (1 + self.visits)

    def best_child(self):
        return max(self.children, key=lambda c: c.ucb(self.visits))

    def most_visited(self):
        return max(self.children, key=lambda c: c.visits)


class BatchMCTS:
    """MCTS with batched neural network evaluation."""

    def __init__(self, model, device, policy_map, num_sims=800, batch_size=32):
        self.model = model
        self.device = device
        self.policy_map = policy_map
        self.num_sims = num_sims
        self.batch_size = batch_size
        self.dtype = next(model.parameters()).dtype

        # Build reverse policy map for fast lookup
        self._reverse_map = {}
        for pidx, attn in enumerate(policy_map):
            self._reverse_map[int(attn)] = pidx

    def _board_to_tensor(self, board):
        from leela_net import board_to_planes
        return board_to_planes(board)

    def _evaluate_batch(self, boards):
        """Evaluate multiple positions in one GPU call."""
        if not boards:
            return [], []

        planes = np.stack([self._board_to_tensor(b) for b in boards])
        x = torch.from_numpy(planes).to(device=self.device, dtype=self.dtype)

        with torch.no_grad():
            pol_logits, val_logits = self.model(x)

        pol_np = pol_logits.float().cpu().numpy()
        val_np = val_logits.float().cpu().numpy()

        policies = []
        values = []

        for i, board in enumerate(boards):
            # Policy: map to legal moves
            probs = np.exp(pol_np[i] - pol_np[i].max())
            probs /= probs.sum()

            flip = board.turn == chess.BLACK
            policy = {}
            for move in board.legal_moves:
                from_sq = move.from_square
                to_sq = move.to_square
                if flip:
                    from_sq = chess.square_mirror(from_sq)
                    to_sq = chess.square_mirror(to_sq)

                attn_idx = from_sq * 64 + to_sq
                pidx = self._reverse_map.get(attn_idx)
                if pidx is not None:
                    policy[move] = float(probs[pidx])
                else:
                    policy[move] = 1e-6

            total = sum(policy.values())
            if total > 0:
                policy = {m: p / total for m, p in policy.items()}
            policies.append(policy)

            # Value: WDL -> scalar
            wdl = np.exp(val_np[i] - val_np[i].max())
            wdl /= wdl.sum()
            values.append(float(wdl[0] - wdl[2]))

        return policies, values

    def _get_activation_batch(self, boards):
        """Get pooled activations for multiple positions in one call."""
        if not boards:
            return []

        captured = {}
        def hook(_, __, out):
            captured["act"] = out.detach().float().cpu()
        handle = self.model.encoders[self.model.n_enc - 1].register_forward_hook(hook)

        planes = np.stack([self._board_to_tensor(b) for b in boards])
        x = torch.from_numpy(planes).to(device=self.device, dtype=self.dtype)
        with torch.no_grad():
            self.model(x)
        handle.remove()

        B = len(boards)
        acts = captured["act"].numpy().reshape(B, 64, 1024).mean(axis=1)
        return [acts[i] for i in range(B)]

    def search(self, board: chess.Board) -> Node:
        """Run batched MCTS. Returns root node."""
        root = Node(None, None, 1.0)

        # Expand root
        policies, values = self._evaluate_batch([board])
        self._expand(root, policies[0])
        self._backprop(root, values[0])

        # Dirichlet noise at root
        if root.children:
            noise = np.random.dirichlet([DIRICHLET_ALPHA] * len(root.children))
            for child, n in zip(root.children, noise):
                child.prior = (1 - DIRICHLET_EPSILON) * child.prior + DIRICHLET_EPSILON * n

        # Batched simulations
        remaining = self.num_sims - 1
        while remaining > 0:
            batch_sz = min(self.batch_size, remaining)
            leaves = []
            leaf_boards = []
            leaf_paths = []

            for _ in range(batch_sz):
                # SELECT
                node = root
                b = board.copy()
                path = [root]

                while node.expanded and node.children:
                    node = node.best_child()
                    b.push(node.move)
                    path.append(node)

                    # Virtual loss: make child look good from ITS perspective
                    # so parent's UCB (-child.value) decreases, discouraging re-visits.
                    node.visits += 1
                    node.value_sum += 1.0

                if b.is_game_over():
                    # Terminal: undo virtual loss and backprop real value
                    node.visits -= 1
                    node.value_sum -= 1.0
                    result = b.result()
                    if result == "1-0":
                        v = 1.0 if b.turn == chess.BLACK else -1.0
                    elif result == "0-1":
                        v = 1.0 if b.turn == chess.WHITE else -1.0
                    else:
                        v = 0.0
                    self._backprop(node, v)
                    remaining -= 1
                    continue

                leaves.append(node)
                leaf_boards.append(b)
                leaf_paths.append(path)

            if not leaves:
                remaining -= batch_sz
                continue

            # BATCH EVALUATE
            policies, values = self._evaluate_batch(leaf_boards)

            # EXPAND + BACKPROP
            for j, (node, policy, value, path) in enumerate(
                    zip(leaves, policies, values, leaf_paths)):
                # Undo virtual loss
                node.visits -= 1
                node.value_sum -= 1.0
                # Expand
                self._expand(node, policy)
                # Backprop
                self._backprop(node, value)

            remaining -= len(leaves)

        return root

    def _expand(self, node, policy):
        node.expanded = True
        for move, prior in policy.items():
            node.children.append(Node(node, move, prior))

    def _backprop(self, node, value):
        while node is not None:
            node.visits += 1
            node.value_sum += value
            value = -value
            node = node.parent

    def get_optimal_path(self, root, board, max_depth=20):
        """Most-visited path with activations."""
        path_boards = []
        path_nodes = []
        node = root
        b = board.copy()
        moves = []

        for _ in range(max_depth):
            if not node.children:
                break
            node = node.most_visited()
            b.push(node.move)
            path_boards.append(b.copy())
            path_nodes.append(node)
            moves.append(node.move)
            if b.is_game_over():
                break

        # Batch activation extraction
        acts = self._get_activation_batch(path_boards) if path_boards else []

        result = []
        b2 = board.copy()
        for i, (move, act) in enumerate(zip(moves, acts)):
            san = b2.san(move)
            b2.push(move)
            result.append({
                "move": move, "san": san, "activation": act,
                "visits": path_nodes[i].visits,
            })

        return result

    def get_suboptimal_path(self, root, board, min_value_diff=0.1,
                            min_visit_ratio=0.05, max_depth=20):
        """High-visit alternative branch."""
        if not root.children or len(root.children) < 2:
            return None

        sorted_ch = sorted(root.children, key=lambda c: c.visits, reverse=True)
        best = sorted_ch[0]

        for child in sorted_ch[1:]:
            if child.visits < 2:
                continue
            vdiff = abs(best.value - child.value)
            vratio = child.visits / max(best.visits, 1)
            if vdiff >= min_value_diff and vratio >= min_visit_ratio:
                # Follow this branch
                path_boards = []
                node = child
                b = board.copy()
                b.push(node.move)
                path_boards.append(b.copy())
                moves = [node.move]

                for _ in range(max_depth - 1):
                    if not node.children:
                        break
                    node = node.most_visited()
                    b.push(node.move)
                    path_boards.append(b.copy())
                    moves.append(node.move)
                    if b.is_game_over():
                        break

                acts = self._get_activation_batch(path_boards)
                result = []
                b2 = board.copy()
                for move, act in zip(moves, acts):
                    san = b2.san(move)
                    b2.push(move)
                    result.append({
                        "move": move, "san": san, "activation": act,
                        "visits": child.visits,
                    })
                return result

        return None

    def get_weak_path(self, root, board, weak_move, min_visits=20, max_depth=20):
        """Follow the weak network's preferred move in the existing MCTS tree.

        Returns path starting from weak_move if it has enough visits, else None.
        """
        weak_node = None
        for child in root.children:
            if child.move == weak_move:
                weak_node = child
                break

        if weak_node is None or weak_node.visits < min_visits:
            return None

        path_boards = []
        path_nodes = []
        moves = []

        b = board.copy()
        node = weak_node
        b.push(node.move)
        path_boards.append(b.copy())
        path_nodes.append(node)
        moves.append(node.move)

        for _ in range(max_depth - 1):
            if not node.children:
                break
            node = node.most_visited()
            b.push(node.move)
            path_boards.append(b.copy())
            path_nodes.append(node)
            moves.append(node.move)
            if b.is_game_over():
                break

        acts = self._get_activation_batch(path_boards) if path_boards else []

        result = []
        b2 = board.copy()
        for i, (move, act) in enumerate(zip(moves, acts)):
            san = b2.san(move)
            b2.push(move)
            result.append({
                "move": move, "san": san, "activation": act,
                "visits": path_nodes[i].visits,
            })

        return result

    def search_from_move(self, board, forced_move, num_sims=200, max_depth=20):
        """Run MCTS after forcing a specific first move.

        Used when the forced move has insufficient visits in the main tree.
        """
        b = board.copy()
        b.push(forced_move)

        if b.is_game_over():
            return None

        old_sims = self.num_sims
        self.num_sims = num_sims
        root = self.search(b)
        self.num_sims = old_sims

        cont_path = self.get_optimal_path(root, b, max_depth=max_depth - 1)
        if not cont_path:
            return None

        # Prepend the forced move with its activation
        forced_act = self._get_activation_batch([b])[0]
        forced_san = board.san(forced_move)

        return [{
            "move": forced_move, "san": forced_san, "activation": forced_act,
            "visits": num_sims,
        }] + cont_path
