from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from stable_baselines3 import DQN, PPO  # noqa: E402

from rl_env import ModelPolicy, TournamentEnv  # noqa: E402


ALGORITHMS = {
    "dqn": DQN,
    "ppo": PPO,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Record detailed model-vs-model tournament traces.")
    parser.add_argument("--algorithm", choices=sorted(ALGORITHMS), default="ppo")
    parser.add_argument("--agent-model", required=True)
    parser.add_argument("--opponent-model", required=True)
    parser.add_argument("--agent-label", default="agent")
    parser.add_argument("--opponent-label", default="opponent")
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--random-games", type=int, default=8)
    parser.add_argument("--max-turns", type=int, default=80)
    parser.add_argument(
        "--character-config",
        default="rl_training/configs/characters_balanced.json",
        help="Character config used for the diagnostic games.",
    )
    parser.add_argument(
        "--starting-actor-mode",
        choices=("opener", "flag_only"),
        default="flag_only",
    )
    parser.add_argument(
        "--include-fixed-combo-cases",
        action="store_true",
        help="Also run fixed matchups that can reveal known setup/finisher combos.",
    )
    parser.add_argument(
        "--swap-perspective",
        action="store_true",
        help="Run the same plan again with agent/opponent models swapped.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Markdown report path. Defaults to <agent_model_dir>/matchup_diagnostics.md.",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional JSON trace output. Defaults to <report_path>.json.",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print saved file paths.")
    return parser.parse_args()


def main():
    args = parse_args()
    model_cls = ALGORITHMS[args.algorithm]
    agent_model_path = resolve_server_path(args.agent_model)
    opponent_model_path = resolve_server_path(args.opponent_model)
    output_path = Path(args.output) if args.output else agent_model_path.parent / "matchup_diagnostics.md"
    json_output_path = Path(args.json_output) if args.json_output else output_path.with_suffix(".json")

    agent_model = model_cls.load(agent_model_path)
    opponent_model = model_cls.load(opponent_model_path)

    games = []
    games.extend(run_plan(
        agent_model=agent_model,
        opponent_model=opponent_model,
        agent_label=args.agent_label,
        opponent_label=args.opponent_label,
        seed=args.seed,
        random_games=args.random_games,
        character_config_path=args.character_config,
        starting_actor_mode=args.starting_actor_mode,
        max_turns=args.max_turns,
        include_fixed_combo_cases=args.include_fixed_combo_cases,
    ))

    if args.swap_perspective:
        games.extend(run_plan(
            agent_model=opponent_model,
            opponent_model=agent_model,
            agent_label=args.opponent_label,
            opponent_label=args.agent_label,
            seed=args.seed + 50_000,
            random_games=args.random_games,
            character_config_path=args.character_config,
            starting_actor_mode=args.starting_actor_mode,
            max_turns=args.max_turns,
            include_fixed_combo_cases=args.include_fixed_combo_cases,
        ))

    report = format_report(
        games=games,
        algorithm=args.algorithm.upper(),
        agent_model_path=agent_model_path,
        opponent_model_path=opponent_model_path,
        starting_actor_mode=args.starting_actor_mode,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    json_output_path.write_text(json.dumps(games, indent=2), encoding="utf-8")

    if not args.quiet:
        print(report)
    print(f"Saved report: {output_path}")
    print(f"Saved JSON traces: {json_output_path}")


def run_plan(
    agent_model,
    opponent_model,
    agent_label,
    opponent_label,
    seed,
    random_games,
    character_config_path,
    starting_actor_mode,
    max_turns,
    include_fixed_combo_cases,
):
    env = TournamentEnv(
        opponent_pool=[ModelPolicy(opponent_model, deterministic=True)],
        character_config_path=character_config_path,
        starting_actor_mode=starting_actor_mode,
        max_turns=max_turns,
    )
    templates = {template.id: template for template in env.characters}
    games = []
    game_index = 0

    for index in range(random_games):
        starting_actor = "agent" if index % 2 == 0 else "opponent"
        games.append(run_game(
            env=env,
            model=agent_model,
            agent_label=agent_label,
            opponent_label=opponent_label,
            seed=seed + game_index,
            starting_actor=starting_actor,
            game_kind="random",
        ))
        game_index += 1

    if include_fixed_combo_cases:
        fixed_cases = [
            ("witch", "knight", "agent"),
            ("giant_spider", "witch", "opponent"),
            ("goblin_warrior", "knight", "agent"),
            ("dragon", "knight", "opponent"),
            ("knight", "witch", "agent"),
        ]
        for agent_id, opponent_id, starting_actor in fixed_cases:
            if agent_id not in templates or opponent_id not in templates:
                continue
            games.append(run_game(
                env=env,
                model=agent_model,
                agent_label=agent_label,
                opponent_label=opponent_label,
                seed=seed + game_index,
                starting_actor=starting_actor,
                game_kind="fixed",
                agent_template=templates[agent_id],
                opponent_template=templates[opponent_id],
            ))
            game_index += 1

    return games


def run_game(
    env,
    model,
    agent_label,
    opponent_label,
    seed,
    starting_actor,
    game_kind,
    agent_template=None,
    opponent_template=None,
):
    options = {"starting_actor": starting_actor}
    if agent_template is not None:
        options["agent_template"] = agent_template
    if opponent_template is not None:
        options["opponent_template"] = opponent_template

    obs, reset_info = env.reset(seed=seed, options=options)
    done = False
    total_reward = 0.0
    turns = []

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += float(reward)
        turns.append(format_turn(info, reward, env.moves_config))
        done = terminated or truncated

    final_info = turns[-1]["raw_info"] if turns else reset_info
    return {
        "kind": game_kind,
        "seed": seed,
        "agent_label": agent_label,
        "opponent_label": opponent_label,
        "agent_character": env.agent_template.name,
        "opponent_character": env.opponent_template.name,
        "starting_actor": starting_actor,
        "starting_actor_mode": env.starting_actor_mode,
        "winner": final_info.get("winner"),
        "winner_label": label_winner(final_info.get("winner"), agent_label, opponent_label),
        "turn_count": len(turns),
        "total_reward": round(total_reward, 3),
        "agent_combo_count": sum(1 for turn in turns if turn["agent_combo"]),
        "opponent_combo_count": sum(1 for turn in turns if turn["opponent_combo"]),
        "agent_moves": [turn["agent_move"] for turn in turns if turn["agent_move"]],
        "opponent_moves": [turn["opponent_move"] for turn in turns if turn["opponent_move"]],
        "turns": turns,
    }


def format_turn(info, reward, moves_config):
    agent_result = info.get("agent_result") or {}
    opponent_result = info.get("opponent_result") or {}
    battle_state = info.get("battle_state", {})
    hero_state = battle_state.get("hero", {})
    monster_state = battle_state.get("monster", {})
    agent_move_id = info.get("agent_move")
    opponent_move_id = info.get("opponent_move")

    turn = {
        "turn": int(info.get("turn", 0)) - 1,
        "reward": round(float(reward), 3),
        "agent_action": info.get("agent_action"),
        "opponent_action": info.get("opponent_action"),
        "agent_move": move_label(agent_move_id, moves_config, agent_result),
        "opponent_move": move_label(opponent_move_id, moves_config, opponent_result),
        "agent_move_id": agent_move_id,
        "opponent_move_id": opponent_move_id,
        "agent_damage": int(agent_result.get("damage", 0)),
        "opponent_damage": int(opponent_result.get("damage", 0)),
        "agent_heal": int(agent_result.get("heal", 0)),
        "opponent_heal": int(opponent_result.get("heal", 0)),
        "agent_hp_cost": int(agent_result.get("hp_cost", 0)),
        "opponent_hp_cost": int(opponent_result.get("hp_cost", 0)),
        "agent_combo": bool(agent_result.get("combo_triggered", False)),
        "opponent_combo": bool(opponent_result.get("combo_triggered", False)),
        "agent_combo_multiplier": agent_result.get("combo_multiplier", 1),
        "opponent_combo_multiplier": opponent_result.get("combo_multiplier", 1),
        "agent_effects": summarize_effects(agent_result),
        "opponent_effects": summarize_effects(opponent_result),
        "events": summarize_events(info.get("events", [])),
        "agent_hp": hero_state.get("hp"),
        "opponent_hp": monster_state.get("hp"),
        "winner": info.get("winner"),
        "raw_info": info,
    }
    return turn


def format_report(games, algorithm, agent_model_path, opponent_model_path, starting_actor_mode):
    lines = [
        f"# {algorithm} Matchup Diagnostics",
        "",
        f"Agent model: `{rel(agent_model_path)}`",
        f"Opponent model: `{rel(opponent_model_path)}`",
        f"Starting actor mode: `{starting_actor_mode}`",
        "",
    ]
    lines.extend(format_summary(games))

    for index, game in enumerate(games, start=1):
        lines.extend(format_game(index, game))

    return "\n".join(lines) + "\n"


def format_summary(games):
    winner_counts = Counter(game["winner_label"] for game in games)
    by_side = defaultdict(lambda: {"games": 0, "wins": 0})
    move_counts = defaultdict(Counter)
    combo_counts = Counter()

    for game in games:
        by_side[(game["agent_label"], game["starting_actor"])]["games"] += 1
        if game["winner"] == "hero":
            by_side[(game["agent_label"], game["starting_actor"])]["wins"] += 1
        move_counts[game["agent_label"]].update(game["agent_moves"])
        move_counts[game["opponent_label"]].update(game["opponent_moves"])
        combo_counts[game["agent_label"]] += game["agent_combo_count"]
        combo_counts[game["opponent_label"]] += game["opponent_combo_count"]

    lines = [
        "## Summary",
        "",
        f"Games: {len(games)}",
        "Winners: " + ", ".join(f"{label}={count}" for label, count in sorted(winner_counts.items())),
        "",
        "Win rate by agent perspective/start flag:",
    ]
    for (label, starting_actor), metrics in sorted(by_side.items()):
        win_rate = metrics["wins"] / metrics["games"] if metrics["games"] else 0.0
        lines.append(f"- {label}, starting_actor={starting_actor}: {metrics['wins']}/{metrics['games']} ({win_rate:.1%})")

    lines.extend(["", "Most used moves:"])
    for label, counts in sorted(move_counts.items()):
        most_common = ", ".join(f"{move} x{count}" for move, count in counts.most_common(8))
        lines.append(f"- {label}: {most_common or 'none'}")

    lines.extend(["", "Triggered combos:"])
    for label in sorted(move_counts):
        lines.append(f"- {label}: {combo_counts[label]}")
    lines.append("")
    return lines


def format_game(index, game):
    lines = [
        f"## Game {index:02d} ({game['kind']})",
        "",
        (
            f"{game['agent_label']} as {game['agent_character']} vs "
            f"{game['opponent_label']} as {game['opponent_character']} | "
            f"starting_actor={game['starting_actor']} | winner={game['winner_label']} | "
            f"turns={game['turn_count']} | reward={game['total_reward']}"
        ),
        "",
        (
            f"Combos: {game['agent_label']}={game['agent_combo_count']}, "
            f"{game['opponent_label']}={game['opponent_combo_count']}"
        ),
        "",
        "| Turn | Agent move | Opponent move | HP after turn | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for turn in game["turns"]:
        lines.append(
            "| {turn} | {agent} | {opponent} | {hp} | {notes} |".format(
                turn=turn["turn"],
                agent=format_actor_move(turn, "agent"),
                opponent=format_actor_move(turn, "opponent"),
                hp=f"A {turn['agent_hp']} / O {turn['opponent_hp']}",
                notes=format_notes(turn),
            )
        )
    lines.append("")
    return lines


def format_actor_move(turn, side):
    move = turn[f"{side}_move"] or "-"
    damage = turn[f"{side}_damage"]
    heal = turn[f"{side}_heal"]
    hp_cost = turn[f"{side}_hp_cost"]
    combo = turn[f"{side}_combo"]
    effects = turn[f"{side}_effects"]
    parts = [move]
    if damage:
        parts.append(f"dmg {damage}")
    if heal:
        parts.append(f"heal {heal}")
    if hp_cost:
        parts.append(f"cost {hp_cost}")
    if effects:
        parts.append(effects)
    if combo:
        parts.append(f"COMBO x{turn[f'{side}_combo_multiplier']}")
    return "<br>".join(parts)


def format_notes(turn):
    notes = []
    if turn["events"]:
        notes.append(turn["events"])
    if turn["winner"]:
        notes.append(f"winner={turn['winner']}")
    return "<br>".join(notes) if notes else "-"


def move_label(move_id, moves_config, result):
    if move_id is None:
        return result.get("move_name") if result else None
    move = moves_config.get(move_id, {})
    return move.get("name", move_id)


def summarize_effects(result):
    effects = []
    for stat_change in result.get("stat_changes", []):
        target = stat_change.get("target", "?")
        stat = stat_change.get("stat", "?")
        amount = stat_change.get("change", stat_change.get("amount", 0))
        effects.append(f"{target} {stat} {amount:+}")
    for applied in result.get("applied_effects", []):
        kind = applied.get("kind", "?")
        target = applied.get("target", "?")
        if kind == "dot":
            effects.append(f"{target} dot {applied.get('damage', 0)}x{applied.get('duration', 0)}")
        else:
            effects.append(f"{target} {kind}")
    return ", ".join(effects)


def summarize_events(events):
    parts = []
    for event in events:
        event_type = event.get("type")
        if event_type == "dot":
            parts.append(f"dot {event.get('target')} -{event.get('damage')} from {event.get('source_move')}")
        elif event_type == "enrage":
            parts.append(f"enrage {event.get('target')} {event.get('stat')} +{event.get('amount')}")
        else:
            parts.append(str(event))
    return ", ".join(parts)


def label_winner(winner, agent_label, opponent_label):
    if winner == "hero":
        return agent_label
    if winner == "monster":
        return opponent_label
    return winner or "none"


def resolve_server_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return SERVER_DIR / path


def rel(path):
    try:
        return path.relative_to(SERVER_DIR)
    except ValueError:
        return path


if __name__ == "__main__":
    main()
