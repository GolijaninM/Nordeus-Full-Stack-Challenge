from pathlib import Path

from rl_env import ModelPolicy, RandomBotPolicy, TournamentEnv


def main():
    try:
        from stable_baselines3 import PPO
    except ImportError as error:
        raise SystemExit(
            "stable-baselines3 is not installed yet. Install it when you are ready for PPO training:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install stable-baselines3"
        ) from error

    output_dir = Path("models")
    output_dir.mkdir(exist_ok=True)

    opponent_pool = [RandomBotPolicy()]
    env = TournamentEnv(opponent_pool=opponent_pool)
    model = PPO("MlpPolicy", env, verbose=1)

    for generation in range(10):
        model.learn(total_timesteps=1_000_000)
        checkpoint_path = output_dir / f"universal_model_gen_{generation}.zip"
        model.save(checkpoint_path)
        opponent_pool.append(ModelPolicy(PPO.load(checkpoint_path), deterministic=False))


if __name__ == "__main__":
    main()
