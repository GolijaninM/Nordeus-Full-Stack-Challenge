from flask import Flask, jsonify
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

    for index,monster in enumerate(monsters_sorted):\
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


if __name__ == '__main__':
    app.run(debug=True)