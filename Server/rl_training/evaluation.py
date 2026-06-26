from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rl_env import RandomBotPolicy, TournamentEnv


def _empty_bucket():
    return {
        "episodes": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "truncations": 0,
        "reward": 0.0,
        "length": 0,
        "invalid_actions": 0,
    }


def _add_result(bucket, winner, reward, length, invalid_actions, truncated):
    bucket["episodes"] += 1
    bucket["wins"] += int(winner == "hero")
    bucket["losses"] += int(winner == "monster")
    bucket["draws"] += int(winner == "draw")
    bucket["truncations"] += int(truncated)
    bucket["reward"] += float(reward)
    bucket["length"] += int(length)
    bucket["invalid_actions"] += int(invalid_actions)


def _finalize_bucket(bucket):
    episodes = bucket["episodes"]
    if episodes <= 0:
        return {
            "episodes": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "truncations": 0,
            "win_rate": 0.0,
            "avg_reward": 0.0,
            "avg_length": 0.0,
            "invalid_actions_per_episode": 0.0,
        }

    return {
        "episodes": episodes,
        "wins": bucket["wins"],
        "losses": bucket["losses"],
        "draws": bucket["draws"],
        "truncations": bucket["truncations"],
        "win_rate": bucket["wins"] / episodes,
        "avg_reward": bucket["reward"] / episodes,
        "avg_length": bucket["length"] / episodes,
        "invalid_actions_per_episode": bucket["invalid_actions"] / episodes,
    }


def _valid_random_action(env):
    valid_actions = env._valid_actions(env.battle_state["hero"], env.agent_moves)
    if not valid_actions:
        return 0
    return int(env.np_random.choice(valid_actions))


def evaluate_policy(
    model=None,
    episodes=100,
    seed=10_000,
    character_config_path=None,
    opponent_pool=None,
    starting_actor_mode="opener",
    deterministic=True,
):
    env = TournamentEnv(
        opponent_pool=opponent_pool or [RandomBotPolicy()],
        character_config_path=character_config_path,
        starting_actor_mode=starting_actor_mode,
    )

    summary = _empty_bucket()
    breakdowns = _empty_breakdowns()

    for episode_index in range(episodes):
        obs, _ = env.reset(seed=seed + episode_index)
        _record_episode_result(env, model, obs, summary, breakdowns, deterministic)

    return _finalize_report(summary, breakdowns)


def evaluate_symmetric_tournament(
    model=None,
    episodes_per_matchup=5,
    seed=30_000,
    character_config_path=None,
    opponent_pool=None,
    starting_actor_mode="flag_only",
    deterministic=True,
):
    env = TournamentEnv(
        opponent_pool=opponent_pool or [RandomBotPolicy()],
        character_config_path=character_config_path,
        starting_actor_mode=starting_actor_mode,
    )

    summary = _empty_bucket()
    breakdowns = _empty_breakdowns()
    episode_index = 0

    for agent_template in env.characters:
        for opponent_template in env.characters:
            if agent_template.id == opponent_template.id:
                continue
            for starting_actor in ("agent", "opponent"):
                for _ in range(episodes_per_matchup):
                    obs, _ = env.reset(
                        seed=seed + episode_index,
                        options={
                            "agent_template": agent_template,
                            "opponent_template": opponent_template,
                            "starting_actor": starting_actor,
                        },
                    )
                    _record_episode_result(env, model, obs, summary, breakdowns, deterministic)
                    episode_index += 1

    return _finalize_report(summary, breakdowns)


def _empty_breakdowns():
    return {
        "agent_character": defaultdict(_empty_bucket),
        "opponent_character": defaultdict(_empty_bucket),
        "dragon_presence": defaultdict(_empty_bucket),
        "initiative": defaultdict(_empty_bucket),
        "matchup": defaultdict(_empty_bucket),
    }


def _record_episode_result(env, model, obs, summary, breakdowns, deterministic):
    episode_reward = 0.0
    episode_length = 0
    invalid_actions = 0
    done = False
    final_info = {}
    truncated_episode = False

    while not done:
        if model is None:
            action = _valid_random_action(env)
        else:
            action, _ = model.predict(obs, deterministic=deterministic)
            action = int(action)

        obs, reward, terminated, truncated, info = env.step(action)
        episode_reward += reward
        episode_length += 1
        invalid_actions += int(info.get("invalid_action", False))
        done = terminated or truncated
        final_info = info
        truncated_episode = bool(truncated)

    winner = final_info.get("winner")
    agent_name = env.agent_template.name
    opponent_name = env.opponent_template.name
    initiative = "agent_started" if env.agent_started else "opponent_started"
    dragon_presence = _dragon_presence(agent_name, opponent_name)
    matchup = f"{agent_name} vs {opponent_name}"

    _add_result(summary, winner, episode_reward, episode_length, invalid_actions, truncated_episode)
    _add_result(breakdowns["agent_character"][agent_name], winner, episode_reward, episode_length, invalid_actions, truncated_episode)
    _add_result(breakdowns["opponent_character"][opponent_name], winner, episode_reward, episode_length, invalid_actions, truncated_episode)
    _add_result(breakdowns["dragon_presence"][dragon_presence], winner, episode_reward, episode_length, invalid_actions, truncated_episode)
    _add_result(breakdowns["initiative"][initiative], winner, episode_reward, episode_length, invalid_actions, truncated_episode)
    _add_result(breakdowns["matchup"][matchup], winner, episode_reward, episode_length, invalid_actions, truncated_episode)


def _finalize_report(summary, breakdowns):
    return {
        "summary": _finalize_bucket(summary),
        "breakdowns": {
            section: {
                key: _finalize_bucket(bucket)
                for key, bucket in values.items()
            }
            for section, values in breakdowns.items()
        },
    }


def write_text_report(path, reports):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for title, report in reports:
            file.write(format_report(title, report))
            file.write("\n")


def format_report(title, report):
    lines = [f"=== {title} ===", ""]
    lines.extend(_format_metrics("overall", report["summary"]))

    for section, values in report["breakdowns"].items():
        lines.append("")
        lines.append(f"[{section}]")
        for key in sorted(values):
            lines.extend(_format_metrics(key, values[key]))

    return "\n".join(lines)


def _format_metrics(label, metrics):
    return [
        (
            f"{label}: episodes={metrics['episodes']} "
            f"wins={metrics['wins']} losses={metrics['losses']} draws={metrics['draws']} "
            f"truncations={metrics['truncations']} "
            f"win_rate={metrics['win_rate']:.2%} "
            f"avg_reward={metrics['avg_reward']:.3f} "
            f"avg_length={metrics['avg_length']:.2f} "
            f"invalid_actions_per_episode={metrics['invalid_actions_per_episode']:.2f}"
        )
    ]


def _dragon_presence(agent_name, opponent_name):
    if "dragon" in agent_name.lower():
        return "agent_dragon"
    if "dragon" in opponent_name.lower():
        return "opponent_dragon"
    return "no_dragon"
