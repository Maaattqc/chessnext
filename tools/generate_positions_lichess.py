#!/usr/bin/env python3
"""
Generate 50K diverse chess positions from realistic games.

Sources (in priority order):
  1. Lichess API: download 200 rated games from top players
  2. Fallback: simulate 1000+ games from 50 common openings using
     weighted-random play (captures/checks biased) for realism

Positions are extracted at moves 10, 15, 20, 25, 30, 35, 40 from each game,
then filtered for quality:
  - At least 4 legal moves (not forced/trivial)
  - Game not over
  - At least 10 pieces on the board (skip ultra-endgames)
  - No duplicate FENs

Output: tools/positions_50k.npz  (contains 'fens' array)

Usage:
    .venv/Scripts/python.exe generate_positions_lichess.py
"""

import io
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

import chess
import chess.pgn
import numpy as np

TOOLS = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(TOOLS, "positions_50k.npz")
TARGET_POSITIONS = 50_000

# Plies at which to sample positions from each game.
# Mix of even (white to move) and odd (black to move) for balanced coverage.
SAMPLE_PLIES = [19, 20, 29, 30, 39, 40, 49, 50, 59, 60, 69, 70, 79, 80]

# Minimum requirements for a position to be included
MIN_LEGAL_MOVES = 4
MIN_PIECES = 10

# ---------------------------------------------------------------------------
# Lichess API: download real games
# ---------------------------------------------------------------------------

# Top players to sample games from (mix of styles, eras, time controls)
LICHESS_PLAYERS = [
    "DrNykterstein",    # Magnus Carlsen
    "alireza2003",      # Alireza Firouzja
    "nihalsarin",       # Nihal Sarin
    "Msb2",             # Maxime Vachier-Lagrave
    "Zhigalko_Sergei",  # Sergei Zhigalko
    "Polish_fighter3000",# Jan-Krzysztof Duda
    "DrDrunkenstein",   # Magnus Carlsen (bullet alt)
    "Jospem",           # Jose Martinez Alcantara
    "Bombegansen",      # Magnus Carlsen (another alt)
    "opperwezen",       # Jorden van Foreest
    "UZBCHESS",         # Nodirbek Abdusattorov
    "penguingim1",      # Andrew Tang
    "Kastansen",        # Magnus Carlsen
    "howitzer14",       # Daniel Naroditsky
    "Fins",             # John Bartholomew
    "Hikaru",           # Hikaru Nakamura
    "LachesisQ",        # Ian Nepomniachtchi
    "may6enexttime",    # Maxim Matlakov
    "EricRosen",        # Eric Rosen
    "GothamChess",      # Levy Rozman
]

# Games per player, time controls to request
GAMES_PER_PLAYER = 30
LICHESS_PERFTYPES = "classical,rapid,blitz"


def download_lichess_games(max_total=500, timeout=15):
    """Try to download PGN games from Lichess API. Returns list of PGN strings."""
    all_pgns = []
    players_tried = 0

    for player in LICHESS_PLAYERS:
        if len(all_pgns) >= max_total:
            break
        url = (
            f"https://lichess.org/api/games/user/{player}"
            f"?max={GAMES_PER_PLAYER}&rated=true"
            f"&perfType={LICHESS_PERFTYPES}"
            f"&moves=true&clocks=false&evals=false&opening=false"
        )
        req = urllib.request.Request(url, headers={
            "Accept": "application/x-chess-pgn",
            "User-Agent": "chessnext-concept-extraction/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            # Split into individual games
            games = [g.strip() for g in raw.split("\n\n\n") if g.strip()]
            # Each PGN has header block + move block separated by \n\n
            # Re-join properly
            pgn_text = raw.strip()
            if pgn_text:
                all_pgns.append(pgn_text)
                players_tried += 1
                # Count games roughly
                n_games = pgn_text.count("[Event ")
                print(f"  {player}: {n_games} games downloaded")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f"  {player}: FAILED ({e})")
            continue

    print(f"  Total: downloaded from {players_tried} players")
    return all_pgns


def parse_pgn_positions(pgn_texts):
    """Parse PGN text blocks and extract positions at target plies."""
    positions = []
    seen = set()
    total_games = 0

    for pgn_text in pgn_texts:
        pgn_io = io.StringIO(pgn_text)
        while True:
            game = chess.pgn.read_game(pgn_io)
            if game is None:
                break
            total_games += 1

            board = game.board()
            ply = 0
            for move in game.mainline_moves():
                board.push(move)
                ply += 1
                if ply in SAMPLE_PLIES:
                    fen = board.fen()
                    if _position_ok(board, fen, seen):
                        positions.append(fen)
                        seen.add(fen)

    return positions, seen, total_games


# ---------------------------------------------------------------------------
# Fallback: opening book + weighted random play
# ---------------------------------------------------------------------------

# 50 common openings as move sequences (UCI notation)
# Covers: Sicilian, French, Caro-Kann, Pirc, Scandinavian, QGD, QGA,
#         Slav, KID, Nimzo, QID, Grunfeld, Dutch, English, Reti,
#         Italian, Ruy Lopez, Scotch, Petroff, Vienna, etc.
OPENINGS = [
    # Sicilian variants
    ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "a7a6"],  # Najdorf
    ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "e7e5"],  # Sveshnikov
    ["e2e4", "c7c5", "g1f3", "b8c6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "e7e5"],  # Classical Sicilian
    ["e2e4", "c7c5", "g1f3", "e7e6", "d2d4", "c5d4", "f3d4", "a7a6", "f1d3"],          # Kan
    ["e2e4", "c7c5", "g1f3", "b8c6", "f1b5"],                                            # Rossolimo
    ["e2e4", "c7c5", "b1c3", "b8c6", "g2g3"],                                            # Closed Sicilian

    # French Defense
    ["e2e4", "e7e6", "d2d4", "d7d5", "b1c3", "g8f6", "c1g5"],                           # Classical French
    ["e2e4", "e7e6", "d2d4", "d7d5", "e4e5", "c7c5", "c2c3", "b8c6", "g1f3"],          # Advance French
    ["e2e4", "e7e6", "d2d4", "d7d5", "b1d2", "g8f6", "e4e5"],                           # Tarrasch French
    ["e2e4", "e7e6", "d2d4", "d7d5", "e4d5", "e6d5"],                                    # Exchange French

    # Caro-Kann
    ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4", "c8f5"],                  # Classical CK
    ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5", "g1f3"],                           # Advance CK
    ["e2e4", "c7c6", "d2d4", "d7d5", "e4d5", "c6d5", "f1d3"],                           # Exchange CK

    # Queen's Gambit
    ["d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "c1g5", "f8e7"],                  # QGD Orthodox
    ["d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "g1f3", "c7c5"],                  # QGD Tarrasch
    ["d2d4", "d7d5", "c2c4", "d5c4", "g1f3", "g8f6", "e2e3", "e7e6"],                  # QGA
    ["d2d4", "d7d5", "c2c4", "c7c6", "g1f3", "g8f6", "b1c3", "e7e6"],                  # Semi-Slav
    ["d2d4", "d7d5", "c2c4", "c7c6", "g1f3", "g8f6", "e2e3", "c8f5"],                  # Slav

    # King's Indian Defense
    ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7", "e2e4", "d7d6", "g1f3", "e8g8"],  # Classical KID
    ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7", "e2e4", "d7d6", "f2f3"],          # Samisch KID
    ["d2d4", "g8f6", "c2c4", "g7g6", "g2g3", "f8g7", "f1g2", "d7d6"],                  # Fianchetto KID

    # Nimzo-Indian
    ["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4", "e2e3", "e8g8"],                  # Rubinstein Nimzo
    ["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4", "d1c2"],                           # Classical Nimzo

    # Queen's Indian
    ["d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "b7b6", "g2g3", "c8b7"],                  # QID
    ["d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "b7b6", "a2a3"],                           # Petrosian QID

    # Grunfeld
    ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5", "c4d5", "f6d5", "e2e4", "d5c3"],  # Exchange Grunfeld
    ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5", "g1f3"],                           # Russian Grunfeld

    # Italian / Giuoco Piano
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4"],          # Italian
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "d2d3"],                           # Giuoco Pianissimo

    # Ruy Lopez
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1"],          # Closed Ruy Lopez
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1", "f8e7"],  # Marshall-ready
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "g8f6"],                                    # Berlin Defense
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "f7f5"],                                    # Schliemann

    # Scotch
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "f3d4"],                           # Scotch Game

    # Petroff
    ["e2e4", "e7e5", "g1f3", "g8f6", "f3e5", "d7d6", "e5f3", "f6e4"],                  # Petroff Classical
    ["e2e4", "e7e5", "g1f3", "g8f6", "d2d4"],                                            # Petroff Steinitz

    # Vienna
    ["e2e4", "e7e5", "b1c3", "g8f6", "f1c4"],                                            # Vienna Game
    ["e2e4", "e7e5", "b1c3", "b8c6", "g2g3"],                                            # Vienna Gambit

    # English Opening
    ["c2c4", "e7e5", "b1c3", "g8f6", "g1f3", "b8c6"],                                   # English Four Knights
    ["c2c4", "g8f6", "b1c3", "e7e5", "g2g3"],                                            # English, Reversed Sicilian
    ["c2c4", "c7c5", "g1f3", "b8c6", "g2g3"],                                            # Symmetrical English

    # Reti
    ["g1f3", "d7d5", "g2g3", "g8f6", "f1g2", "c7c6"],                                   # Reti Opening
    ["g1f3", "d7d5", "c2c4", "d5c4"],                                                     # Reti Gambit

    # Pirc / Modern
    ["e2e4", "d7d6", "d2d4", "g8f6", "b1c3", "g7g6", "f2f4"],                           # Austrian Attack Pirc
    ["e2e4", "g7g6", "d2d4", "f8g7", "b1c3", "d7d6"],                                   # Modern Defense

    # Scandinavian
    ["e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5"],                                   # Scandinavian
    ["e2e4", "d7d5", "e4d5", "g8f6"],                                                     # Scandinavian Modern

    # Catalan
    ["d2d4", "g8f6", "c2c4", "e7e6", "g2g3", "d7d5", "f1g2"],                           # Catalan Open
    ["d2d4", "g8f6", "c2c4", "e7e6", "g2g3", "d7d5", "f1g2", "f8e7", "g1f3", "e8g8"],  # Catalan Closed

    # London System / Torre
    ["d2d4", "d7d5", "c1f4", "g8f6", "e2e3", "c7c5"],                                   # London System
    ["d2d4", "g8f6", "g1f3", "e7e6", "c1g5"],                                            # Torre Attack

    # Dutch
    ["d2d4", "f7f5", "g2g3", "g8f6", "f1g2", "g7g6"],                                   # Leningrad Dutch
    ["d2d4", "f7f5", "c2c4", "g8f6", "b1c3", "e7e6"],                                   # Stonewall Dutch
]


def _position_ok(board, fen, seen):
    """Check if a position passes quality filters."""
    if fen in seen:
        return False
    if board.is_game_over():
        return False
    if len(list(board.legal_moves)) < MIN_LEGAL_MOVES:
        return False
    if len(board.piece_map()) < MIN_PIECES:
        return False
    return True


def weighted_random_move(board, rng):
    """Pick a semi-realistic random move, biased toward captures, checks, and central moves.

    This produces much more realistic games than pure random play.
    Strategy:
      - Captures and checks get 5x weight
      - Moves to central squares (c3-f6) get 2x weight
      - Everything else gets 1x weight
    """
    moves = list(board.legal_moves)
    if not moves:
        return None

    CENTER = {
        chess.C3, chess.D3, chess.E3, chess.F3,
        chess.C4, chess.D4, chess.E4, chess.F4,
        chess.C5, chess.D5, chess.E5, chess.F5,
        chess.C6, chess.D6, chess.E6, chess.F6,
    }

    weights = []
    for m in moves:
        w = 1.0
        if board.is_capture(m):
            w = 5.0
        if board.gives_check(m):
            w = 5.0
        if m.to_square in CENTER:
            w = max(w, 2.0)
        # Penalize moving the king early (unless castling)
        if board.piece_at(m.from_square) and \
           board.piece_at(m.from_square).piece_type == chess.KING and \
           not board.is_castling(m):
            w *= 0.3
        weights.append(w)

    total = sum(weights)
    r = rng.random() * total
    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            return moves[i]
    return moves[-1]


def generate_from_openings(target, seed=42, existing_seen=None):
    """Generate positions by playing from known openings with weighted-random continuation."""
    rng = random.Random(seed)
    positions = []
    seen = set(existing_seen) if existing_seen else set()

    games_played = 0
    max_games = 5000  # Safety cap

    # We need ~target positions. Each game yields ~5-7 positions at our sample plies.
    # With 50 openings, cycle through them repeatedly.
    opening_idx = 0

    while len(positions) < target and games_played < max_games:
        opening = OPENINGS[opening_idx % len(OPENINGS)]
        opening_idx += 1

        # Add slight variation: sometimes skip 1-2 opening moves for diversity
        trim = rng.randint(0, min(2, max(0, len(opening) - 4)))
        moves_to_play = opening[:len(opening) - trim]

        board = chess.Board()
        valid_opening = True
        for uci_str in moves_to_play:
            try:
                move = chess.Move.from_uci(uci_str)
                if move in board.legal_moves:
                    board.push(move)
                else:
                    valid_opening = False
                    break
            except ValueError:
                valid_opening = False
                break

        if not valid_opening:
            continue

        # Continue with weighted random play up to ~80 plies (move 40)
        ply = board.ply()
        max_ply = rng.randint(70, 90)

        while ply < max_ply:
            move = weighted_random_move(board, rng)
            if move is None:
                break
            board.push(move)
            ply += 1

            if ply in SAMPLE_PLIES:
                fen = board.fen()
                if _position_ok(board, fen, seen):
                    positions.append(fen)
                    seen.add(fen)

            if board.is_game_over():
                break

        games_played += 1

        if games_played % 200 == 0:
            print(f"    {games_played} games -> {len(positions)} positions so far")

    return positions, seen, games_played


def generate_extra_random(target, seen, seed=123):
    """Generate additional positions from purely random starting moves to fill diversity gaps.

    Uses a wider range of ply depths (6-80) and samples more aggressively.
    """
    rng = random.Random(seed)
    positions = []
    attempts = 0
    max_attempts = target * 5  # Generous budget

    # Additional sample plies for more coverage
    extra_plies = set(range(12, 82, 2))  # Every even ply from 12 to 80

    while len(positions) < target and attempts < max_attempts:
        board = chess.Board()
        # Pick a random opening from our book to start
        if rng.random() < 0.5 and OPENINGS:
            opening = rng.choice(OPENINGS)
            trim = rng.randint(0, len(opening) // 2)
            for uci_str in opening[:len(opening) - trim]:
                try:
                    move = chess.Move.from_uci(uci_str)
                    if move in board.legal_moves:
                        board.push(move)
                    else:
                        break
                except ValueError:
                    break

        max_ply = rng.randint(30, 80)
        ply = board.ply()

        while ply < max_ply:
            move = weighted_random_move(board, rng)
            if move is None:
                break
            board.push(move)
            ply += 1

            if ply in extra_plies:
                fen = board.fen()
                if _position_ok(board, fen, seen):
                    positions.append(fen)
                    seen.add(fen)

            if board.is_game_over():
                break

        attempts += 1

    return positions


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t_start = time.time()
    all_positions = []
    seen = set()

    print("=" * 70)
    print("  POSITION GENERATOR: 50K diverse chess positions")
    print("=" * 70)

    # ---- Phase 1: Try Lichess API ----
    print("\n[1/3] Downloading games from Lichess API...")
    lichess_pgns = []
    try:
        lichess_pgns = download_lichess_games(max_total=500, timeout=15)
    except Exception as e:
        print(f"  Lichess download failed: {e}")

    if lichess_pgns:
        print(f"\n  Parsing Lichess PGNs...")
        lichess_positions, seen, n_games = parse_pgn_positions(lichess_pgns)
        all_positions.extend(lichess_positions)
        print(f"  Lichess: {len(lichess_positions)} positions from {n_games} games")
    else:
        print("  No Lichess games available. Using fallback only.")

    # ---- Phase 2: Opening book + weighted random ----
    remaining = TARGET_POSITIONS - len(all_positions)
    if remaining > 0:
        print(f"\n[2/3] Generating positions from opening book ({remaining} needed)...")
        opening_positions, seen, n_games = generate_from_openings(
            remaining, seed=42, existing_seen=seen
        )
        all_positions.extend(opening_positions)
        print(f"  Opening book: {len(opening_positions)} positions from {n_games} games")

    remaining = TARGET_POSITIONS - len(all_positions)
    if remaining > 0:
        print(f"\n[3/3] Generating {remaining} extra positions for diversity...")
        extra = generate_extra_random(remaining, seen, seed=999)
        all_positions.extend(extra)
        print(f"  Generated {len(extra)} extra positions")

    # ---- Final stats ----
    total = len(all_positions)
    elapsed = time.time() - t_start

    # Analyze diversity
    print(f"\n{'=' * 70}")
    print(f"  POSITION STATISTICS")
    print(f"{'=' * 70}")
    print(f"  Total positions: {total:,}")

    # Material distribution
    piece_counts = []
    material_balances = []
    game_phases = {"opening": 0, "middlegame": 0, "endgame": 0}
    side_to_move = {"white": 0, "black": 0}
    castling_count = 0

    for fen in all_positions[:5000]:  # Sample for stats
        try:
            b = chess.Board(fen)
            n_pieces = len(b.piece_map())
            piece_counts.append(n_pieces)

            # Material balance
            pv = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                  chess.ROOK: 5, chess.QUEEN: 9}
            wm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if p.color)
            bm = sum(pv.get(p.piece_type, 0) for p in b.piece_map().values() if not p.color)
            material_balances.append(wm - bm)

            if n_pieces > 28:
                game_phases["opening"] += 1
            elif n_pieces > 16:
                game_phases["middlegame"] += 1
            else:
                game_phases["endgame"] += 1

            side_to_move["white" if b.turn else "black"] += 1
            if b.has_castling_rights(chess.WHITE) or b.has_castling_rights(chess.BLACK):
                castling_count += 1
        except Exception:
            pass

    n_sample = len(piece_counts)
    if n_sample > 0:
        print(f"\n  Sample of {n_sample} positions:")
        print(f"  Piece count   : mean={np.mean(piece_counts):.1f}, "
              f"min={min(piece_counts)}, max={max(piece_counts)}")
        print(f"  Material bal  : mean={np.mean(material_balances):.2f}, "
              f"std={np.std(material_balances):.2f}")
        print(f"  Game phases   : opening={game_phases['opening']}, "
              f"middlegame={game_phases['middlegame']}, "
              f"endgame={game_phases['endgame']}")
        print(f"  Side to move  : white={side_to_move['white']}, "
              f"black={side_to_move['black']}")
        print(f"  Has castling  : {castling_count}/{n_sample} "
              f"({100*castling_count/n_sample:.0f}%)")

    # ---- Save ----
    fens_array = np.array(all_positions, dtype=object)
    np.savez_compressed(OUTPUT_PATH, fens=fens_array)
    mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"\n  Saved -> {OUTPUT_PATH}")
    print(f"  File size: {mb:.1f} MB")
    print(f"  Total time: {elapsed:.1f}s")

    # Verify
    check = np.load(OUTPUT_PATH, allow_pickle=True)
    print(f"  Verification: {len(check['fens'])} FENs in file")
    print(f"\n  Done. Ready for concept extraction pipeline.")


if __name__ == "__main__":
    main()
