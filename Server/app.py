from flask import Flask, jsonify, request
import random
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)


def load_config(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'config', filename)

    with open(file_path, 'r') as file:
        return json.load(file)


def clamp(value, minimum=0, maximum=None):
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def get_int_arg(name, default=0):
    raw_value = request.args.get(name)
    if raw_value in (None, ''):
        return default

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def calculate_damage(move, attacker_atk, attacker_mag, defender_def):
    move_type = move.get("type")
    base = move.get("base_value", 0)

    if move_type == "physical":
        damage = (base + attacker_atk) - defender_def
    elif move_type == "magic":
        damage = base + attacker_mag
    else:
        damage = 0

    return max(0, damage)


def build_character_state(current_hp, attack, defense, magic, max_hp):
    return {
        "hp": current_hp,
        "attack": attack,
        "defense": defense,
        "magic": magic,
        "max_hp": max_hp,
    }


def serialize_state(state):
    return {
        "hp": state.get("hp", 0),
        "attack": state.get("attack", 0),
        "defense": state.get("defense", 0),
        "magic": state.get("magic", 0),
        "max_hp": state.get("max_hp", 0),
    }


def resolve_move(move, actor_state, target_state, actor_label, target_label):
    effect = move.get("effect", "damage")
    move_name = move.get("name", "Unknown Move")
    stat_change = move.get("stat_change", 5)
    duration = move.get("duration", 0)

    result = {
        "move_name": move_name,
        "effect": effect,
        "damage": 0,
        "heal": 0,
        "hp_cost": 0,
        "stat_changes": [],
    }

    if effect in ("damage", "damage_and_debuff", "lifesteal"):
        damage = calculate_damage(
            move=move,
            attacker_atk=actor_state.get("attack", 0),
            attacker_mag=actor_state.get("magic", 0),
            defender_def=target_state.get("defense", 0),
        )
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
            actor_state[target_stat] = max(0, actor_state.get(target_stat, 0) + stat_change)
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
            target_state[target_stat] = max(0, target_state.get(target_stat, 0) - stat_change)
            result["stat_changes"].append({
                "target": target_label,
                "stat": target_stat,
                "change": -stat_change,
                "duration": duration,
                "source_move": move_name,
            })

    if effect == "buff_with_cost":
        hp_cost = move.get("cost_hp", 0)
        actor_state["hp"] = clamp(actor_state.get("hp", 0) - hp_cost, 0)
        result["hp_cost"] = hp_cost

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


def build_turn_response(hero_state, monster_state, hero_result, monster_result=None, match_over=False, winner=None, xp_earned=None, learned_move=None):
    monster_result = monster_result or {
        "move_name": None,
        "effect": None,
        "damage": 0,
        "heal": 0,
        "hp_cost": 0,
        "stat_changes": [],
    }

    response = {
        "hero_move": hero_result.get("move_name"),
        "hero_damage": hero_result.get("damage", 0),
        "hero_heal": hero_result.get("heal", 0),
        "hero_hp_cost": hero_result.get("hp_cost", 0),
        "hero_stat_changes": hero_result.get("stat_changes", []),
        "monster_hp_remaining": monster_state.get("hp", 0),
        "monster_move": monster_result.get("move_name"),
        "monster_damage": monster_result.get("damage", 0),
        "monster_heal": monster_result.get("heal", 0),
        "monster_hp_cost": monster_result.get("hp_cost", 0),
        "monster_stat_changes": monster_result.get("stat_changes", []),
        "hero_hp_remaining": hero_state.get("hp", 0),
        "hero_state": serialize_state(hero_state),
        "monster_state": serialize_state(monster_state),
        "match_over": match_over,
        "winner": winner,
    }

    if xp_earned is not None:
        response["xp_earned"] = xp_earned
    
    if learned_move is not None:
        response["learned_move"] = learned_move

    return jsonify(response)


@app.route('/api/start-run', methods=['GET'])
def start_run():
    try:
        characters = load_config('characters.json')
        moves = load_config('moves.json')
    except:
        return jsonify({'error': 'Failed to load configuration files'}), 500

    base_hero = characters.get('hero', {})

    # Initial hero moves
    equipped_moves = []
    for move in base_hero.get('default_moves', []):
        if move in moves:
            move_detail = moves[move].copy()
            move_detail['id'] = move
            equipped_moves.append(move_detail)

    # Initial hero state
    hero_state = {
        "name": base_hero.get("name", "Knight"),
        "level": 1,
        "current_xp": 0,
        "max_hp": base_hero.get("max_hp", 100),
        "current_hp": base_hero.get("max_hp", 100),
        "attack": base_hero.get("attack", 10),
        "defense": base_hero.get("defense", 8),
        "magic": base_hero.get("magic", 5),
        "equipped_moves": equipped_moves
    }

    # Initial monsters state
    run_encounters = []
    monsters = characters.get('monsters', [])
    monsters_sorted = sorted(monsters, key=lambda x: x.get('level_order', 99))

    for index, monster in enumerate(monsters_sorted):
        run_encounters.append({
            "order": monster.get("level_order"),
            "id": monster.get("id"),
            "name": monster.get("name"),
            "max_hp": monster.get("max_hp"),
            "status": "next" if index == 0 else "locked"
        })

    return jsonify({
        "hero": hero_state,
        "run_encounters": run_encounters
    })


@app.route('/api/play-turn', methods=['GET'])
def play_turn():
    hero_hp = get_int_arg('hero_hp')
    hero_atk = get_int_arg('hero_atk', 0)
    hero_def = get_int_arg('hero_def', 0)
    hero_mag = get_int_arg('hero_mag', 0)

    monster_id = request.args.get('monster_id')
    monster_hp = get_int_arg('monster_hp')
    hero_move_id = request.args.get('move_id')

    characters = load_config('characters.json')
    moves = load_config('moves.json')

    monsters = characters.get('monsters', [])
    monster_data = next((m for m in monsters if m['id'] == monster_id), None)
    base_hero = characters.get('hero', {})

    hero_max_hp = get_int_arg('hero_max_hp', base_hero.get('max_hp', 100))
    monster_max_hp = monster_data.get('max_hp', monster_hp) if monster_data else monster_hp

    if not monster_data or hero_move_id not in moves:
        return jsonify({"error": "Invalid monster or move ID"}), 400

    hero_state = build_character_state(
        current_hp=hero_hp,
        attack=hero_atk,
        defense=hero_def,
        magic=hero_mag,
        max_hp=hero_max_hp,
    )

    monster_state = build_character_state(
        current_hp=monster_hp,
        attack=monster_data.get('attack', 0),
        defense=monster_data.get('defense', 0),
        magic=monster_data.get('magic', 0),
        max_hp=monster_max_hp,
    )

    # Resolve hero's turn first.
    hero_move = moves[hero_move_id]
    hero_result = resolve_move(hero_move, hero_state, monster_state, "hero", "monster")

    # End immediately if the hero's action ends the battle.
    if monster_state.get("hp", 0) <= 0 or hero_state.get("hp", 0) <= 0:
        # Check if the monster died from the hero's attack (hero wins)
        xp_earned = None
        learned_move = None
        
        if monster_state.get("hp", 0) <= 0 and hero_state.get("hp", 0) > 0:
            # Calculate XP (e.g., half of the monster's max HP)
            xp_earned = monster_data.get('max_hp', 50) // 2
            
            # Pick a random move from the monster to learn
            monster_move_list = monster_data.get('moves', [])
            if monster_move_list:
                learned_move_id = random.choice(monster_move_list)
                learned_move = moves[learned_move_id].copy()
                learned_move['id'] = learned_move_id  # Ensure the ID is attached
        
        return build_turn_response(
            hero_state=hero_state,
            monster_state=monster_state,
            hero_result=hero_result,
            match_over=True,
            winner=determine_winner(hero_state, monster_state),
            xp_earned=xp_earned,
            learned_move=learned_move,
        )

    # Resolve monster's retaliation.
    monster_move_list = monster_data.get('moves', [])
    random_monster_move_id = random.choice(monster_move_list) if monster_move_list else None
    monster_move = moves.get(random_monster_move_id) if random_monster_move_id else None

    monster_result = {
        "move_name": None,
        "effect": None,
        "damage": 0,
        "heal": 0,
        "hp_cost": 0,
        "stat_changes": [],
    }

    if monster_move:
        monster_result = resolve_move(monster_move, monster_state, hero_state, "monster", "hero")

    match_over = hero_state.get("hp", 0) <= 0 or monster_state.get("hp", 0) <= 0

    # Check if the monster died after retaliation (hero wins)
    xp_earned = None
    learned_move = None
    
    if match_over and monster_state.get("hp", 0) <= 0 and hero_state.get("hp", 0) > 0:
        # Calculate XP (e.g., half of the monster's max HP)
        xp_earned = monster_data.get('max_hp', 50) // 2
        
        # Pick a random move from the monster to learn
        monster_move_list = monster_data.get('moves', [])
        if monster_move_list:
            learned_move_id = random.choice(monster_move_list)
            learned_move = moves[learned_move_id].copy()
            learned_move['id'] = learned_move_id  # Ensure the ID is attached

    return build_turn_response(
        hero_state=hero_state,
        monster_state=monster_state,
        hero_result=hero_result,
        monster_result=monster_result,
        match_over=match_over,
        winner=determine_winner(hero_state, monster_state),
        xp_earned=xp_earned,
        learned_move=learned_move,
    )


if __name__ == '__main__':
    app.run(debug=True)