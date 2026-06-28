import argparse
import csv
from collections import deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

from rl_env import ModelPolicy, RandomBotPolicy, TournamentEnv
from rl_training.evaluation import evaluate_policy, evaluate_symmetric_tournament, write_text_report


SERVER_DIR = Path(__file__).resolve().parent


class TrainingCurveCallback(BaseCallback):
    def __init__(self, output_dir, moving_average_window=25):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.moving_average_window = moving_average_window
        self.episode_rewards = []
        self.episode_lengths = []
        self.timesteps = []

    def _on_step(self):
        for info in self.locals.get("infos", []):
            episode = info.get("episode")
            if not episode:
                continue

            self.episode_rewards.append(float(episode["r"]))
            self.episode_lengths.append(int(episode["l"]))
            self.timesteps.append(int(self.num_timesteps))

        return True

    def _on_training_end(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._write_csv()
        self._plot_curve()

    def _write_csv(self):
        csv_path = self.output_dir / "ppo_training_curve.csv"
        with csv_path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["episode", "timestep", "reward", "length"])
            for index, (timestep, reward, length) in enumerate(
                zip(self.timesteps, self.episode_rewards, self.episode_lengths),
                start=1,
            ):
                writer.writerow([index, timestep, reward, length])

    def _plot_curve(self):
        if not self.episode_rewards:
            return

        rewards = np.array(self.episode_rewards, dtype=np.float32)
        episodes = np.arange(1, len(rewards) + 1)
        moving_average = self._moving_average(rewards)

        plt.figure(figsize=(12, 6))
        plt.plot(episodes, rewards, color="#8ab4ff", alpha=0.35, label="Episode reward")
        plt.plot(episodes, moving_average, color="#fbbc04", linewidth=2, label=f"{self.moving_average_window}-episode average")
        plt.xlabel("Episode")
        plt.ylabel("Reward")
        plt.title("PPO Training Curve")
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.output_dir / "ppo_training_curve.png", dpi=150)
        plt.close()

    def _moving_average(self, rewards):
        window = deque(maxlen=self.moving_average_window)
        averages = []
        for reward in rewards:
            window.append(float(reward))
            averages.append(sum(window) / len(window))
        return np.array(averages, dtype=np.float32)


def evaluate_model(
    model,
    episodes=50,
    seed=10_000,
    character_config_path=None,
    opponent_pool=None,
    starting_actor_mode="opener",
):
    wins = 0
    losses = 0
    draws = 0
    truncations = 0
    total_reward = 0.0
    episode_lengths = []

    env = TournamentEnv(
        opponent_pool=opponent_pool or [RandomBotPolicy()],
        character_config_path=character_config_path,
        starting_actor_mode=starting_actor_mode,
    )
    for episode_index in range(episodes):
        obs, _ = env.reset(seed=seed + episode_index)
        done = False
        episode_reward = 0.0
        steps = 0
        final_info = {}

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            steps += 1
            done = terminated or truncated
            final_info = info

        winner = final_info.get("winner")
        if winner == "hero":
            wins += 1
        elif winner == "monster":
            losses += 1
        elif winner == "draw":
            draws += 1
        if final_info.get("winner") is None:
            truncations += 1

        total_reward += episode_reward
        episode_lengths.append(steps)

    return {
        "episodes": episodes,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "truncations": truncations,
        "win_rate": wins / episodes if episodes else 0.0,
        "avg_reward": total_reward / episodes if episodes else 0.0,
        "avg_length": sum(episode_lengths) / episodes if episodes else 0.0,
    }


def write_evaluation(output_dir, metrics):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "ppo_evaluation.txt").open("w") as file:
        for key, value in metrics.items():
            file.write(f"{key}: {value}\n")


def build_model(env, seed):
    return PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        seed=seed,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Train a PPO agent for the tournament environment.")
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--eval-episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="models/PPO/fair_init/ppo_fair_random_100k")
    parser.add_argument("--curve-window", type=int, default=25)
    parser.add_argument(
        "--character-config",
        default="rl_training/configs/characters_balanced.json",
        help="Training character config. Use config/characters.json for the original game balance.",
    )
    parser.add_argument(
        "--breakdown-episodes",
        type=int,
        default=None,
        help="Episodes used for matchup breakdowns. Defaults to --eval-episodes.",
    )
    parser.add_argument(
        "--opponent-models",
        nargs="*",
        default=[],
        help="PPO checkpoint paths to include in the opponent pool.",
    )
    parser.add_argument(
        "--random-opponents",
        type=int,
        default=1,
        help="Number of RandomBotPolicy copies in the opponent pool. Use 2 with two PPO models for 50/25/25.",
    )
    parser.add_argument(
        "--starting-actor-mode",
        choices=("opener", "flag_only"),
        default="flag_only",
        help="Use 'opener' for the old free opening move, or 'flag_only' for fair-init training.",
    )
    parser.add_argument(
        "--symmetric-eval",
        action="store_true",
        help="Also write a symmetric tournament report over every character matchup and both starting actors.",
    )
    parser.add_argument(
        "--episodes-per-matchup",
        type=int,
        default=5,
        help="Repetitions per ordered matchup/start-side pair for --symmetric-eval.",
    )
    return parser.parse_args()


def build_opponent_pool(opponent_model_paths, random_opponents=1):
    pool = [RandomBotPolicy() for _ in range(max(0, random_opponents))]
    loaded_models = []

    for model_path in opponent_model_paths:
        resolved_path = resolve_server_path(model_path)
        opponent_model = PPO.load(resolved_path)
        pool.append(ModelPolicy(opponent_model, deterministic=True))
        loaded_models.append((resolved_path, opponent_model))

    if not pool:
        pool.append(RandomBotPolicy())

    return pool, loaded_models


def resolve_server_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return SERVER_DIR / path


def opponent_pool_description(args):
    total = max(0, args.random_opponents) + len(args.opponent_models)
    if total <= 0:
        return "RandomBotPolicy: 100.00%"

    parts = []
    if args.random_opponents > 0:
        parts.append(f"RandomBotPolicy: {(args.random_opponents / total):.2%}")
    for model_path in args.opponent_models:
        parts.append(f"{model_path}: {(1 / total):.2%}")
    return ", ".join(parts)


def format_model_label(path):
    path = Path(path)
    return f"{path.parent.name}/{path.name}"


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    opponent_pool, loaded_opponent_models = build_opponent_pool(
        args.opponent_models,
        random_opponents=args.random_opponents,
    )

    train_env = Monitor(TournamentEnv(
        opponent_pool=opponent_pool,
        character_config_path=args.character_config,
        starting_actor_mode=args.starting_actor_mode,
    ))
    model = build_model(train_env, args.seed)
    callback = TrainingCurveCallback(output_dir=output_dir, moving_average_window=args.curve_window)

    model.learn(total_timesteps=args.timesteps, callback=callback, progress_bar=False)

    model_path = output_dir / "ppo_model.zip"
    model.save(model_path)

    metrics = evaluate_model(
        model,
        episodes=args.eval_episodes,
        seed=args.seed + 100_000,
        character_config_path=args.character_config,
        opponent_pool=opponent_pool,
        starting_actor_mode=args.starting_actor_mode,
    )
    write_evaluation(output_dir, metrics)

    breakdown_episodes = args.breakdown_episodes or args.eval_episodes
    reports = []
    reports.append((
        "PPO vs training opponent pool",
        evaluate_policy(
            model=model,
            episodes=breakdown_episodes,
            seed=args.seed + 200_000,
            character_config_path=args.character_config,
            opponent_pool=opponent_pool,
            starting_actor_mode=args.starting_actor_mode,
        ),
    ))
    reports.append((
        "PPO vs RandomBotPolicy",
        evaluate_policy(
            model=model,
            episodes=breakdown_episodes,
            seed=args.seed + 210_000,
            character_config_path=args.character_config,
            opponent_pool=[RandomBotPolicy()],
            starting_actor_mode=args.starting_actor_mode,
        ),
    ))
    for index, (opponent_path, opponent_model) in enumerate(loaded_opponent_models, start=1):
        reports.append((
            f"PPO vs opponent model {index}: {format_model_label(opponent_path)}",
            evaluate_policy(
                model=model,
                episodes=breakdown_episodes,
                seed=args.seed + 220_000 + index,
                character_config_path=args.character_config,
                opponent_pool=[ModelPolicy(opponent_model, deterministic=True)],
                starting_actor_mode=args.starting_actor_mode,
            ),
        ))

    random_report = evaluate_policy(
        model=None,
        episodes=breakdown_episodes,
        seed=args.seed + 200_000,
        character_config_path=args.character_config,
        opponent_pool=[RandomBotPolicy()],
        starting_actor_mode=args.starting_actor_mode,
    )
    reports.append(("Valid-random vs RandomBotPolicy", random_report))

    breakdown_path = output_dir / "ppo_matchup_breakdown.txt"
    write_text_report(breakdown_path, reports)

    symmetric_path = None
    if args.symmetric_eval:
        symmetric_reports = []
        symmetric_reports.append((
            "PPO symmetric tournament vs training opponent pool",
            evaluate_symmetric_tournament(
                model=model,
                episodes_per_matchup=args.episodes_per_matchup,
                seed=args.seed + 300_000,
                character_config_path=args.character_config,
                opponent_pool=opponent_pool,
                starting_actor_mode=args.starting_actor_mode,
            ),
        ))
        symmetric_reports.append((
            "PPO symmetric tournament vs RandomBotPolicy",
            evaluate_symmetric_tournament(
                model=model,
                episodes_per_matchup=args.episodes_per_matchup,
                seed=args.seed + 310_000,
                character_config_path=args.character_config,
                opponent_pool=[RandomBotPolicy()],
                starting_actor_mode=args.starting_actor_mode,
            ),
        ))
        symmetric_path = output_dir / "ppo_symmetric_tournament.txt"
        write_text_report(symmetric_path, symmetric_reports)

    print(f"Opponent pool: {opponent_pool_description(args)}")
    print(f"Starting actor mode: {args.starting_actor_mode}")
    print(f"Saved model: {model_path}")
    print(f"Saved curve: {output_dir / 'ppo_training_curve.png'}")
    print(f"Saved rewards: {output_dir / 'ppo_training_curve.csv'}")
    print(f"Saved matchup breakdown: {breakdown_path}")
    if symmetric_path:
        print(f"Saved symmetric tournament: {symmetric_path}")
    print(f"Evaluation: {metrics}")


if __name__ == "__main__":
    main()
