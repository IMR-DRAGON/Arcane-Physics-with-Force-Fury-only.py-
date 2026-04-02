# 🌌 Arcane Physics Battle Simulator 🐍💥

A high-performance, physics-based 2D battle simulator featuring **40 unique character classes**, dynamic arena hazards, and a premium "Combat Juiciness" update. Face off in team battles or intense Battle Royale (BR) modes where every impact, explosion, and ability strike is physically simulated.

## ✨ Latest Features: "The Juiciness & Stats Update"
- **🥊 Combat Weight:** Implemented **Hit-Stop (Freeze-Frame)** on heavy internal impacts (60ms–120ms) and dynamic screenshake.
- **📸 Visual Feedback:** Critical hit popups, impact flashes, and gold particle leveling rings.
- **📊 Match Statistics & MVP:** Comprehensive post-match dashboard tracking **Total Kills**, **Damage Dealt**, and **Luckiest** fighter (highest trait activations).
- **📈 Global Leveling:** Fighters scale in size (8%) and damage (15%) with every kill, becoming "Boss" threats.
- **⚖️ Strategic Hazards:** Incremental stage damage (1.0 + 0.6 per hit) and shrinking arena **Sudden Death** with periodic void damage.
- **🕒 Pre-Match Flow:** Professional 1.0s "READY... FIGHT!" countdown with frozen character starts.

## 🛠 Prerequisites
Ensure you have the following installed to run the simulator:
- **Python 3.10+** (Recommend 3.14 for maximum performance)
- **pygame-ce** (For high-performance 2D rendering and sound)
- **pymunk** (For realistic rigid-body physics)
- **numpy** (For vector mathematics)

```bash
pip install pygame-ce pymunk numpy
```

## 🎮 How to Play
1. **🚀 Run the Game:**
   ```bash
   python battle_sim.py
   ```
2. **🕹 Controls:**
   - **Main Menu:** Use mouse to select Character 'A' and Character 'B'.
   - **Toggle Mode:** Click the center icon to switch between **Team Battle** (Blue vs Red) and **Battle Royale** (Every fighter for themselves).
   - **Start Match:** Hit the **Fight!** button (requires at least 2 fighters).
   - **Post-Match:** Press **[SPACE]** on the results screen to return to the character selection menu.

## 🔬 Physics & AI
The simulation runs on a high-frequency **Pymunk 7+** space with a gravity-aware collision matrix. Each of the 40+ fighters features a custom "Strategic Stealth & Strafe" AI that reacts to health percentages, distance, and ability cooldowns.

---
*Built with Arcane Physics & Force Fury principles.* 🏆🔥🏅
