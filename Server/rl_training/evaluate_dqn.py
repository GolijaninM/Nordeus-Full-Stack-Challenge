from __future__ import annotations

import argparse
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from stable_baselines3 import DQN  # noqa: E402

from rl_training.evaluation import evaluate_policy, format_report, write_text_report  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained DQN checkpoint with matchup breakdowns.")
    parser.add_argument("--model", default="models/dqn/dqn_model.zip")
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument(
        "--character-config",
        default="rl_training/configs/characters_balanced.json",
        help="Character config used during evaluation.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional text report path. Defaults to <model_dir>/dqn_matchup_breakdown.txt.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = _resolve_server_path(args.model)
    output_path = Path(args.output) if args.output else model_path.parent / "dqn_matchup_breakdown.txt"

    model = DQN.load(model_path)
    dqn_report = evaluate_policy(
        model=model,
        episodes=args.episodes,
        seed=args.seed,
        character_config_path=args.character_config,
    )
    random_report = evaluate_policy(
        model=None,
        episodes=args.episodes,
        seed=args.seed,
        character_config_path=args.character_config,
    )

    reports = [
        ("DQN", dqn_report),
        ("Valid-random baseline", random_report),
    ]
    write_text_report(output_path, reports)

    for title, report in reports:
        print(format_report(title, report))
        print()
    print(f"Saved matchup breakdown: {output_path}")


def _resolve_server_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return SERVER_DIR / path


if __name__ == "__main__":
    main()
