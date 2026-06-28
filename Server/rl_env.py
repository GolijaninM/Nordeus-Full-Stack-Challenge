import json
import random
from dataclasses import dataclass
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from game_engine import (
    apply_enrage_if_needed,
    apply_start_of_turn_effects,
    build_character_state,
    determine_winner,
    load_config,
    resolve_move,
    serialize_battle_state,
    set_move_cooldown,
    tick_cooldowns,
    tick_stat_effects,
)


MAX_STAT_VALUE = 100.0
MAX_HP_VALUE = 700.0
MAX_BASE_VALUE = 100.0
MAX_COOLDOWN_VALUE = 5.0
MAX_EFFECT_DURATION = 5.0
OBSERVATION_SIZE = 36

MOVE_TYPE_CODES = {
    "physical": 1.0 / 3.0,
    "magic": 2.0 / 3.0,
    "status": 1.0,
}


@dataclass(frozen=True)
class CharacterTemplate:
    id: str
    name: str
    max_hp: int
    attack: int
    defense: int
    magic: int
    moves: tuple[str, ...]
    enrage_threshold: float | None = None
    enrage_buff_stat: str | None = None
    enrage_buff_value: int = 0
    enrage_unlock_moves: tuple[str, ...] = ()


class RandomBotPolicy:
    def select_action(self, observation, valid_actions, env=None):
        if not valid_actions:
            return 0
        rng = env.np_random if env is not None else random
        return int(rng.choice(valid_actions))


class ModelPolicy:
    def __init__(self, model, deterministic=False):
        self.model = model
        self.deterministic = deterministic

    def select_action(self, observation, valid_actions, env=None):
        action, _ = self.model.predict(observation, deterministic=self.deterministic)
        action = int(action)
        if action in valid_actions:
            return action
        if not valid_actions:
            return 0
        rng = env.np_random if env is not None else random
        return int(rng.choice(valid_actions))


class TournamentEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        opponent_pool=None,
        max_turns=80,
        invalid_action_penalty=-1.0,
        character_config_path=None,
        starting_actor_mode="opener",
    ):
        super().__init__()
        if starting_actor_mode not in ("opener", "flag_only"):
            raise ValueError("starting_actor_mode must be 'opener' or 'flag_only'.")

        self.moves_config = load_config("moves.json")
        self.character_config_path = character_config_path
        self.starting_actor_mode = starting_actor_mode
        self.characters = self._load_character_templates()
        self.opponent_pool = opponent_pool or [RandomBotPolicy()]
        self.max_turns = max_turns
        self.invalid_action_penalty = invalid_action_penalty

        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(OBSERVATION_SIZE,),
            dtype=np.float32,
        )

        self.agent_template = None
        self.opponent_template = None
        self.agent_moves = []
        self.opponent_moves = []
        self.opponent_policy = self.opponent_pool[0]
        self.battle_state = None
        self.starting_actor = "agent"
        self.agent_started = True
        self.last_info = {}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}

        agent_template = options.get("agent_template")
        opponent_template = options.get("opponent_template")
        requested_starting_actor = options.get("starting_actor")

        self.agent_template = agent_template or self._sample_character()
        self.opponent_template = opponent_template or self._sample_character(exclude_id=self.agent_template.id)
        self.opponent_policy = self._sample_opponent_policy()
        self.starting_actor = requested_starting_actor or self._sample_starting_actor()
        self.agent_started = self.starting_actor == "agent"

        self.agent_moves = list(self.agent_template.moves[:4])
        self.opponent_moves = list(self.opponent_template.moves[:4])
        self.battle_state = {
            "turn": 1,
            "hero": self._state_from_template(self.agent_template),
            "monster": self._state_from_template(self.opponent_template),
        }

        opening_events = []
        opening_action = None
        opening_move = None
        if self.starting_actor_mode == "opener" and self.starting_actor == "opponent":
            opening_action, opening_result = self._play_opponent_opener(opening_events)
            opening_move = opening_result.get("move_id") if opening_result else None

        self.last_info = {
            "agent_id": self.agent_template.id,
            "opponent_id": self.opponent_template.id,
            "opponent_policy": type(self.opponent_policy).__name__,
            "starting_actor": self.starting_actor,
            "starting_actor_mode": self.starting_actor_mode,
            "agent_started": self.agent_started,
            "opponent_opening_action": opening_action,
            "opponent_opening_move": opening_move,
            "opening_events": opening_events,
        }
        return self._get_observation(), self.last_info.copy()

    def step(self, action):
        if self.battle_state is None:
            raise RuntimeError("Call reset() before step().")

        action = int(action)
        previous_agent_hp = self.battle_state["hero"]["hp"]
        previous_opponent_hp = self.battle_state["monster"]["hp"]
        reward = -0.01
        events = []

        invalid_agent_action = self._is_invalid_action(action, self.battle_state["hero"], self.agent_moves)
        agent_result = self._resolve_actor_turn(
            actor_key="hero",
            target_key="monster",
            actor_moves=self.agent_moves,
            action=action,
            actor_label="agent",
            target_label="opponent",
            events=events,
            skip_action=invalid_agent_action,
        )

        if invalid_agent_action:
            reward += self.invalid_action_penalty

        winner = determine_winner(self.battle_state["hero"], self.battle_state["monster"])
        if winner is None:
            opponent_observation = self._get_observation(agent_perspective=False)
            opponent_action = self.opponent_policy.select_action(
                opponent_observation,
                self._valid_actions(self.battle_state["monster"], self.opponent_moves),
                env=self,
            )
            opponent_result = self._resolve_actor_turn(
                actor_key="monster",
                target_key="hero",
                actor_moves=self.opponent_moves,
                action=opponent_action,
                actor_label="opponent",
                target_label="agent",
                events=events,
            )
        else:
            opponent_action = None
            opponent_result = None

        tick_stat_effects(self.battle_state["hero"])
        tick_stat_effects(self.battle_state["monster"])
        self.battle_state["turn"] += 1

        agent_hp = self.battle_state["hero"]["hp"]
        opponent_hp = self.battle_state["monster"]["hp"]
        damage_dealt = max(0, previous_opponent_hp - opponent_hp)
        damage_taken = max(0, previous_agent_hp - agent_hp)
        reward += (damage_dealt / max(1, self.battle_state["monster"]["max_hp"])) * 2.0
        reward -= (damage_taken / max(1, self.battle_state["hero"]["max_hp"])) * 1.5

        winner = determine_winner(self.battle_state["hero"], self.battle_state["monster"])
        terminated = winner is not None
        truncated = self.battle_state["turn"] > self.max_turns

        if winner == "hero":
            reward += 10.0
        elif winner == "monster":
            reward -= 10.0
        elif winner == "draw":
            reward -= 2.0
        elif truncated:
            reward -= 1.0

        info = {
            **self.last_info,
            "turn": self.battle_state["turn"],
            "winner": winner,
            "invalid_action": invalid_agent_action,
            "agent_action": action,
            "opponent_action": opponent_action,
            "agent_move": agent_result.get("move_id") if agent_result else None,
            "opponent_move": opponent_result.get("move_id") if opponent_result else None,
            "agent_result": agent_result,
            "opponent_result": opponent_result,
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "events": events,
            "battle_state": serialize_battle_state(self.battle_state),
        }
        self.last_info = info
        return self._get_observation(), float(reward), terminated, truncated, info

    def _resolve_actor_turn(self, actor_key, target_key, actor_moves, action, actor_label, target_label, events, skip_action=False):
        actor_state = self.battle_state[actor_key]
        target_state = self.battle_state[target_key]

        apply_start_of_turn_effects(actor_state, actor_label, events)
        if actor_state.get("hp", 0) <= 0:
            return None

        if skip_action:
            tick_cooldowns(actor_state)
            return {
                "move_id": None,
                "move_name": "Invalid Action",
                "damage": 0,
                "heal": 0,
            }

        move_id = actor_moves[action]
        move = self.moves_config[move_id]
        result = resolve_move(move_id, move, actor_state, target_state, actor_label, target_label)
        tick_cooldowns(actor_state, used_move_id=move_id)
        set_move_cooldown(actor_state, move_id, move)
        apply_enrage_if_needed(target_state, self.moves_config, events, target_label=target_label)
        apply_enrage_if_needed(actor_state, self.moves_config, events, target_label=actor_label)
        return result

    def _is_invalid_action(self, action, actor_state, actor_moves):
        if action < 0 or action >= len(actor_moves):
            return True
        move_id = actor_moves[action]
        if move_id not in self.moves_config:
            return True
        return actor_state.get("cooldowns", {}).get(move_id, 0) > 0

    def _valid_actions(self, actor_state, actor_moves):
        return [
            index for index, move_id in enumerate(actor_moves)
            if move_id in self.moves_config
            and actor_state.get("cooldowns", {}).get(move_id, 0) <= 0
        ]

    def _get_observation(self, agent_perspective=True):
        if agent_perspective:
            agent_state = self.battle_state["hero"]
            opponent_state = self.battle_state["monster"]
            agent_moves = self.agent_moves
        else:
            agent_state = self.battle_state["monster"]
            opponent_state = self.battle_state["hero"]
            agent_moves = self.opponent_moves

        values = []
        values.extend(self._encode_stats(agent_state, include_enrage=False))
        values.extend(self._encode_moves(agent_moves, agent_state))
        values.extend(self._encode_status(agent_state, agent_moves))
        values.extend(self._encode_stats(opponent_state, include_enrage=True))
        values.extend(self._encode_status(opponent_state, []))
        side_started = self.agent_started if agent_perspective else not self.agent_started
        values.append(1.0 if side_started else 0.0)

        observation = np.array(values, dtype=np.float32)
        if observation.shape != self.observation_space.shape:
            raise RuntimeError(f"Observation shape {observation.shape} does not match {self.observation_space.shape}.")
        return np.clip(observation, 0.0, 1.0)

    def _encode_stats(self, state, include_enrage):
        stats = [
            self._scale(state.get("hp", 0), MAX_HP_VALUE),
            self._scale(state.get("max_hp", 0), MAX_HP_VALUE),
            self._scale(state.get("attack", 0), MAX_STAT_VALUE),
            self._scale(state.get("defense", 0), MAX_STAT_VALUE),
            self._scale(state.get("magic", 0), MAX_STAT_VALUE),
        ]
        if include_enrage:
            stats.append(1.0 if state.get("enraged") else 0.0)
        return stats

    def _encode_moves(self, move_ids, actor_state):
        encoded = []
        for slot in range(4):
            move_id = move_ids[slot] if slot < len(move_ids) else None
            move = self.moves_config.get(move_id, {})
            encoded.extend([
                MOVE_TYPE_CODES.get(move.get("type"), 0.0),
                self._scale(move.get("base_value", 0), MAX_BASE_VALUE),
                self._scale(actor_state.get("cooldowns", {}).get(move_id, 0), MAX_COOLDOWN_VALUE),
            ])
        return encoded

    def _encode_status(self, state, move_ids):
        attack_mod = 0.0
        defense_mod = 0.0
        magic_mod = 0.0
        poison_remaining = 0.0
        burn_remaining = 0.0

        for effect in state.get("active_effects", []):
            remaining = self._scale(effect.get("remaining", 0), MAX_EFFECT_DURATION)
            if effect.get("kind") == "stat_mod":
                if effect.get("stat") == "attack":
                    attack_mod = max(attack_mod, remaining)
                elif effect.get("stat") == "defense":
                    defense_mod = max(defense_mod, remaining)
                elif effect.get("stat") == "magic":
                    magic_mod = max(magic_mod, remaining)
            elif effect.get("kind") == "dot":
                if effect.get("effect_id") == "poison":
                    poison_remaining = max(poison_remaining, remaining)
                elif effect.get("effect_id") == "burn":
                    burn_remaining = max(burn_remaining, remaining)

        last_move = state.get("last_move")
        if last_move in move_ids:
            last_move_slot = (move_ids.index(last_move) + 1) / 4.0
        else:
            last_move_slot = 0.0

        return [attack_mod, defense_mod, magic_mod, poison_remaining, burn_remaining, last_move_slot]

    def _state_from_template(self, template):
        return build_character_state(
            current_hp=template.max_hp,
            attack=template.attack,
            defense=template.defense,
            magic=template.magic,
            max_hp=template.max_hp,
            extra={
                "id": template.id,
                "name": template.name,
                "enrage_threshold": template.enrage_threshold,
                "enrage_buff_stat": template.enrage_buff_stat,
                "enrage_buff_value": template.enrage_buff_value,
                "enrage_unlock_moves": list(template.enrage_unlock_moves),
            },
        )

    def _sample_character(self, exclude_id=None):
        candidates = [character for character in self.characters if character.id != exclude_id]
        index = int(self.np_random.integers(0, len(candidates)))
        return candidates[index]

    def _sample_opponent_policy(self):
        index = int(self.np_random.integers(0, len(self.opponent_pool)))
        return self.opponent_pool[index]

    def _sample_starting_actor(self):
        return "agent" if int(self.np_random.integers(0, 2)) == 0 else "opponent"

    def _play_opponent_opener(self, events):
        opponent_observation = self._get_observation(agent_perspective=False)
        opponent_action = self.opponent_policy.select_action(
            opponent_observation,
            self._valid_actions(self.battle_state["monster"], self.opponent_moves),
            env=self,
        )
        opponent_result = self._resolve_actor_turn(
            actor_key="monster",
            target_key="hero",
            actor_moves=self.opponent_moves,
            action=opponent_action,
            actor_label="opponent",
            target_label="agent",
            events=events,
        )
        return opponent_action, opponent_result

    def _load_character_templates(self):
        characters = self._load_character_config()
        templates = []

        hero = characters.get("hero", {})
        templates.append(CharacterTemplate(
            id=hero.get("id", "knight"),
            name=hero.get("name", "Knight"),
            max_hp=hero.get("max_hp", 100),
            attack=hero.get("attack", 0),
            defense=hero.get("defense", 0),
            magic=hero.get("magic", 0),
            moves=tuple(hero.get("default_moves", [])[:4]),
        ))

        for monster in characters.get("monsters", []):
            templates.append(CharacterTemplate(
                id=monster.get("id"),
                name=monster.get("name"),
                max_hp=monster.get("max_hp", 1),
                attack=monster.get("attack", 0),
                defense=monster.get("defense", 0),
                magic=monster.get("magic", 0),
                moves=tuple(monster.get("moves", [])[:4]),
                enrage_threshold=monster.get("enrage_threshold"),
                enrage_buff_stat=monster.get("enrage_buff_stat"),
                enrage_buff_value=monster.get("enrage_buff_value", 0),
                enrage_unlock_moves=tuple(monster.get("enrage_unlock_moves", [])),
            ))

        return [template for template in templates if len(template.moves) == 4]

    def _load_character_config(self):
        if not self.character_config_path:
            return load_config("characters.json")

        config_path = Path(self.character_config_path)
        if not config_path.is_absolute():
            config_path = Path(__file__).resolve().parent / config_path

        with config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _scale(value, maximum):
        if maximum <= 0:
            return 0.0
        return float(max(0.0, min(1.0, value / maximum)))
