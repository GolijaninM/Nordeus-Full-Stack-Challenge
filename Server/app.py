from flask import Flask, jsonify, request
from flask_cors import CORS

from game_engine import create_battle_state, create_initial_run, load_config, play_turn as engine_play_turn

app = Flask(__name__)
CORS(app)


def get_int_arg(name, default=0):
    raw_value = request.args.get(name)
    if raw_value in (None, ""):
        return default

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


@app.route("/api/start-run", methods=["GET"])
def start_run():
    try:
        return jsonify(create_initial_run())
    except Exception:
        return jsonify({"error": "Failed to load configuration files"}), 500


def build_legacy_battle_state():
    characters = load_config("characters.json")
    monster_id = request.args.get("monster_id")
    monster_data = next(
        (monster for monster in characters.get("monsters", []) if monster.get("id") == monster_id),
        None,
    )
    base_hero = characters.get("hero", {})

    if not monster_data:
        return None

    hero_max_hp = get_int_arg("hero_max_hp", base_hero.get("max_hp", 100))
    hero = {
        "name": base_hero.get("name", "Hero"),
        "current_hp": get_int_arg("hero_hp"),
        "max_hp": hero_max_hp,
        "attack": get_int_arg("hero_atk", base_hero.get("attack", 0)),
        "defense": get_int_arg("hero_def", base_hero.get("defense", 0)),
        "magic": get_int_arg("hero_mag", base_hero.get("magic", 0)),
    }
    monster = {
        **monster_data,
        "hp": get_int_arg("monster_hp", monster_data.get("max_hp", 1)),
    }
    return create_battle_state(hero, monster)


@app.route("/api/play-turn", methods=["GET", "POST"])
def play_turn():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        hero_move_id = payload.get("move_id")
        battle_state = payload.get("battle_state")

        if not battle_state and payload.get("hero") and payload.get("monster"):
            battle_state = create_battle_state(payload["hero"], payload["monster"])
    else:
        hero_move_id = request.args.get("move_id")
        battle_state = build_legacy_battle_state()

    try:
        return jsonify(engine_play_turn(battle_state, hero_move_id))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        return jsonify({"error": "Failed to process turn"}), 500


if __name__ == "__main__":
    app.run(debug=True)
