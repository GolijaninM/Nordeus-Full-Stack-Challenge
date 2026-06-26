from __future__ import annotations

import argparse
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from stable_baselines3 import DQN  # noqa: E402

from rl_env import ModelPolicy, RandomBotPolicy  # noqa: E402
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
    parser.add_argument(
        "--opponent-models",
        nargs="*",
        default=[],
        help="DQN checkpoint paths to evaluate against in addition to RandomBotPolicy.",
    )
    parser.add_argument(
        "--random-opponents",
        type=int,
        default=1,
        help="Number of RandomBotPolicy copies used in the mixed opponent pool.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = _resolve_server_path(args.model)
    output_path = Path(args.output) if args.output else model_path.parent / "dqn_matchup_breakdown.txt"

    model = DQN.load(model_path)
    opponent_pool, loaded_opponent_models = _build_opponent_pool(
        args.opponent_models,
        random_opponents=args.random_opponents,
    )

    reports = []
    reports.append((
        "DQN vs mixed opponent pool",
        evaluate_policy(
            model=model,
            episodes=args.episodes,
            seed=args.seed,
            character_config_path=args.character_config,
            opponent_pool=opponent_pool,
        ),
    ))
    reports.append((
        "DQN vs RandomBotPolicy",
        evaluate_policy(
            model=model,
            episodes=args.episodes,
            seed=args.seed + 10_000,
            character_config_path=args.character_config,
            opponent_pool=[RandomBotPolicy()],
        ),
    ))
    for index, (opponent_path, opponent_model) in enumerate(loaded_opponent_models, start=1):
        reports.append((
            f"DQN vs opponent model {index}: {_format_model_label(opponent_path)}",
            evaluate_policy(
                model=model,
                episodes=args.episodes,
                seed=args.seed + 20_000 + index,
                character_config_path=args.character_config,
                opponent_pool=[ModelPolicy(opponent_model, deterministic=True)],
            ),
        ))
    reports.append((
        "Valid-random vs RandomBotPolicy",
        evaluate_policy(
            model=None,
            episodes=args.episodes,
            seed=args.seed + 30_000,
            character_config_path=args.character_config,
            opponent_pool=[RandomBotPolicy()],
        ),
    ))

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


def _format_model_label(path):
    path = Path(path)
    return f"{path.parent.name}/{path.name}"


def _build_opponent_pool(opponent_model_paths, random_opponents=1):
    pool = [RandomBotPolicy() for _ in range(max(0, random_opponents))]
    loaded_models = []

    for model_path in opponent_model_paths:
        resolved_path = _resolve_server_path(model_path)
        opponent_model = DQN.load(resolved_path)
        pool.append(ModelPolicy(opponent_model, deterministic=True))
        loaded_models.append((resolved_path, opponent_model))

    if not pool:
        pool.append(RandomBotPolicy())

    return pool, loaded_models


if __name__ == "__main__":
    main()
