# ⚔️ Shadows of Nordeus

> A full-stack, turn-based roguelike battle demo.

**Shadows of Nordeus** is a web-based RPG prototype that bridges the gap between dark fantasy adventure and modern web development. What begins as a seamless full-stack architecture demo quickly evolves into a treacherous gauntlet of tactical battles, persistent progression, and strategic character building.

Forge your legend as you **explore a mysterious forest**, outsmart monstrous foes to **unlock powerful new abilities and stylish skins**, and keep a sharp eye on your surroundings—you never know what **hidden Easter eggs** are waiting to be unearthed in the shadows!

---

### ✨ Key Features

- **Stateless Combat Resolution:** A Python-driven backend handles all heavy lifting, ensuring secure, tamper-proof battle math, damage calculation, and turn simulation.
- **Dynamic Hero Progression:** A flexible leveling system where players dynamically allocate stats to tailor their build, integrated seamlessly with a custom XP growth curve.
- **Persistent Architecture:** Complete run preservation utilizing browser-native local storage, allowing users to pause and resume their journey, maintain their inventory, and save their map state.
- **Modular UI/UX Design:** Built with React, featuring animated combat arenas, interactive map routing, and responsive design for a polished, game-like feel in the browser.
- **Expandable Loot & Entity Systems:** A highly scalable JSON-based architecture making it incredibly easy to inject new monsters, abilities, and cosmetic skins into the game loop.

---

### 💻 Tech Stack

**Frontend (Client)**

- **React 18** – UI architecture and complex state management
- **Vite** – Ultra-fast module bundling and local development
- **Pure CSS3** – Custom animations, dynamic HUDs, and responsive layout styling

**Backend (Server)**

- **Python 3.8+** – Core game logic and mathematics
- **Flask** – Lightweight REST API routing
- **Flask-CORS** – Secure cross-origin resource sharing

---

### 🚀 Getting Started

To run this project locally, you will need two terminal windows: one for the server and one for the client.

#### 1. Boot up the Server

The Python server handles the API endpoints (`/api/start-run` and `/api/play-turn`). It runs on port `5000`.

Open a terminal in your `server/` directory:

**Windows:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install flask flask-cors
python app.py
```

**macOS / Linux::**

```powershell
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-cors
python app.py
```

#### 2. Launch the Client

The React frontend handles the UI and communicates with the Flask server.

Open a second terminal in your client/ directory:

```powershell
npm install
npm run dev
```
