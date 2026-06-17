import json
import os
import random


def load_config(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "config", filename)

    with open(file_path, "r") as file:
        return json.load(file)


def clamp(value, minimum=0, maximum=None):
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def calculate_damage(move, attacker_atk, attacker_mag, defender_def):
    move_type = move.get("type")
    base = move.get("base_value", 0)

    if move_type == "physical":
        damage = (base + attacker_atk) - defender_def
    elif move_type == "magic":
        damage = base + attacker_mag
    else:
        damage = base if move.get("effect") in ("dot", "damage_and_dot") else 0

    return max(0, damage)


def with_move_id(move_id, move):
    move_detail = move.copy()
    move_detail["id"] = move_id
    move_detail.setdefault("cooldown", 0)
    return move_detail


def build_character_state(current_hp, attack, defense, magic, max_hp, extra=None):
    extra = extra or {}
    state = {
        "hp": current_hp,
        "max_hp": max_hp,
        "base_attack": attack,
        "base_defense": defense,
        "base_magic": magic,
        "attack": attack,
        "defense": defense,
        "magic": magic,
        "cooldowns": {},
        "active_effects": [],
        "last_move": None,
        "enraged": False,
    }
    state.update(extra)
    refresh_effective_stats(state)
    return state


def refresh_effective_stats(state):
    attack = state.get("base_attack", state.get("attack", 0))
    defense = state.get("base_defense", state.get("defense", 0))
    magic = state.get("base_magic", state.get("magic", 0))

    for effect in state.get("active_effects", []):
        if effect.get("kind") != "stat_mod":
            continue
        stat = effect.get("stat")
        amount = effect.get("amount", 0)
        if stat == "attack":
            attack += amount
        elif stat == "defense":
            defense += amount
        elif stat == "magic":
            magic += amount

    state["attack"] = max(0, int(round(attack)))
    state["defense"] = max(0, int(round(defense)))
    state["magic"] = max(0, int(round(magic)))
    return state


def serialize_character_state(state):
    refresh_effective_stats(state)
    return {
        "id": state.get("id"),
        "name": state.get("name"),
        "hp": state.get("hp", 0),
        "max_hp": state.get("max_hp", 0),
        "base_attack": state.get("base_attack", 0),
        "base_defense": state.get("base_defense", 0),
        "base_magic": state.get("base_magic", 0),
        "attack": state.get("attack", 0),
        "defense": state.get("defense", 0),
        "magic": state.get("magic", 0),
        "cooldowns": {
            move_id: turns
            for move_id, turns in state.get("cooldowns", {}).items()
            if turns > 0
        },
        "active_effects": [
            effect for effect in state.get("active_effects", [])
            if effect.get("remaining", 0) > 0
        ],
        "last_move": state.get("last_move"),
        "enraged": state.get("enraged", False),
    }


def serialize_battle_state(battle_state):
    return {
        "turn": battle_state.get("turn", 1),
        "hero": serialize_character_state(battle_state.get("hero", {})),
        "monster": serialize_character_state(battle_state.get("monster", {})),
    }


def create_initial_run():
    characters = load_config("characters.json")
    moves = load_config("moves.json")
    base_hero = characters.get("hero", {})

    equipped_moves = [
        with_move_id(move_id, moves[move_id])
        for move_id in base_hero.get("default_moves", [])
        if move_id in moves
    ]

    hero_state = {
        "name": base_hero.get("name", "Knight"),
        "level": 1,
        "current_xp": 0,
        "max_hp": base_hero.get("max_hp", 100),
        "current_hp": base_hero.get("max_hp", 100),
        "attack": base_hero.get("attack", 10),
        "defense": base_hero.get("defense", 8),
        "magic": base_hero.get("magic", 5),
        "coins": base_hero.get("coins", 0),
        "current_skin": base_hero.get("current_skin", "knight_default"),
        "available_skins": base_hero.get("available_skins", {}),
        "equipped_moves": equipped_moves,
    }

    monsters_sorted = sorted(
        characters.get("monsters", []),
        key=lambda monster: monster.get("level_order", 99),
    )
    run_encounters = []
    for index, monster in enumerate(monsters_sorted):
        run_encounters.append({
            "order": monster.get("level_order"),
            "id": monster.get("id"),
            "name": monster.get("name"),
            "max_hp": monster.get("max_hp"),
            "attack": monster.get("attack", 0),
            "defense": monster.get("defense", 0),
            "magic": monster.get("magic", 0),
            "moves": monster.get("moves", []),
            "enrage_threshold": monster.get("enrage_threshold"),
            "enrage_buff_stat": monster.get("enrage_buff_stat"),
            "enrage_buff_value": monster.get("enrage_buff_value", 0),
            "enrage_unlock_moves": monster.get("enrage_unlock_moves", []),
            "status": "next" if index == 0 else "locked",
        })

    return {
        "hero": hero_state,
        "run_encounters": run_encounters,
    }


def create_battle_state(hero, monster):
    return {
        "turn": 1,
        "hero": build_character_state(
            current_hp=hero.get("current_hp", hero.get("max_hp", 100)),
            attack=hero.get("attack", 0),
            defense=hero.get("defense", 0),
            magic=hero.get("magic", 0),
            max_hp=hero.get("max_hp", 100),
            extra={"name": hero.get("name", "Hero")},
        ),
        "monster": build_character_state(
            current_hp=monster.get("hp", monster.get("max_hp", 1)),
            attack=monster.get("attack", 0),
            defense=monster.get("defense", 0),
            magic=monster.get("magic", 0),
            max_hp=monster.get("max_hp", 1),
            extra={
                "id": monster.get("id"),
                "name": monster.get("name", "Monster"),
                "enrage_threshold": monster.get("enrage_threshold"),
                "enrage_buff_stat": monster.get("enrage_buff_stat"),
                "enrage_buff_value": monster.get("enrage_buff_value", 0),
                "enrage_unlock_moves": monster.get("enrage_unlock_moves", []),
            },
        ),
    }


def normalize_battle_state(raw_state):
    state = raw_state or {}
    hero = state.get("hero", {})
    monster = state.get("monster", {})

    normalized = {
        "turn": state.get("turn", 1),
        "hero": {
            **hero,
            "cooldowns": hero.get("cooldowns", {}),
            "active_effects": hero.get("active_effects", []),
        },
        "monster": {
            **monster,
            "cooldowns": monster.get("cooldowns", {}),
            "active_effects": monster.get("active_effects", []),
        },
    }
    refresh_effective_stats(normalized["hero"])
    refresh_effective_stats(normalized["monster"])
    return normalized


def has_effect(target_state, requirement):
    if not requirement:
        return False

    return any(
        effect.get("source_move_id") == requirement
        or effect.get("effect_id") == requirement
        or effect.get("stat") == requirement
        for effect in target_state.get("active_effects", [])
        if effect.get("remaining", 0) > 0
    )


def apply_start_of_turn_effects(state, actor_label, events):
    kept_effects = []
    total_dot_damage = 0

    for effect in state.get("active_effects", []):
        if effect.get("remaining", 0) <= 0:
            continue

        effect = effect.copy()
        if effect.get("kind") != "dot":
            kept_effects.append(effect)
            continue

        damage = max(0, effect.get("damage", 0))
        state["hp"] = clamp(state.get("hp", 0) - damage, 0)
        total_dot_damage += damage
        events.append({
            "type": "dot",
            "target": actor_label,
            "source_move": effect.get("source_move"),
            "damage": damage,
        })

        effect["remaining"] -= 1
        if effect["remaining"] > 0:
            kept_effects.append(effect)

    state["active_effects"] = kept_effects
    refresh_effective_stats(state)
    return total_dot_damage


def tick_stat_effects(state):
    kept_effects = []

    for effect in state.get("active_effects", []):
        if effect.get("kind") != "stat_mod":
            kept_effects.append(effect)
            continue

        effect = effect.copy()
        effect["remaining"] -= 1
        if effect["remaining"] > 0:
            kept_effects.append(effect)

    state["active_effects"] = kept_effects
    refresh_effective_stats(state)


def tick_cooldowns(state, used_move_id=None):
    cooldowns = {}
    for move_id, turns in state.get("cooldowns", {}).items():
        if move_id == used_move_id:
            cooldowns[move_id] = turns
            continue
        next_turns = max(0, turns - 1)
        if next_turns > 0:
            cooldowns[move_id] = next_turns
    state["cooldowns"] = cooldowns


def set_move_cooldown(state, move_id, move):
    cooldown = max(0, move.get("cooldown", 0))
    if cooldown > 0:
        state.setdefault("cooldowns", {})[move_id] = cooldown


def apply_enrage_if_needed(monster_state, moves, events, target_label="monster"):
    if monster_state.get("enraged"):
        return

    threshold = monster_state.get("enrage_threshold")
    if threshold is None:
        return

    max_hp = max(1, monster_state.get("max_hp", 1))
    if monster_state.get("hp", 0) / max_hp > threshold:
        return

    stat = monster_state.get("enrage_buff_stat")
    value = monster_state.get("enrage_buff_value", 0)
    if stat == "attack":
        monster_state["base_attack"] = monster_state.get("base_attack", 0) + value
    elif stat == "defense":
        monster_state["base_defense"] = monster_state.get("base_defense", 0) + value
    elif stat == "magic":
        monster_state["base_magic"] = monster_state.get("base_magic", 0) + value

    monster_state["enraged"] = True
    refresh_effective_stats(monster_state)
    events.append({
        "type": "enrage",
        "target": target_label,
        "stat": stat,
        "amount": value,
        "unlocked_moves": [
            moves[move_id].get("name", move_id)
            for move_id in monster_state.get("enrage_unlock_moves", [])
            if move_id in moves
        ],
    })


def resolve_move(move_id, move, actor_state, target_state, actor_label, target_label):
    refresh_effective_stats(actor_state)
    refresh_effective_stats(target_state)

    effect = move.get("effect", "damage")
    move_name = move.get("name", "Unknown Move")
    stat_change = move.get("stat_change", 5)
    duration = move.get("duration", 0)
    combo_multiplier = 1
    combo_triggered = False

    if has_effect(target_state, move.get("combo_requirement_debuff")):
        combo_multiplier = max(combo_multiplier, move.get("combo_multiplier", 1.5))
        combo_triggered = True

    required_previous_move = move.get("combo_requirement_previous_move")
    if required_previous_move and actor_state.get("last_move") == required_previous_move:
        combo_multiplier = max(combo_multiplier, move.get("combo_multiplier", 1.5))
        combo_triggered = True

    result = {
        "move_id": move_id,
        "move_name": move_name,
        "effect": effect,
        "damage": 0,
        "heal": 0,
        "hp_cost": 0,
        "stat_changes": [],
        "applied_effects": [],
        "combo_triggered": combo_triggered,
        "combo_multiplier": combo_multiplier,
    }

    if effect in ("damage", "damage_and_debuff", "lifesteal", "dot", "damage_and_dot"):
        damage = calculate_damage(
            move=move,
            attacker_atk=actor_state.get("attack", 0),
            attacker_mag=actor_state.get("magic", 0),
            defender_def=target_state.get("defense", 0),
        )
        damage = int(round(damage * combo_multiplier))
        target_state["hp"] = clamp(target_state.get("hp", 0) - damage, 0)
        result["damage"] = damage

    if effect == "heal":
        before_hp = actor_state.get("hp", 0)
        heal_amount = max(0, move.get("base_value", 0) + actor_state.get("magic", 0))
        actor_state["hp"] = clamp(before_hp + heal_amount, 0, actor_state.get("max_hp", 0))
        result["heal"] = actor_state["hp"] - before_hp

    elif effect == "lifesteal":
        before_hp = actor_state.get("hp", 0)
        heal_amount = result["damage"]
        actor_state["hp"] = clamp(before_hp + heal_amount, 0, actor_state.get("max_hp", 0))
        result["heal"] = actor_state["hp"] - before_hp

    if effect in ("buff", "buff_with_cost"):
        target_stat = move.get("target_stat")
        if target_stat in ("attack", "defense", "magic"):
            actor_state.setdefault("active_effects", []).append({
                "kind": "stat_mod",
                "effect_id": f"{move_id}_{target_stat}_buff",
                "source_move_id": move_id,
                "source_move": move_name,
                "stat": target_stat,
                "amount": stat_change,
                "remaining": duration,
            })
            result["stat_changes"].append({
                "target": actor_label,
                "stat": target_stat,
                "change": stat_change,
                "duration": duration,
                "source_move": move_name,
            })

    if effect in ("debuff", "damage_and_debuff"):
        target_stat = move.get("target_stat")
        if target_stat in ("attack", "defense", "magic"):
            target_state.setdefault("active_effects", []).append({
                "kind": "stat_mod",
                "effect_id": f"{move_id}_{target_stat}_debuff",
                "source_move_id": move_id,
                "source_move": move_name,
                "stat": target_stat,
                "amount": -stat_change,
                "remaining": duration,
            })
            result["stat_changes"].append({
                "target": target_label,
                "stat": target_stat,
                "change": -stat_change,
                "duration": duration,
                "source_move": move_name,
            })

    if effect in ("dot", "damage_and_dot") and move.get("dot_damage", 0) > 0:
        target_state.setdefault("active_effects", []).append({
            "kind": "dot",
            "effect_id": move.get("dot_effect", move_id),
            "source_move_id": move_id,
            "source_move": move_name,
            "damage": move.get("dot_damage", 0),
            "remaining": duration,
        })
        result["applied_effects"].append({
            "target": target_label,
            "kind": "dot",
            "damage": move.get("dot_damage", 0),
            "duration": duration,
            "source_move": move_name,
        })

    if effect == "buff_with_cost":
        hp_cost = move.get("cost_hp", 0)
        actor_state["hp"] = clamp(actor_state.get("hp", 0) - hp_cost, 0)
        result["hp_cost"] = hp_cost

    actor_state["last_move"] = move_id
    refresh_effective_stats(actor_state)
    refresh_effective_stats(target_state)
    return result


def determine_winner(hero_state, monster_state):
    hero_dead = hero_state.get("hp", 0) <= 0
    monster_dead = monster_state.get("hp", 0) <= 0

    if hero_dead and monster_dead:
        return "draw"
    if monster_dead:
        return "hero"
    if hero_dead:
        return "monster"
    return None


def pick_monster_move(monster_state, monster_data, moves):
    move_ids = list(monster_data.get("moves", []))
    if monster_state.get("enraged"):
        move_ids.extend(monster_data.get("enrage_unlock_moves", []))

    available_move_ids = [
        move_id for move_id in move_ids
        if move_id in moves and monster_state.get("cooldowns", {}).get(move_id, 0) <= 0
    ]
    if not available_move_ids:
        return None
    return random.choice(available_move_ids)


def build_reward_data(monster_data, moves, hero_state, monster_state):
    if monster_state.get("hp", 0) > 0 or hero_state.get("hp", 0) <= 0:
        return None, None

    xp_earned = monster_data.get("max_hp", 50) // 2
    learned_move = None
    monster_move_list = monster_data.get("moves", [])
    if monster_move_list:
        learned_move_id = random.choice(monster_move_list)
        learned_move = with_move_id(learned_move_id, moves[learned_move_id])

    return xp_earned, learned_move


def play_turn(battle_state, hero_move_id):
    characters = load_config("characters.json")
    moves = load_config("moves.json")
    state = normalize_battle_state(battle_state)
    hero_state = state["hero"]
    monster_state = state["monster"]
    monster_id = monster_state.get("id")
    monster_data = next(
        (monster for monster in characters.get("monsters", []) if monster.get("id") == monster_id),
        None,
    )

    if not monster_data or hero_move_id not in moves:
        raise ValueError("Invalid monster or move ID")

    if hero_state.get("cooldowns", {}).get(hero_move_id, 0) > 0:
        raise ValueError("Move is on cooldown")

    events = []
    hero_dot_damage = apply_start_of_turn_effects(hero_state, "hero", events)
    if hero_state.get("hp", 0) <= 0:
        return build_turn_response(state, None, None, True, events, hero_dot_damage=hero_dot_damage)

    hero_move = moves[hero_move_id]
    hero_result = resolve_move(hero_move_id, hero_move, hero_state, monster_state, "hero", "monster")
    tick_cooldowns(hero_state, used_move_id=hero_move_id)
    set_move_cooldown(hero_state, hero_move_id, hero_move)

    apply_enrage_if_needed(monster_state, moves, events)

    monster_result = None
    monster_dot_damage = 0
    match_over = hero_state.get("hp", 0) <= 0 or monster_state.get("hp", 0) <= 0

    if not match_over:
        monster_dot_damage = apply_start_of_turn_effects(monster_state, "monster", events)
        apply_enrage_if_needed(monster_state, moves, events)
        match_over = hero_state.get("hp", 0) <= 0 or monster_state.get("hp", 0) <= 0

    if not match_over:
        monster_move_id = pick_monster_move(monster_state, monster_data, moves)
        if monster_move_id:
            monster_move = moves[monster_move_id]
            monster_result = resolve_move(
                monster_move_id,
                monster_move,
                monster_state,
                hero_state,
                "monster",
                "hero",
            )
            tick_cooldowns(monster_state, used_move_id=monster_move_id)
            set_move_cooldown(monster_state, monster_move_id, monster_move)
        else:
            tick_cooldowns(monster_state)
            monster_result = {
                "move_id": None,
                "move_name": "Recover",
                "effect": "skip",
                "damage": 0,
                "heal": 0,
                "hp_cost": 0,
                "stat_changes": [],
                "applied_effects": [],
                "combo_triggered": False,
                "combo_multiplier": 1,
            }

    tick_stat_effects(hero_state)
    tick_stat_effects(monster_state)
    state["turn"] = state.get("turn", 1) + 1

    return build_turn_response(
        state,
        hero_result,
        monster_result,
        hero_state.get("hp", 0) <= 0 or monster_state.get("hp", 0) <= 0,
        events,
        hero_dot_damage=hero_dot_damage,
        monster_dot_damage=monster_dot_damage,
    )


def build_turn_response(state, hero_result, monster_result, match_over, events, hero_dot_damage=0, monster_dot_damage=0):
    hero_result = hero_result or {
        "move_name": None,
        "effect": None,
        "damage": 0,
        "heal": 0,
        "hp_cost": 0,
        "stat_changes": [],
        "applied_effects": [],
        "combo_triggered": False,
        "combo_multiplier": 1,
    }
    monster_result = monster_result or {
        "move_name": None,
        "effect": None,
        "damage": 0,
        "heal": 0,
        "hp_cost": 0,
        "stat_changes": [],
        "applied_effects": [],
        "combo_triggered": False,
        "combo_multiplier": 1,
    }

    hero_state = state["hero"]
    monster_state = state["monster"]
    characters = load_config("characters.json")
    moves = load_config("moves.json")
    monster_data = next(
        (monster for monster in characters.get("monsters", []) if monster.get("id") == monster_state.get("id")),
        {},
    )
    xp_earned, learned_move = build_reward_data(monster_data, moves, hero_state, monster_state)

    response = {
        "hero_move": hero_result.get("move_name"),
        "hero_damage": hero_result.get("damage", 0),
        "hero_heal": hero_result.get("heal", 0),
        "hero_hp_cost": hero_result.get("hp_cost", 0),
        "hero_stat_changes": hero_result.get("stat_changes", []),
        "hero_applied_effects": hero_result.get("applied_effects", []),
        "hero_combo_triggered": hero_result.get("combo_triggered", False),
        "hero_combo_multiplier": hero_result.get("combo_multiplier", 1),
        "hero_dot_damage": hero_dot_damage,
        "monster_hp_remaining": monster_state.get("hp", 0),
        "monster_move": monster_result.get("move_name"),
        "monster_damage": monster_result.get("damage", 0),
        "monster_heal": monster_result.get("heal", 0),
        "monster_hp_cost": monster_result.get("hp_cost", 0),
        "monster_stat_changes": monster_result.get("stat_changes", []),
        "monster_applied_effects": monster_result.get("applied_effects", []),
        "monster_combo_triggered": monster_result.get("combo_triggered", False),
        "monster_combo_multiplier": monster_result.get("combo_multiplier", 1),
        "monster_dot_damage": monster_dot_damage,
        "hero_hp_remaining": hero_state.get("hp", 0),
        "hero_state": serialize_character_state(hero_state),
        "monster_state": serialize_character_state(monster_state),
        "battle_state": serialize_battle_state(state),
        "events": events,
        "match_over": match_over,
        "winner": determine_winner(hero_state, monster_state),
    }

    if xp_earned is not None:
        response["xp_earned"] = xp_earned
    if learned_move is not None:
        response["learned_move"] = learned_move

    return response
