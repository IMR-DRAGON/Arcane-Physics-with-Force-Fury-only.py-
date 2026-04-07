# 🌌 Arcane Physics Battle Simulator: Ultimate Edition v3.5 ⚔️🔥

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Pygame-CE 2.5+](https://img.shields.io/badge/Pygame--CE-2.5%2B-green?logo=pygame&logoColor=white)](https://pyga.me/)
[![Pymunk 7.0+](https://img.shields.io/badge/Pymunk-7.0%2B-orange?logo=pypi&logoColor=white)](http://www.pymunk.org/)
[![Status](https://img.shields.io/badge/Status-Optimized-brightgreen)](https://github.com/)

A high-performance, **physically-simulated 2D combat engine** optimized for cinematic "Let's Fight" content creation. Featuring a massive roster of **40+ hero classes** and over **70+ Legendary Pokémon from Gen 1 to Gen 8**, each with unique physics-based abilities and tactical AI.

---

## ✨ What's New in v3.5 "Legendary Strikes"?

- **🦸 Massive Roster Expansion:** Integrated **70+ Legendary & Mythical Pokémon** including *Mewtwo*, *Rayquaza*, *Arceus*, and *Zacian*, each with authentic movesets.
- **🎭 Kinetic "Juiciness" HUD:** Real-time **Squash & Stretch** deformation, **Hit-Stop** frames, and **Screen Shake** for maximum impact feel.
- **🌀 Battlefield Hazards:** Procedural effects like **Gravity Vortexes**, **Meteor Storms**, **EMP Pulses**, and **Healing Rituals**.
- **🤖 Tactical AI 2.0:** Entities now feature advanced pathfinding, kiting, and cooldown management logic for smarter "Brave Bird" or "Sword Slash" usage.
- **📊 Post-Match Dashboard:** Track **Total Damage**, **Luckiest Fighter**, and **MVP** metrics with a sleek new summary UI.

---

## 🛠 Prerequisites & Installation

Ensure you have a recent version of Python and the following high-performance libraries:

```powershell
pip install pygame-ce pymunk numpy
```

---

## 🎮 How to Play

### 🚀 Starting the Game
```powershell
python battle_sim.py
```

### 🕹 Controls
- **Main Menu**: Use **[MOUSE]** to browse the gallery. Click a character to add them to Team Blue/Red.
- **Battle Modes**:
  - **Team Battle**: Tactical Blue vs Red showdown (custom team sizes).
  - **Battle Royale**: A chaotic **8-way free-for-all** where only one survives.
- **In-Battle**:
  - **[ESC]**: Instantly return to menu.
  - **[SPACE]**: Reset on the results screen.
  - **Camera**: The camera automatically tracks the most intense action!

---

## 🔬 Under the Hood: The Engine

The simulator is built on a custom **Physics-First Architecture**:
- **Pymunk Integration**: Real-time collision detection and rigid-body dynamics for every character and projectile.
- **Zero-G Canvas**: A standard 540x960 portrait canvas optimized for mobile/short-form content.
- **Type Effectiveness**: A deep, Pokémon-inspired rock-paper-scissors system affecting damage multipliers.
- **Particle System**: Procedural spark, trails, and impact particles for every interaction.

---

## 🛠 Repository Structure

- `battle_sim.py`: The core engine, game loop, and UI logic.
- `pokemon_legendaries.py`: Massive data module for all legendary stats and moves.
- `generation-*/`: Optimized sprite assets for the entire roster.
- `balance_script.py`: Utility for fine-tuning match outcomes.

---
*Created by **Antigravity** & the **Arcane Physics** Team* 🏅🏆🏅
