#!/usr/bin/env python3
"""Name concept groups using Claude API based on representative positions."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

# Load API key from website .env.local
env_path = os.path.join(os.path.dirname(__file__), "..", "website", ".env.local")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                val = val.strip().strip('"')
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = val

from anthropic import Anthropic

api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: No CLAUDE_API_KEY or ANTHROPIC_API_KEY found")
    sys.exit(1)
client = Anthropic(api_key=api_key)

with open("concepts_for_seed.json") as f:
    concepts = json.load(f)

print(f"Naming {len(concepts)} concept groups with Claude API...")

named_concepts = []

for i, c in enumerate(concepts):
    positions_text = ""
    for j, p in enumerate(c["positions"]):
        positions_text += f"  Position {j+1}: FEN={p['fen']}\n"
        positions_text += f"    Strong network plays: {p['strong']}\n"
        positions_text += f"    Weak network plays:   {p['weak']}\n\n"

    phase_str = ", ".join(f"{k}: {v}" for k, v in c["phases"].items())

    prompt = f"""You are a chess coach naming a concept discovered by analyzing disagreements between two Leela Chess Zero neural networks (69 Elo apart, both ~3600 CCRL).

This concept group has {c['size']} positions where the stronger network consistently plays a different move than the weaker one.

Average pieces on board: {c['avg_pieces']:.0f}
Game phases: {phase_str}
Average material balance: {c['avg_material']:+.1f}

Representative positions:
{positions_text}

Based on these positions, provide:
1. A short concept name (2-4 words, like "Prophylactic Knight Retreat" or "Central Pawn Sacrifice")
2. A one-sentence summary (what the stronger network understands that the weaker doesn't)
3. A 2-3 paragraph description explaining this concept to an intermediate (1400-1800) chess player. Use the specific positions as examples. Be concrete, not abstract.
4. A difficulty level: beginner, intermediate, or advanced

Format your response EXACTLY as JSON:
{{"name": "...", "summary": "...", "description": "...", "difficulty": "..."}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Extract JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            result["positions"] = c["positions"]
            result["size"] = c["size"]
            result["avg_teach"] = c["avg_teach"]
            named_concepts.append(result)
            print(f"  {i+1}. {result['name']} ({c['size']} pos, {result['difficulty']})")
        else:
            print(f"  {i+1}. FAILED to parse JSON")
    except Exception as e:
        print(f"  {i+1}. ERROR: {e}")

    time.sleep(0.5)  # Rate limit

# Save
with open("named_concepts.json", "w", encoding="utf-8") as f:
    json.dump(named_concepts, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(named_concepts)} named concepts to named_concepts.json")
