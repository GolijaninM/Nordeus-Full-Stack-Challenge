import argparse
import csv
from collections import deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

from rl_env import RandomBotPolicy, TournamentEnv
from rl_training.evaluation import evaluate_policy, write_text_report


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
        csv_path = self.output_dir / "dqn_training_curve.csv"
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
        plt.title("DQN Training Curve")
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.output_dir / "dqn_training_curve.png", dpi=150)
        plt.close()

    def _moving_average(self, rewards):
        window = deque(maxlen=self.moving_average_window)
        averages = []
        for reward in rewards:
            window.append(float(reward))
            averages.append(sum(window) / len(window))
        return np.array(averages, dtype=np.float32)


def evaluate_model(model, episodes=50, seed=10_000, character_config_path=None):
    wins = 0
    losses = 0
    draws = 0
    truncations = 0
    total_reward = 0.0
    episode_lengths = []

    env = TournamentEnv(opponent_pool=[RandomBotPolicy()], character_config_path=character_config_path)
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
    with (output_dir / "dqn_evaluation.txt").open("w") as file:
        for key, value in metrics.items():
            file.write(f"{key}: {value}\n")


def build_model(env, seed):
    return DQN(
        "MlpPolicy",
        env,
        learning_rate=1e-4,
        buffer_size=50_000,
        learning_starts=1_000,
        batch_size=64,
        gamma=0.99,
        train_freq=4,
        target_update_interval=1_000,
        exploration_fraction=0.25,
        exploration_initial_eps=1.0,
        exploration_final_eps=0.08,
        verbose=1,
        seed=seed,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Train a DQN agent for the tournament environment.")
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--eval-episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="models/dqn")
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
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_env = Monitor(TournamentEnv(
        opponent_pool=[RandomBotPolicy()],
        character_config_path=args.character_config,
    ))
    model = build_model(train_env, args.seed)
    callback = TrainingCurveCallback(output_dir=output_dir, moving_average_window=args.curve_window)

    model.learn(total_timesteps=args.timesteps, callback=callback, progress_bar=False)

    model_path = output_dir / "dqn_model.zip"
    model.save(model_path)

    metrics = evaluate_model(
        model,
        episodes=args.eval_episodes,
        seed=args.seed + 100_000,
        character_config_path=args.character_config,
    )
    write_evaluation(output_dir, metrics)

    breakdown_episodes = args.breakdown_episodes or args.eval_episodes
    dqn_report = evaluate_policy(
        model=model,
        episodes=breakdown_episodes,
        seed=args.seed + 200_000,
        character_config_path=args.character_config,
    )
    random_report = evaluate_policy(
        model=None,
        episodes=breakdown_episodes,
        seed=args.seed + 200_000,
        character_config_path=args.character_config,
    )
    breakdown_path = output_dir / "dqn_matchup_breakdown.txt"
    write_text_report(
        breakdown_path,
        [
            ("DQN", dqn_report),
            ("Valid-random baseline", random_report),
        ],
    )

    print(f"Saved model: {model_path}")
    print(f"Saved curve: {output_dir / 'dqn_training_curve.png'}")
    print(f"Saved rewards: {output_dir / 'dqn_training_curve.csv'}")
    print(f"Saved matchup breakdown: {breakdown_path}")
    print(f"Evaluation: {metrics}")


if __name__ == "__main__":
    main()
