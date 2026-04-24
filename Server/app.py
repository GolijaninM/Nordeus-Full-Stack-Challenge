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


def calculate_damage(move, attacker_atk, attacker_mag, defender_def):
    move_type = move.get("type")
    base = move.get("base_value", 0)

    if move_type == "physical":
        damage = (base + attacker_atk) - defender_def
    elif move_type == "magic":
        damage = base + attacker_mag
    else:
        damage = 0

    return damage

@app.route('/api/start-run', methods=['GET'])
def start_run():
    try:
        characters = load_config('characters.json')
        moves = load_config('moves.json')
    except:
        return jsonify({'error': 'Failed to load configuration files'}), 500

    base_hero = characters.get('hero',{})

    # Initial hero moves
    equipped_moves=[]
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
    run_encounters=[]
    monsters=characters.get('monsters',[])
    monsters_sorted=sorted(monsters,key=lambda x: x.get('level_order',99))

    for index,monster in enumerate(monsters_sorted):
        run_encounters.append({
            "order": monster.get("level_order"),
            "id": monster.get("id"),
            "name": monster.get("name"),
            "max_hp": monster.get("max_hp"),
            "status": "next" if index==0 else "locked"
        })

    return jsonify({
        "hero": hero_state,
        "run_encounters": run_encounters
    })


@app.route('/api/play-turn', methods=['GET'])
def play_turn():

    hero_hp = int(request.args.get('hero_hp'))
    hero_atk = int(request.args.get('hero_atk',0))
    hero_def = int(request.args.get('hero_def',0))
    hero_mag = int(request.args.get('hero_mag',0))

    monster_id = request.args.get('monster_id')
    monster_hp = int(request.args.get('monster_hp'))
    hero_move_id = request.args.get('move_id')

    characters = load_config('characters.json')
    moves = load_config('moves.json')

    monsters = characters.get('monsters', [])
    monster_data = next((m for m in monsters if m['id'] == monster_id), None)

    if not monster_data or hero_move_id not in moves:
        return jsonify({"error": "Invalid monster or move ID"}), 400

    # Calculate Hero's turn
    hero_move = moves[hero_move_id]
    hero_dmg = calculate_damage(
        move=hero_move,
        attacker_atk=hero_atk,
        attacker_mag=hero_mag,
        defender_def=monster_data.get('defense', 0)
    )

    new_monster_hp = monster_hp - hero_dmg

    # Check if the monster died from the hero's attack
    if new_monster_hp <= 0:
        return jsonify({
            "hero_move": hero_move.get("name"),
            "hero_damage": hero_dmg,
            "monster_hp_remaining": 0,
            "monster_move": None,
            "monster_damage": 0,
            "hero_hp_remaining": hero_hp,
            "match_over": True,
            "winner": "hero"
        })

    # Calculate Monster's turn (Random)
    monster_move_list = monster_data.get('moves', [])
    random_monster_move_id = random.choice(monster_move_list)
    monster_move = moves[random_monster_move_id]

    monster_dmg = calculate_damage(
        move=monster_move,
        attacker_atk=monster_data.get('attack', 0),
        attacker_mag=monster_data.get('magic', 0),
        defender_def=hero_def
    )

    new_hero_hp = hero_hp - monster_dmg

    # Check if hero died
    match_over = new_hero_hp <= 0
    winner = "monster" if match_over else None

    return jsonify({
        "hero_move": hero_move.get("name"),
        "hero_damage": hero_dmg,
        "monster_hp_remaining": new_monster_hp,
        "monster_move": monster_move.get("name"),
        "monster_damage": monster_dmg,
        "hero_hp_remaining": new_hero_hp,
        "match_over": match_over,
        "winner": winner
    })


if __name__ == '__main__':
    app.run(debug=True)