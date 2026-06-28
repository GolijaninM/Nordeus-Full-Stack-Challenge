# Server and RL Environment

This folder contains the Flask API, the shared battle engine, and the first Gymnasium environment used for reinforcement learning experiments.

## Files

- `app.py`
  - Flask API layer for the web game.
  - Exposes `/api/start-run` and `/api/play-turn`.
  - Should stay thin: HTTP in, JSON out. Core combat rules belong in `game_engine.py`.

- `game_engine.py`
  - Shared pure Python battle logic.
  - Handles damage, healing, buffs, debuffs, DoT, cooldowns, combos, enrage, winner detection, and battle state serialization.
  - Used by both Flask and RL code, so game rules stay consistent between the UI and training.

- `rl_env.py`
  - Gymnasium environment for model training.
  - Main class: `TournamentEnv`.
  - Uses `spaces.Discrete(4)` actions, where action `0` means "use move slot 0", not a global move name.
  - Uses a normalized `spaces.Box` observation vector.
  - Randomizes matchups in `reset()` so one universal model can learn to play as different characters.
  - Randomizes initiative: sometimes the agent starts, sometimes the opponent opens before the first agent observation.
  - Can use a training-only character config through `character_config_path`.
  - Includes `RandomBotPolicy` and `ModelPolicy` for future opponent-pool/self-play training.

- `rl_training/`
  - Training-only helpers and configs.
  - `configs/characters_balanced.json` is the current balanced character setup for RL experiments.
  - `evaluation.py` contains shared evaluation/report helpers.
  - `evaluate_dqn.py` evaluates a saved DQN checkpoint and writes matchup breakdowns.

- `train_universal.py`
  - Initial training scaffold.
  - Currently structured around PPO-style checkpoint self-play, but the environment itself is not PPO-specific.
  - PPO/DQN/SAC can use `TournamentEnv` through Stable-Baselines3.
  - NEAT should use the same env through a separate genome evaluation loop.

- `train_dqn.py`
  - First concrete training script.
  - Trains a DQN agent against `RandomBotPolicy`.
  - Uses `rl_training/configs/characters_balanced.json` by default.
  - Saves the model, a CSV reward log, a PNG training curve, a small evaluation report, and matchup breakdowns.

- `requirements.txt`
  - Backend/RL dependencies currently needed for Flask and Gymnasium.

- `config/characters.json`
  - Defines the hero and monster templates.
  - Includes base stats, HP, move slots, and enrage settings.
  - This remains the default game/UI config.

- `config/moves.json`
  - Defines move behavior.
  - Includes damage/heal/status effects, cooldowns, DoT, and combo metadata.

## Current RL Interface

### Action Space

```python
spaces.Discrete(4)
```

Actions are slot-based:

```text
0 -> use current character move slot 0
1 -> use current character move slot 1
2 -> use current character move slot 2
3 -> use current character move slot 3
```

The model should not learn global move names like `slash` or `firebolt`. It should learn from the move properties in the observation vector.

### Observation Space

```python
spaces.Box(low=0.0, high=1.0, shape=(36,), dtype=np.float32)
```

The current observation vector is:

```text
Agent stats:
0  current_hp
1  max_hp
2  attack
3  defense
4  magic

Agent move slot 0:
5  move_type
6  base_value
7  cooldown_remaining

Agent move slot 1:
8  move_type
9  base_value
10 cooldown_remaining

Agent move slot 2:
11 move_type
12 base_value
13 cooldown_remaining

Agent move slot 3:
14 move_type
15 base_value
16 cooldown_remaining

Agent statuses:
17 attack_modifier_remaining
18 defense_modifier_remaining
19 magic_modifier_remaining
20 poison_remaining
21 burn_remaining
22 last_move_slot

Opponent stats:
23 current_hp
24 max_hp
25 attack
26 defense
27 magic
28 enrage_flag

Opponent statuses:
29 attack_modifier_remaining
30 defense_modifier_remaining
31 magic_modifier_remaining
32 poison_remaining
33 burn_remaining
34 last_move_slot

Initiative:
35 side_started_flag
```

`side_started_flag` is perspective-based:

```text
1.0 -> the side receiving this observation started the battle
0.0 -> the other side started the battle
```

This matters for self-play, where the same model may receive observations from either side.

## Quick Checks

From this folder:

```powershell
.\.venv\Scripts\python.exe -B -c "from gymnasium.utils.env_checker import check_env; from rl_env import TournamentEnv; check_env(TournamentEnv(), skip_render_check=True); print('check_env ok')"
```

Smoke test:

```powershell
.\.venv\Scripts\python.exe -B -c "from rl_env import TournamentEnv; env=TournamentEnv(); obs, info=env.reset(seed=1); print(obs.shape, env.observation_space.contains(obs), info)"
```

Expected observation shape:

```text
(36,)
```

## Training Plan

The intended training tracks are:

- DQN/DQL
- PPO
- SAC
- NEAT

Recommended next steps before long training runs:

1. Add a random-vs-random baseline evaluation script.
2. Add one training script per algorithm:
   - `train_dqn.py`
   - `train_ppo.py`
   - `train_sac.py`
   - `train_neat.py`
3. Add tournament/evaluation scripts for comparing checkpoints.
4. Tune reward shaping after observing baseline results.

## DQN Training

Install backend/RL dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run a short smoke training:

```powershell
.\.venv\Scripts\python.exe train_dqn.py --timesteps 2000 --eval-episodes 5 --output-dir models/dqn_smoke
```

Run a longer first experiment:

```powershell
.\.venv\Scripts\python.exe train_dqn.py --timesteps 100000 --eval-episodes 50 --output-dir models/dqn
```

This uses the balanced RL character config by default:

```text
rl_training/configs/characters_balanced.json
```

To train against the original game balance instead:

```powershell
.\.venv\Scripts\python.exe train_dqn.py --timesteps 100000 --eval-episodes 50 --output-dir models/dqn_original --character-config config/characters.json
```

Outputs:

```text
models/dqn/dqn_model.zip
models/dqn/dqn_training_curve.csv
models/dqn/dqn_training_curve.png
models/dqn/dqn_evaluation.txt
models/dqn/dqn_matchup_breakdown.txt
```

The curve is episode reward over time, with a moving average overlay. Early DQN runs may look noisy because matchups, character roles, and initiative are randomized.

Evaluate an existing DQN model without retraining:

```powershell
.\.venv\Scripts\python.exe rl_training\evaluate_dqn.py --model models\dqn\dqn_model.zip --episodes 200
```

The matchup breakdown compares DQN against a valid-random baseline using the same seeds and reports:

```text
overall
agent_character
opponent_character
dragon_presence
initiative
```

## DQN Mixed Opponent Training

After training baseline DQN checkpoints against `RandomBotPolicy`, the next phase is to train against a mixed opponent pool.

Example 50/25/25 pool:

```powershell
.\.venv\Scripts\python.exe train_dqn.py --timesteps 1000000 --eval-episodes 500 --breakdown-episodes 500 --output-dir models\DQN\balanced_opener\dqn_mixed_v2_1m --character-config rl_training/configs/characters_balanced.json --random-opponents 2 --opponent-models models\DQN\balanced_opener\dqn_balanced_v2_100k\dqn_model.zip models\DQN\balanced_opener\dqn_balanced_v2_300k\dqn_model.zip
```

This means:

```text
2 RandomBotPolicy entries
1 DQN 100k opponent
1 DQN 300k opponent
```

The environment samples uniformly from the pool, so the effective opponent distribution is:

```text
50% RandomBotPolicy
25% DQN 100k
25% DQN 300k
```

The mixed training report includes:

```text
DQN vs training opponent pool
DQN vs RandomBotPolicy
DQN vs each opponent model
Valid-random vs RandomBotPolicy
```

## PPO Training

PPO uses the same `TournamentEnv`, balanced character config, fair initiative mode, matchup breakdowns, and symmetric evaluation as DQN. The only intended difference is the learning algorithm.

Run a short smoke training:

```powershell
.\.venv\Scripts\python.exe -B train_ppo.py --timesteps 64 --eval-episodes 3 --breakdown-episodes 3 --output-dir models\PPO\fair_init\ppo_smoke --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 1
```

Phase 1, random-only 100k:

```powershell
.\.venv\Scripts\python.exe -B train_ppo.py --timesteps 100000 --eval-episodes 500 --breakdown-episodes 500 --output-dir models\PPO\fair_init\ppo_fair_random_100k --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 5
```

Phase 1, random-only 300k:

```powershell
.\.venv\Scripts\python.exe -B train_ppo.py --timesteps 300000 --eval-episodes 500 --breakdown-episodes 500 --output-dir models\PPO\fair_init\ppo_fair_random_300k --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 5
```

Phase 2, mixed opponent pool:

```powershell
.\.venv\Scripts\python.exe -B train_ppo.py --timesteps 1000000 --eval-episodes 500 --breakdown-episodes 500 --output-dir models\PPO\fair_init\ppo_fair_mixed_phase2_1m --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 5 --random-opponents 2 --opponent-models models\PPO\fair_init\ppo_fair_random_100k\ppo_model.zip models\PPO\fair_init\ppo_fair_random_300k\ppo_model.zip
```

Phase 3, final PPO self-play:

```powershell
.\.venv\Scripts\python.exe -B train_ppo.py --timesteps 1000000 --eval-episodes 1000 --breakdown-episodes 1000 --output-dir models\PPO\fair_init\ppo_fair_phase3_final_1m --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 10 --random-opponents 1 --opponent-models models\PPO\fair_init\ppo_fair_random_300k\ppo_model.zip models\PPO\fair_init\ppo_fair_mixed_phase2_1m\ppo_model.zip models\PPO\fair_init\ppo_fair_mixed_phase2_1m\ppo_model.zip
```

Outputs:

```text
models/PPO/fair_init/<run_name>/ppo_model.zip
models/PPO/fair_init/<run_name>/ppo_training_curve.csv
models/PPO/fair_init/<run_name>/ppo_training_curve.png
models/PPO/fair_init/<run_name>/ppo_evaluation.txt
models/PPO/fair_init/<run_name>/ppo_matchup_breakdown.txt
models/PPO/fair_init/<run_name>/ppo_symmetric_tournament.txt
```

Evaluate an existing PPO model without retraining:

```powershell
.\.venv\Scripts\python.exe -B rl_training\evaluate_ppo.py --model models\PPO\fair_init\ppo_fair_phase3_final_1m\ppo_model.zip --episodes 1000 --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 10
```

## Fair Initiative Mode

The original environment uses:

```text
--starting-actor-mode opener
```

In this mode, if the opponent starts, it immediately plays an opening move during `reset()` before the agent gets its first action.

For fairer algorithm comparisons, use:

```text
--starting-actor-mode flag_only
```

In this mode the observation still contains `side_started_flag`, but the opponent does not receive a free opening move before the agent's first action.

Example fair-init DQN run:

```powershell
.\.venv\Scripts\python.exe train_dqn.py --timesteps 300000 --eval-episodes 500 --breakdown-episodes 500 --output-dir models\DQN\fair_init\dqn_fair_random_300k --character-config rl_training/configs/characters_balanced.json --starting-actor-mode flag_only --symmetric-eval --episodes-per-matchup 10
```

Symmetric evaluation tests every ordered character matchup with both starting actors:

```text
agent starts
opponent starts
```

This is the preferred evaluation mode for comparing DQN, PPO, SAC, and NEAT.

Evaluate an existing model against the same mixed pool:

```powershell
.\.venv\Scripts\python.exe rl_training\evaluate_dqn.py --model models\DQN\balanced_opener\dqn_mixed_v2_1m\dqn_model.zip --episodes 500 --character-config rl_training/configs/characters_balanced.json --random-opponents 2 --opponent-models models\DQN\balanced_opener\dqn_balanced_v2_100k\dqn_model.zip models\DQN\balanced_opener\dqn_balanced_v2_300k\dqn_model.zip
```

## Model Folders

DQN experiment outputs are grouped under:

```text
models/DQN/
```

Current groups:

```text
models/DQN/original_unbalanced/
models/DQN/balanced_opener/
models/DQN/fair_init/
models/PPO/fair_init/
```

- `original_unbalanced/` contains early DQN runs against the original game character balance.
- `balanced_opener/` contains balanced-character DQN runs that still use the old opener initiative mode.
- `fair_init/` is for new runs using `--starting-actor-mode flag_only`.
- `models/PPO/fair_init/` contains PPO runs that follow the same fair-init methodology as final DQN.

## Notes

- Do not put training-only logic into `app.py`.
- Do not duplicate combat rules in training scripts.
- Keep `game_engine.py` as the single source of truth for battle mechanics.
- If the observation vector changes after training starts, old model checkpoints may no longer be compatible.
