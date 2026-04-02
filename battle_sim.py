import pygame
import pymunk
import pymunk.pygame_util
import math
import random
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import numpy as np

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1440, 900
FPS = 60
GRAVITY = 0

class SoundManager:
    def __init__(self):
        if not pygame.mixer.get_init():
            # Use 1024 buffer for better stability on some Windows systems
            pygame.mixer.init(44100, -16, 2, 1024)
        self.sounds = {}
        self._build_sounds()

    def _gen_hit(self):
        sr = 44100
        dur = 0.08
        t = np.linspace(0, dur, int(sr*dur))
        noise = np.random.uniform(-1, 1, len(t))
        # Smoother hit: apply low-pass feel with a steeper envelope
        env = np.exp(-40 * t)
        buf = (noise * env * 0.15 * 32767).astype(np.int16) # Lower volume (0.15 vs 1.0)
        stereo = np.column_stack((buf, buf))
        self.sounds['hit'] = pygame.sndarray.make_sound(stereo)

    def _gen_shoot(self):
        sr = 44100
        dur = 0.12
        t = np.linspace(0, dur, int(sr*dur))
        freq = np.linspace(1200, 400, len(t))
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-20 * t)
        buf = (snd * env * 0.2 * 32767).astype(np.int16)
        stereo = np.column_stack((buf, buf))
        self.sounds['shoot'] = pygame.sndarray.make_sound(stereo)

    def _gen_special(self):
        sr = 44100
        dur = 0.4
        t = np.linspace(0, dur, int(sr*dur))
        freq = 200 + np.sin(2 * np.pi * 12 * t) * 80
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-6 * t)
        buf = (snd * env * 0.3 * 32767).astype(np.int16)
        stereo = np.column_stack((buf, buf))
        self.sounds['special'] = pygame.sndarray.make_sound(stereo)

    def _gen_slash(self):
        sr = 44100
        dur = 0.1
        t = np.linspace(0, dur, int(sr*dur))
        freq = np.linspace(1500, 800, len(t))
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-35 * t)
        buf = (snd * env * 0.25 * 32767).astype(np.int16)
        stereo = np.column_stack((buf, buf))
        self.sounds['slash'] = pygame.sndarray.make_sound(stereo)

    def _gen_thud(self):
        sr = 44100
        dur = 0.2
        t = np.linspace(0, dur, int(sr*dur))
        freq = np.linspace(150, 40, len(t))
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-15 * t)
        buf = (snd * env * 0.6 * 32767).astype(np.int16)
        stereo = np.column_stack((buf, buf))
        self.sounds['thud'] = pygame.sndarray.make_sound(stereo)

    def _gen_heal(self):
        sr = 44100
        dur = 0.3
        t = np.linspace(0, dur, int(sr*dur))
        freq = np.linspace(400, 1200, len(t))
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-10 * t)
        buf = (snd * env * 0.2 * 32767).astype(np.int16)
        stereo = np.column_stack((buf, buf))
        self.sounds['heal'] = pygame.sndarray.make_sound(stereo)

    def _build_sounds(self):
        self._gen_hit()
        self._gen_shoot()
        self._gen_special()
        self._gen_slash()
        self._gen_thud()
        self._gen_heal()

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

# Colors
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_BG     = (10,  10,  20)
ARENA_FLOOR = (30,  30,  50)
PANEL_BG    = (15,  15,  30)
GOLD        = (255, 200, 50)
RED         = (220, 50,  50)
GREEN       = (50,  220, 80)
BLUE        = (50,  120, 255)
PURPLE      = (160, 50,  255)
ORANGE      = (255, 140, 0)
CYAN        = (0,   220, 220)
PINK        = (255, 80,  180)
YELLOW      = (255, 230, 0)
LIME        = (140, 255, 0)
TEAL        = (0,   200, 180)
CRIMSON     = (180, 0,   40)
SILVER      = (180, 190, 200)
BROWN       = (140, 90,  40)

# ─── PARTICLE SYSTEM ─────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, vx, vy, color, size, life, gravity=True):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.gravity = gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.gravity:
            self.vy += 600 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, screen):
        alpha = max(0, self.life / self.max_life)
        size = max(1, int(self.size * alpha))
        c = tuple(min(255, int(ch * (0.5 + 0.5*alpha))) for ch in self.color)
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), size)

class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, x, y, color, count=8, speed=150, spread=math.pi*2,
             size=4, life=0.6, gravity=True, direction=0):
        for _ in range(count):
            angle = direction + random.uniform(-spread/2, spread/2)
            spd   = random.uniform(speed*0.4, speed)
            vx    = math.cos(angle) * spd
            vy    = math.sin(angle) * spd
            sz    = random.uniform(size*0.5, size)
            lt    = random.uniform(life*0.5, life)
            self.particles.append(Particle(x, y, vx, vy, color, sz, lt, gravity))

    def emit_trap(self, x, y, color, size=60, count=20):
        # A closing geometric trap effect
        for i in range(count):
            ang = (i / count) * math.pi * 2
            px = x + math.cos(ang) * size
            py = y + math.sin(ang) * size
            # Particles that move towards the center
            vx = -math.cos(ang) * 150
            vy = -math.sin(ang) * 150
            self.particles.append(Particle(px, py, vx, vy, color, 6, 0.5, False))

    def emit_ring(self, x, y, color, count=12, speed=120, size=3, life=0.5):
        for i in range(count):
            angle = (2 * math.pi / count) * i
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x, y, vx, vy, color, size, life, False))

    def emit_beam(self, x1, y1, x2, y2, color, count=10, size=3, life=0.3):
        for _ in range(count):
            t = random.random()
            px = x1 + (x2-x1)*t + random.uniform(-8,8)
            py = y1 + (y2-y1)*t + random.uniform(-8,8)
            self.particles.append(Particle(px, py, 0, 0, color, size, life, False))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

class DamagePopup:
    def __init__(self, x, y, text, color=WHITE, is_crit=False):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.is_crit = is_crit
        self.life = 1.0
        self.vx = random.uniform(-40, 40)
        self.vy = -80 if is_crit else -60
        self.scale = 1.5 if is_crit else 1.0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        # If crit, shake a bit
        if self.is_crit:
            self.x += random.uniform(-2, 2)
        return self.life > 0

    def draw(self, screen, font, font_big):
        alpha = int(self.life * 255)
        use_font = font_big if self.is_crit else font
        text_surf = use_font.render(self.text, True, self.color)
        if self.is_crit:
            # Scale it up slightly
            s = int(self.scale + (1.0 - self.life)*0.5)
            # (In pygame simpler to just use a bigger font)
            pass
        text_surf.set_alpha(alpha)
        screen.blit(text_surf, (self.x - text_surf.get_width()//2, self.y))

class Projectile:
    def __init__(self, x, y, vx, vy, damage, color, size, owner_team,
                 trail_color=None, piercing=False, homing=False, aoe_radius=0, owner=None):
        self.owner = owner
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.damage = damage
        self.color = color
        self.size = size
        self.owner_team = owner_team
        self.trail_color = trail_color or color
        self.piercing = piercing
        self.homing = homing
        self.aoe_radius = aoe_radius
        self.alive = True
        self.trail = []
        self.gravity_affected = False

    def update(self, dt, targets):
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 8:
            self.trail.pop(0)
        if self.homing and targets:
            closest = min(targets, key=lambda t: math.hypot(t.x-self.x, t.y-self.y))
            dx = closest.x - self.x
            dy = closest.y - self.y
            dist = max(1, math.hypot(dx, dy))
            self.vx += (dx/dist) * 300 * dt
            self.vy += (dy/dist) * 300 * dt
            spd = math.hypot(self.vx, self.vy)
            if spd > 600:
                self.vx = self.vx/spd*600
                self.vy = self.vy/spd*600
        if self.gravity_affected:
            self.vy += GRAVITY * 0.3 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -50 or self.x > WIDTH+50 or self.y > HEIGHT+50 or self.y < -200:
            self.alive = False

    def draw(self, screen):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = (i+1) / len(self.trail)
            sz = max(1, int(self.size * alpha * 0.7))
            c = tuple(int(ch * alpha) for ch in self.trail_color)
            pygame.draw.circle(screen, c, (tx, ty), sz)
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
        # glow
        glow_surf = pygame.Surface((self.size*4, self.size*4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 60),
                          (self.size*2, self.size*2), self.size*2)
        screen.blit(glow_surf, (int(self.x)-self.size*2, int(self.y)-self.size*2))

# ─── ABILITY DEFINITIONS ─────────────────────────────────────────────────────
@dataclass
class Ability:
    name: str
    cooldown: float
    damage: float
    range: float
    color: Tuple
    description: str
    timer: float = 0.0

    def ready(self):
        return self.timer <= 0

    def use(self):
        self.timer = self.cooldown

    def tick(self, dt):
        if self.timer > 0:
            self.timer -= dt

# ─── CHARACTER DEFINITIONS ───────────────────────────────────────────────────
CHARACTER_DATA = {
    "⚔️ Warrior": {
        "color": (200, 150, 50),
        "body_color": (180, 100, 30),
        "hp": 500,
        "speed": 220,
        "mass": 3.0,
        "size": 18,
        "description": "Heavily armored melee fighter\nHigh HP, slow but deadly at close range",
        "abilities": [
            Ability("Sword Slash",   0.8,  70, 80,  GOLD,   "Powerful melee swing"),
            Ability("Shield Bash",   2.0,  40, 60,  SILVER, "Knocks enemy back hard"),
            Ability("War Cry",       8.0,  30, 200, ORANGE, "AOE shout damages all nearby"),
            Ability("Berserker",    15.0, 120, 90,  CRIMSON,"Devastating power attack"),
        ],
        "dodge_rate": 0.1,
        "weapon_type": "sword",
        "has_shield": True
    },
    "🔮 Mage": {
        "color": (100, 80, 220),
        "body_color": (80, 60, 200),
        "hp": 350,
        "speed": 200,
        "mass": 1.8,
        "size": 16,
        "description": "Arcane spellcaster\nLow HP but powerful ranged magic",
        "abilities": [
            Ability("Fireball",     1.0,  75, 500, ORANGE, "Explosive fire projectile"),
            Ability("Ice Shard",    0.7,  45, 600, CYAN,   "Piercing ice projectile"),
            Ability("Lightning",    1.5,  90, 450, YELLOW, "Chain lightning bolt"),
            Ability("Meteor",      12.0, 200, 600, RED,    "Massive meteor strike"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🥷 Ninja": {
        "color": (60, 60, 80),
        "body_color": (40, 40, 60),
        "hp": 380,
        "speed": 340,
        "mass": 1.5,
        "size": 15,
        "description": "Shadow assassin\nExtreme speed, teleport, combo attacks",
        "abilities": [
            Ability("Shuriken",     0.5,  35, 500, SILVER, "3x rapid shurikens"),
            Ability("Shadow Step",  3.0,  60, 100, PURPLE, "Teleport + backstab"),
            Ability("Smoke Bomb",   5.0,  25, 150, (100,100,100), "Confuse + area damage"),
            Ability("Death Mark",  10.0, 150, 300, CRIMSON,"Guaranteed critical hit"),
        ],
        "dodge_rate": 0.35,
        "weapon_type": "katana",
        "has_shield": False
    },
    "🐉 Dragon": {
        "color": (180, 50, 30),
        "body_color": (140, 30, 20),
        "hp": 600,
        "speed": 180,
        "mass": 4.0,
        "size": 22,
        "description": "Ancient fire dragon\nMassive HP, fire breath, flight",
        "abilities": [
            Ability("Fire Breath",  0.9,  65, 250, ORANGE, "Cone of fire particles"),
            Ability("Tail Whip",    1.5,  80, 100, BROWN,  "Sweeping tail AOE"),
            Ability("Wing Slam",    4.0,  60, 180, RED,    "Shockwave from wings"),
            Ability("Dragon Rage", 14.0, 250, 300, CRIMSON,"Full power fire explosion"),
        ],
        "dodge_rate": 0.08,
        "weapon_type": "claws",
        "has_shield": False
    },
    "👿 Demon": {
        "color": (160, 30, 30),
        "body_color": (120, 20, 20),
        "hp": 450,
        "speed": 240,
        "mass": 2.5,
        "size": 19,
        "description": "Hellish demon lord\nLife steal, dark magic, curses",
        "abilities": [
            Ability("Dark Claw",    0.7,  55, 90,  CRIMSON,"Life-stealing melee"),
            Ability("Hell Spike",   1.2,  70, 400, (150,0,50), "Homing dark projectile"),
            Ability("Soul Drain",   5.0,  40, 200, PURPLE, "Drains HP, heals self"),
            Ability("Hellfire",    11.0, 180, 350, ORANGE, "Rain of fire pillars"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "trident",
        "has_shield": False
    },
    "🤖 Robot": {
        "color": (100, 130, 160),
        "body_color": (80, 110, 140),
        "hp": 480,
        "speed": 210,
        "mass": 3.5,
        "size": 20,
        "description": "Combat android\nPrecise laser targeting, missiles, shield",
        "abilities": [
            Ability("Laser Beam",   0.6,  50, 600, CYAN,   "Precise energy beam"),
            Ability("Missile",      1.5,  90, 700, ORANGE, "Homing rocket"),
            Ability("EMP Blast",    6.0,  45, 250, BLUE,   "AOE electric pulse"),
            Ability("Overdrive",   13.0, 170, 500, YELLOW, "Rapid-fire laser barrage"),
        ],
        "dodge_rate": 0.12
    },
    "🌪️ Elemental": {
        "color": (80, 180, 220),
        "body_color": (60, 160, 200),
        "hp": 400,
        "speed": 260,
        "mass": 1.2,
        "size": 17,
        "description": "Wind & storm spirit\nTornado, lightning storm, levitation",
        "abilities": [
            Ability("Gust",         0.6,  40, 300, CYAN,   "Wind pushes enemies back"),
            Ability("Tornado",      2.5,  85, 200, TEAL,   "Spinning wind vortex"),
            Ability("Thunderbolt",  1.8,  95, 500, YELLOW, "Direct lightning strike"),
            Ability("Storm",       12.0, 200, 400, BLUE,   "Full screen storm barrage"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🧛 Vampire": {
        "color": (130, 50, 130),
        "body_color": (100, 30, 100),
        "hp": 420,
        "speed": 250,
        "mass": 2.0,
        "size": 17,
        "description": "Undead bloodsucker\nLife steal, bats, transform into mist",
        "abilities": [
            Ability("Blood Drain",  0.8,  50, 100, CRIMSON,"Suck life from enemy"),
            Ability("Bat Swarm",    2.0,  60, 350, PURPLE, "Launch swarm of bats"),
            Ability("Mist Form",    5.0,  20, 150, (150,150,200), "Phase through attacks"),
            Ability("Drain Life",   9.0, 140, 250, PINK,   "Massive HP steal attack"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🏹 Archer": {
        "color": (80, 150, 60),
        "body_color": (60, 120, 40),
        "hp": 360,
        "speed": 280,
        "mass": 1.6,
        "size": 15,
        "description": "Precision marksman\nLong range, rapid shots, explosive arrows",
        "abilities": [
            Ability("Arrow Shot",   0.4,  40, 700, LIME,   "Quick precision arrow"),
            Ability("Multi-Shot",   1.5,  30, 650, GREEN,  "5 arrows at once"),
            Ability("Poison Arrow", 2.0,  25, 600, (100,200,50), "Poison DOT arrow"),
            Ability("Rain of Arrows",10.0,160,500, ORANGE, "Arrow storm on target"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "bow",
        "has_shield": False
    },
    "🔱 Poseidon": {
        "color": (30, 100, 200),
        "body_color": (20, 80, 180),
        "hp": 500,
        "speed": 200,
        "mass": 3.0,
        "size": 20,
        "description": "God of the seas\nWater waves, trident attacks, tidal force",
        "abilities": [
            Ability("Trident",      0.9,  65, 150, BLUE,   "Powerful trident thrust"),
            Ability("Water Blast",  1.3,  70, 450, CYAN,   "High-pressure water shot"),
            Ability("Tidal Wave",   5.0, 100, 300, BLUE,   "Sweeping wave knockback"),
            Ability("Maelstrom",   13.0, 220, 400, TEAL,   "Massive water vortex"),
        ],
        "dodge_rate": 0.12,
        "weapon_type": "trident",
        "has_shield": False
    },
    "🕸️ Web-Slinger": {
        "color": (200, 30, 30),
        "body_color": (30, 50, 200),
        "hp": 400,
        "speed": 320,
        "mass": 1.8,
        "size": 16,
        "description": "Web-swinging hero\nHigh mobility, stuns, and rapid melee",
        "abilities": [
            Ability("Web Shot",     0.6,  30, 500, WHITE,  "Stuns enemy with webs"),
            Ability("Web Swing",    2.5,  50, 400, BLUE,   "Dashing kick attack"),
            Ability("Spider-Sense", 6.0,  20, 150, RED,    "Quick dodge & counter"),
            Ability("Web Barrage", 12.0, 180, 500, WHITE,  "Multiple webs trap all"),
        ],
        "dodge_rate": 0.3
    },
    "🚀 Tech-Armor": {
        "color": (200, 50, 50),
        "body_color": (220, 200, 50),
        "hp": 450,
        "speed": 230,
        "mass": 2.8,
        "size": 18,
        "description": "High-tech armored suit\nEnergy beams, missiles, and flight",
        "abilities": [
            Ability("Repulsor",    0.7,  55, 550, CYAN,   "Energy blast from palm"),
            Ability("Mini-Missile", 1.8,  80, 650, ORANGE, "Homing mini-rockets"),
            Ability("Uni-Beam",     7.0, 130, 700, WHITE,  "Massive chest laser"),
            Ability("Rocket Barrage", 14.0, 220, 500, RED, "Full weapon discharge"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🟢 Gamma-Giant": {
        "color": (50, 180, 50),
        "body_color": (120, 50, 180),
        "hp": 750,
        "speed": 160,
        "mass": 5.0,
        "size": 25,
        "description": "Unstoppable force\nHuge HP, massive smash damage",
        "abilities": [
            Ability("Smash",        1.0,  90, 100, GREEN,  "Powerful ground punch"),
            Ability("Gamma Leap",   3.0,  70, 300, LIME,   "Jumps and lands hard"),
            Ability("Thunderclap",  5.0,  60, 250, WHITE,  "Shockwave stuns nearby"),
            Ability("Hulk Rage",   15.0, 280, 350, RED,    "Devastating multi-smash"),
        ],
        "dodge_rate": 0.05,
        "weapon_type": "fists",
        "has_shield": False
    },
    "⚡ Thunder-God": {
        "color": (100, 200, 255),
        "body_color": (180, 180, 200),
        "hp": 550,
        "speed": 200,
        "mass": 3.5,
        "size": 20,
        "description": "God of Thunder\nLightning strikes & Mjolnir throws",
        "abilities": [
            Ability("Hammer Throw", 0.9,  75, 600, SILVER, "Mjolnir flies and returns"),
            Ability("Lightning",    1.5,  95, 450, YELLOW, "Call down a bolt"),
            Ability("Shockwave",    4.0,  65, 200, CYAN,   "Hammer slam AOE"),
            Ability("God Blast",   13.0, 240, 500, WHITE,  "Ultimate lightning storm"),
        ],
        "dodge_rate": 0.12,
        "weapon_type": "hammer",
        "has_shield": False
    },
    "🛡️ Star-Soldier": {
        "color": (30, 80, 200),
        "body_color": (200, 30, 30),
        "hp": 520,
        "speed": 250,
        "mass": 2.5,
        "size": 18,
        "description": "Peak human soldier\nMaster of shield combat & defense",
        "abilities": [
            Ability("Shield Toss",  1.0,  60, 550, SILVER, "Ricochet shield attack"),
            Ability("Combat Combo", 0.7,  45, 90,  BLUE,   "Rapid martial arts"),
            Ability("Shield Charge",3.0,  70, 250, WHITE,  "Unstoppable dash bash"),
            Ability("Final Stand", 12.0, 180, 300, RED,    "Heroic series of blows"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "shield_only",
        "has_shield": True
    },
    "🐾 Jungle-King": {
        "color": (40, 40, 40),
        "body_color": (150, 120, 255),
        "hp": 480,
        "speed": 310,
        "mass": 2.0,
        "size": 17,
        "description": "Vibranium-enhanced warrior\nFast claws & kinetic energy",
        "abilities": [
            Ability("Claw Slash",   0.6,  50, 80,  PURPLE, "Quick vibranium slashes"),
            Ability("Pounce",       2.5,  65, 300, DARK_BG,"Lunging leap attack"),
            Ability("Kinetic Burst",6.0,  90, 220, PINK,   "Releases stored energy"),
            Ability("Panther Hunt",11.0, 170, 400, SILVER, "Stealthy rapid strikes"),
        ],
        "dodge_rate": 0.3,
        "weapon_type": "claws",
        "has_shield": False
    },
    "🧪 Toxic-Widow": {
        "color": (30, 30, 30),
        "body_color": (200, 30, 30),
        "hp": 380,
        "speed": 290,
        "mass": 1.6,
        "size": 16,
        "description": "Master spy\nVenom blasts & acrobatic combat",
        "abilities": [
            Ability("Widow Sting",  0.7,  45, 400, CYAN,   "Electric wrist blast"),
            Ability("Toxic Mine",   3.5,  60, 300, GREEN,  "Poison gas trap"),
            Ability("Acrobat Strike",2.0, 55, 120, RED,    "Spinning kick combo"),
            Ability("Assassination",10.0, 160, 350, SILVER, "Precise lethal strike"),
        ],
        "dodge_rate": 0.32,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🏹 Hawk-Arrow": {
        "color": (100, 30, 150),
        "body_color": (50, 50, 100),
        "hp": 370,
        "speed": 280,
        "mass": 1.6,
        "size": 15,
        "description": "Grandmaster archer\nVariety of trick arrows",
        "abilities": [
            Ability("Sonic Arrow",  1.0,  50, 600, WHITE,  "Stuns with high sound"),
            Ability("Exploding Tip",1.8,  85, 650, ORANGE, "Massive AOE arrow"),
            Ability("Electric Arrow",2.5, 60, 550, YELLOW, "Chain lightning effect"),
            Ability("Barrage",     12.0, 200, 500, PURPLE, "Rain of 20 arrows"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "bow",
        "has_shield": False
    },
    "🌀 Sorcerer-Lord": {
        "color": (200, 50, 30),
        "body_color": (30, 50, 150),
        "hp": 360,
        "speed": 210,
        "mass": 1.7,
        "size": 16,
        "description": "Master of mystic arts\nShields, portals, and spells",
        "abilities": [
            Ability("Mystic Bolt",  0.8,  60, 500, GOLD,   "Arcane energy blast"),
            Ability("Portal Warp",  4.0,  70, 400, ORANGE, "Teleport and strike"),
            Ability("Eldritch Whip",1.5,  55, 250, RED,    "Energy whip pull"),
            Ability("Mirror Realm",14.0, 230, 600, PURPLE, "Bends space for damage"),
        ],
        "dodge_rate": 0.18,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🐜 Size-Shifter": {
        "color": (200, 30, 30),
        "body_color": (40, 40, 40),
        "hp": 410,
        "speed": 260,
        "mass": 1.8,
        "size": 16,
        "description": "Pym particle user\nShrink to dodge, grow to smash",
        "abilities": [
            Ability("Shrink Punch", 0.6,  40, 400, RED,    "Tiny but fast punch"),
            Ability("Ant Swarm",    3.0,  70, 350, BLACK,  "Summons biting ants"),
            Ability("Giant Stomp",  8.0, 150, 300, SILVER, "Grows huge & crushes"),
            Ability("Disk Throw",  10.0, 120, 500, BLUE,   "Enlarges objects to hit"),
        ],
        "dodge_rate": 0.35,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🌪️ Weather-Soul": {
        "color": (255, 255, 255),
        "body_color": (30, 30, 80),
        "hp": 400,
        "speed": 240,
        "mass": 1.5,
        "size": 17,
        "description": "Elemental goddess\nControls wind, rain, & lighting",
        "abilities": [
            Ability("Wind Gust",    0.8,  45, 450, CYAN,   "Pushes enemies away"),
            Ability("Hail Storm",   3.0,  80, 500, WHITE,  "Raining ice chunks"),
            Ability("Thunderbolt",  1.5,  95, 550, YELLOW, "Direct precise strike"),
            Ability("Hurricane",   13.0, 210, 600, BLUE,   "Total screen storm"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🕶️ Optic-Hero": {
        "color": (50, 50, 200),
        "body_color": (200, 180, 50),
        "hp": 420,
        "speed": 220,
        "mass": 2.0,
        "size": 18,
        "description": "Field leader\nContinuous optic concussive beams",
        "abilities": [
            Ability("Optic Blast",  0.5,  40, 700, RED,    "Fast concussive beam"),
            Ability("Wide Beam",    2.5,  90, 500, RED,    "Wide area blast"),
            Ability("Ricochet",     1.8,  65, 600, CRIMSON,"Bouncing beam shot"),
            Ability("Full Power",  12.0, 250, 800, WHITE,  "Destructive mega beam"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🐱 Feral-Claw": {
        "color": (220, 160, 50),
        "body_color": (30, 50, 150),
        "hp": 550,
        "speed": 280,
        "mass": 2.2,
        "size": 17,
        "description": "Mutant with healing factor\nAdamantium claws & berserker rage",
        "abilities": [
            Ability("X-Slash",      0.5,  55, 80,  SILVER, "Fast claw cross-cut"),
            Ability("Lunge",        2.0,  60, 250, BROWN,  "Lunging slash attack"),
            Ability("Regenerate",   7.0,  0,  0,   GREEN,  "Heals significant HP"),
            Ability("Berserker",   14.0, 200, 150, RED,    "Unstoppable claw flurry"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "claws",
        "has_shield": False
    },
    "🃏 Mischief-Loki": {
        "color": (50, 150, 50),
        "body_color": (200, 180, 50),
        "hp": 400,
        "speed": 250,
        "mass": 2.0,
        "size": 17,
        "description": "God of Mischief\nClones, illusions, and daggers",
        "abilities": [
            Ability("Dagger Throw", 0.6,  45, 500, SILVER, "Quick throw daggers"),
            Ability("Illusion",     4.0,  20, 200, GREEN,  "Clones distract enemy"),
            Ability("Scepter Blast",1.8,  75, 450, BLUE,   "Mind stone energy shot"),
            Ability("Trickery",    12.0, 180, 400, PURPLE, "Massive illusion strike"),
        ],
        "dodge_rate": 0.38,
        "weapon_type": "katana",
        "has_shield": False
    },
    "💀 Ghost-Biker": {
        "color": (200, 80, 30),
        "body_color": (20, 20, 20),
        "hp": 500,
        "speed": 260,
        "mass": 2.8,
        "size": 19,
        "description": "Spirit of Vengeance\nHellfire chains & hellcycle",
        "abilities": [
            Ability("Hell-Chain",   0.8,  60, 400, ORANGE, "Flame chain whip"),
            Ability("Penance Gaze", 5.0, 100, 150, RED,    "Stuns and burns"),
            Ability("Hellfire",     2.5,  80, 350, CRIMSON,"AOE fire explosion"),
            Ability("Hell-Cycle",  13.0, 200, 500, ORANGE, "Flaming bike charge"),
        ],
        "dodge_rate": 0.1,
        "weapon_type": "chain",
        "has_shield": False
    },
    "🌳 Forest-Giant": {
        "color": (80, 150, 60),
        "body_color": (120, 90, 50),
        "hp": 650,
        "speed": 170,
        "mass": 4.5,
        "size": 23,
        "description": "Sentient tree warrior\nRegeneration & vine attacks",
        "abilities": [
            Ability("Vine Smash",   1.0,  70, 120, GREEN,  "Lashing vine sweep"),
            Ability("Root Trap",    3.5,  40, 400, BROWN,  "Enemies can't move"),
            Ability("Spore Heal",   8.0,  0,  0,   LIME,   "Healing spores"),
            Ability("Tree Grow",   14.0, 210, 300, GREEN,  "Massive growth smash"),
        ],
        "dodge_rate": 0.04,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🦝 Space-Raccoon": {
        "color": (100, 80, 60),
        "body_color": (50, 100, 200),
        "hp": 340,
        "speed": 270,
        "mass": 1.4,
        "size": 14,
        "description": "Ordnance expert\nHeavy weapons & explosives",
        "abilities": [
            Ability("Blaster",      0.5,  40, 600, ORANGE, "Rapid laser fire"),
            Ability("Sticky Grenade",2.0, 80, 450, RED,    "Delayed explosion"),
            Ability("Machine Gun",  5.0, 120, 550, YELLOW, "Hail of bullets"),
            Ability("The Big One", 14.0, 280, 650, WHITE,  "Massive experimental bomb"),
        ],
        "dodge_rate": 0.3,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🌟 Cosmic-Nova": {
        "color": (255, 255, 100),
        "body_color": (50, 80, 200),
        "hp": 460,
        "speed": 250,
        "mass": 2.5,
        "size": 18,
        "description": "Cosmic powerhouse\nEnergy blasts & flight",
        "abilities": [
            Ability("Photon Blast", 0.7,  65, 550, YELLOW, "Concentrated energy"),
            Ability("Cosmic Dash",  2.5,  75, 350, CYAN,   "High-speed tackle"),
            Ability("Energy Shield",6.0,  10, 100, WHITE,  "Temporary invincibility"),
            Ability("Binary Power",13.0, 250, 500, GOLD,   "Full cosmic release"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "fists",
        "has_shield": True
    },
    "🔱 Trident-Hero": {
        "color": (0, 150, 150),
        "body_color": (200, 150, 50),
        "hp": 520,
        "speed": 230,
        "mass": 3.0,
        "size": 20,
        "description": "King of the deep\nWater control & trident master",
        "abilities": [
            Ability("Trident Stab", 0.8,  65, 100, SILVER, "Quick triple thrust"),
            Ability("Water Wave",   2.5,  70, 400, BLUE,   "Tidal surge push"),
            Ability("Shark Call",   6.0,  90, 450, TEAL,   "Summons a spectral shark"),
            Ability("Ocean Wrath", 12.0, 210, 500, BLUE,   "Massive whirlpool"),
        ],
        "weapon_type": "trident",
        "has_shield": False
    },
    "🦇 Dark-Hero": {
        "color": (20, 20, 20),
        "body_color": (80, 80, 80),
        "hp": 450,
        "speed": 280,
        "mass": 2.2,
        "size": 18,
        "description": "Detective & vigilante\nGadgets and martial arts",
        "abilities": [
            Ability("Batarang",     0.6,  40, 500, SILVER, "Quick throwing weapon"),
            Ability("Smoke Pellets",4.0,  20, 200, (100,100,100), "Confuses enemies"),
            Ability("Grapple Kick", 2.5,  65, 350, BLACK,  "Pull and kick combo"),
            Ability("The Knight",  12.0, 190, 400, DARK_BG,"Perfect combat series"),
        ],
        "dodge_rate": 0.3,
        "weapon_type": "katana",
        "has_shield": False
    },
    "🏃 Sonic-Speed": {
        "color": (220, 30, 30),
        "body_color": (255, 255, 100),
        "hp": 380,
        "speed": 450,
        "mass": 1.5,
        "size": 16,
        "description": "Fastest man alive\nExtreme speed & sonic booms",
        "abilities": [
            Ability("Speed Punch",  0.4,  35, 100, YELLOW, "Ultra-fast punches"),
            Ability("Sonic Boom",   3.0,  70, 300, WHITE,  "Dash creates shockwave"),
            Ability("Lightning Rim",6.0,  85, 400, BLUE,   "Circular speed attack"),
            Ability("Infinite Mass",14.0, 260, 200, GOLD,  "The ultimate punch"),
        ],
        "dodge_rate": 0.4
    },
    "🦅 Wing-Soldier": {
        "color": (200, 30, 30),
        "body_color": (150, 150, 150),
        "hp": 430,
        "speed": 340,
        "mass": 2.0,
        "size": 17,
        "description": "Aerial combatant\nWings & tactical drones",
        "abilities": [
            Ability("Wing Slash",   0.7,  50, 150, SILVER, "Blade-wing strike"),
            Ability("Redwing",      3.0,  55, 500, RED,    "Support drone laser"),
            Ability("Dive Bomb",    4.0,  80, 400, DARK_BG,"Diving tackle"),
            Ability("Air Strike",  11.0, 180, 500, WHITE,  "Full aerial assault"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "katana",
        "has_shield": False
    },
    "🧚 Wasp-Hero": {
        "color": (220, 200, 30),
        "body_color": (30, 30, 30),
        "hp": 350,
        "speed": 360,
        "mass": 1.2,
        "size": 14,
        "description": "Miniature fighter\nBio-stings & rapid flight",
        "abilities": [
            Ability("Bio-Sting",    0.5,  40, 450, YELLOW, "Rapid energy stingers"),
            Ability("Swarm",        3.5,  65, 300, GOLD,   "Dashing multiple hits"),
            Ability("Tiny Fury",    6.0,  80, 200, WHITE,  "Frenzy of small attacks"),
            Ability("Stinger Rain",12.0, 190, 500, YELLOW, "Massive sting barrage"),
        ],
        "dodge_rate": 0.45,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🧱 Rock-Tank": {
        "color": (150, 100, 80),
        "body_color": (100, 80, 60),
        "hp": 700,
        "speed": 180,
        "mass": 4.8,
        "size": 24,
        "description": "Solid stone hero\nIncredible defense & strength",
        "abilities": [
            Ability("Stone Fist",   1.0,  85, 100, BROWN,  "Heavy rock punch"),
            Ability("Clobberin Time",3.5, 100, 150, ORANGE, "Massive impact strike"),
            Ability("Earthquake",   6.0,  70, 350, SILVER, "Stuns nearby enemies"),
            Ability("Boulder Throw",12.0, 220, 600, BROWN,  "Yeets a huge rock"),
        ],
        "dodge_rate": 0.03,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🔥 Fire-Burst": {
        "color": (255, 100, 30),
        "body_color": (255, 230, 50),
        "hp": 400,
        "speed": 280,
        "mass": 1.6,
        "size": 16,
        "description": "Living flame\nFire manipulation & flight",
        "abilities": [
            Ability("Flame On",     1.0,  40, 300, ORANGE, "Passive burn damage"),
            Ability("Fireball",     0.8,  60, 500, RED,    "Projected fire"),
            Ability("Nova Blast",   7.0, 140, 400, GOLD,   "Explosive fire release"),
            Ability("Supernova",   15.0, 300, 600, WHITE,  "Full power explosion"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🧞 Genie-Magic": {
        "color": (80, 180, 255),
        "body_color": (200, 150, 50),
        "hp": 440,
        "speed": 220,
        "mass": 2.0,
        "size": 18,
        "description": "Cosmic genie\nWishes and magic smoke",
        "abilities": [
            Ability("Magic Lamp",   0.9,  60, 450, GOLD,   "Blasts magic smoke"),
            Ability("Giant Hands",  3.0,  80, 200, CYAN,   "Smack from above"),
            Ability("Wish Grant",   8.0,  0,  0,   PINK,   "Random buff/heal"),
            Ability("Phenomenal",  13.0, 210, 500, PURPLE, "Ultimate magic show"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🧟 Plague-Walker": {
        "color": (150, 180, 100),
        "body_color": (80, 100, 60),
        "hp": 500,
        "speed": 150,
        "mass": 2.5,
        "size": 18,
        "description": "Undead plague\nInfects and survives",
        "abilities": [
            Ability("Bite",         0.7,  40, 80,  LIME,   "Infects with poison"),
            Ability("Vomit",        2.5,  55, 300, GREEN,  "Acid splash DOT"),
            Ability("Horde Call",   6.0,  70, 400, BROWN,  "Summons small zombies"),
            Ability("Undead Rage", 12.0, 180, 250, RED,    "Frenzy of bites"),
        ],
        "dodge_rate": 0.05,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🛸 Void-Traveler": {
        "color": (100, 255, 200),
        "body_color": (40, 60, 100),
        "hp": 420,
        "speed": 230,
        "mass": 1.8,
        "size": 17,
        "description": "Alien voyager\nAdvanced tech and beams",
        "abilities": [
            Ability("Ray Gun",      0.6,  45, 550, CYAN,   "Plasma energy shot"),
            Ability("Abduction",    4.0,  60, 300, WHITE,  "Lifts enemy up"),
            Ability("Gravity Bomb", 5.0,  75, 400, PURPLE, "Crushes with gravity"),
            Ability("Mothership",  13.0, 240, 600, LIME,   "Full ship bombardment"),
        ],
        "dodge_rate": 0.18,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🏴‍☠️ Pirate-King": {
        "color": (160, 30, 30),
        "body_color": (50, 40, 40),
        "hp": 480,
        "speed": 240,
        "mass": 2.4,
        "size": 18,
        "description": "King of the seas\nCannons and scimitar",
        "abilities": [
            Ability("Scimitar",     0.7,  50, 90,  SILVER, "Masterful sword cut"),
            Ability("Pistol Shot",  1.5,  65, 500, DARK_BG,"Lead bullet shot"),
            Ability("Cannonade",    5.0,  95, 550, BLACK,  "Fire the ship's big gun"),
            Ability("Kraken",      14.0, 260, 450, BLUE,   "Summons the beast"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "sword",
        "has_shield": False
    },
    "🤺 Shadow-Knight": {
        "color": (60, 60, 70),
        "body_color": (40, 40, 50),
        "hp": 460,
        "speed": 300,
        "mass": 1.9,
        "size": 17,
        "description": "Cursed ronin\nShadow blades & speed",
        "abilities": [
            Ability("Shadow Slash", 0.5,  50, 90,  PURPLE, "Ultra-fast cut"),
            Ability("Dark Dash",    2.5,  60, 350, BLACK,  "Phases through enemy"),
            Ability("Soul Reaper",  6.0,  90, 150, CRIMSON,"Health drain strike"),
            Ability("Nightfall",   12.0, 220, 500, TEAL,   "Total darkness flurry"),
        ],
        "dodge_rate": 0.35,
        "weapon_type": "katana",
        "has_shield": False
    },


}

# ─── FIGHTER CLASS ────────────────────────────────────────────────────────────
class Fighter:
    def __init__(self, char_name, x, y, team, space, particles):
        data = CHARACTER_DATA[char_name]
        self.name       = char_name
        self.team       = team
        self.color      = data["color"]
        self.body_color = data["body_color"]
        self.max_hp     = data["hp"]
        self.hp         = float(data["hp"])
        self.speed      = data["speed"]
        self.size       = data["size"]
        self.particles  = particles
        self.abilities  = [Ability(a.name, a.cooldown, a.damage, a.range,
                                   a.color, a.description) for a in data["abilities"]]
        self.dodge_rate = data.get("dodge_rate", 0.1)
        self.weapon_type = data.get("weapon_type", "fists")
        self.has_shield = data.get("has_shield", False)
        self.is_blocking = False # Can be toggled if needed, but we'll use passive shield for now

        # AI behavior
        self.ai_target: Optional['Fighter'] = None
        self.ai_state = "approach"
        self.ai_timer  = 0.0

        # Hidden Traits system (Rare luck-based buffs)
        train_list = ["RAGE", "ASCENSION", "SECOND WIND", "REBIRTH"]
        self.hidden_trait = random.choice(train_list)
        self.trait_timer = 0.0
        self.trait_triggered = False 
        self.trait_label_timer = 0.0
        self.trait_label_txt = ""

        # Match Stats
        self.kills = 0
        self.damage_dealt = 0.0
        self.damage_taken = 0.0
        self.traits_activated_count = 0

        self.dot_damage = 0.0
        self.dot_timer  = 0.0

        # Physics body
        self.body = pymunk.Body(data["mass"], pymunk.moment_for_circle(data["mass"], 0, data["size"]))
        self.body.position = (x, y)
        self.shape = pymunk.Circle(self.body, data["size"])
        self.shape.elasticity = 0.5
        self.shape.friction   = 0.5
        self.shape.filter     = pymunk.ShapeFilter()  # Collide with everything
        space.add(self.body, self.shape)

        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True
        self.facing = 1  # 1=right, -1=left
        self.state = "idle"  # idle, moving, attacking, stunned
        self.stun_timer = 0.0
        self.invincible_timer = 0.0

        self.level = 1
        self.damage_mult = 1.0
        self.level_up_timer = 0.0
        self.current_ability_idx = 0

        # Visual
        self.hit_flash = 0.0
        self.death_timer = 0.0
        self.combo_count = 0

        self.hazard_hit_count = 0
        self.dot_damage = 0.0
        self.dot_timer  = 0.0

    @property
    def pos(self):
        return (int(self.x), int(self.y))

    def take_damage(self, dmg, knockback_x=0, knockback_y=-200, attacker=None):
        if self.invincible_timer > 0 or not self.alive:
            return 0
        
        # Dodge Mechanic
        if random.random() < self.dodge_rate:
            self.particles.emit(self.x, self.y, WHITE, count=15, speed=300, size=3, life=0.4, gravity=False)
            self.heal(10) # Recover some HP on successful dodge
            return 0
        
        # Shield Block Mechanic
        # If the attacker is in front of the character and they have a shield
        if self.has_shield:
            # We assume a 30% chance to block if hit
            if random.random() < 0.35:
                self.particles.emit(self.x + self.facing*self.size, self.y, SILVER, count=12, speed=100, size=4, gravity=False)
                return 0 # Fully block for now, or could reduce damage

        self.hp = max(0, self.hp - dmg)
        self.damage_taken += dmg
        if attacker: 
            # Apply attacker's level damage multiplier
            dmg *= attacker.damage_mult
            attacker.damage_dealt += dmg

        # Damage Popup & Screenshake
        if hasattr(self, 'battle_ref'):
            is_rage = (self.hidden_trait == "Rage" and self.trait_timer > 0)
            is_big = (dmg > 80 or is_rage)
            color = GOLD if is_big else (WHITE if dmg < 50 else (255, 100, 50))
            
            self.battle_ref.popups.append(DamagePopup(self.x, self.y - 20, f"{int(dmg)}", color, is_crit=is_big))
            
            # Shake based on damage percentage
            shake_amt = (dmg / self.max_hp) * 45
            if shake_amt > 1.0:
                self.battle_ref.shake = min(20.0, self.battle_ref.shake + shake_amt)
            
            # ── JUICY HIT-STOP (Freeze Frame) ──
            if dmg > 60:
                self.battle_ref.hit_stop = 0.06 # 60ms freeze
            if dmg > 150:
                self.battle_ref.hit_stop = 0.12 # 120ms freeze for massive hits
                self.battle_ref.impact_flash = 0.05 # Brief screen flash
            
            self.battle_ref.sounds.play('hit')

        self.hit_flash = 0.25
        self.invincible_timer = 0.12
        # Apply physics knockback
        self.body.velocity = (
            self.body.velocity.x + knockback_x,
            self.body.velocity.y + knockback_y
        )
        self.particles.emit(self.x, self.y, RED, count=10,
                            speed=200, size=5, life=0.5)
        if self.hp <= 0:
            # Check for REBIRTH hidden trait (0.5% per tick? No, 2% once on death)
            if self.hidden_trait == "REBIRTH" and not self.trait_triggered:
                if random.random() < 0.02: # 2% chance to come back to life
                    self.trait_triggered = True
                    self.hp = self.max_hp * 0.35
                    self.alive = True
                    self.trait_label_timer = 2.0
                    self.trait_label_txt = "REBIRTH!"
                    self.particles.emit_ring(self.x, self.y, PINK, count=40, speed=400, size=10)
                    if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
                    return 0 # Neutralize the death blow
            self.die(attacker)
        return dmg

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        self.particles.emit(self.x, self.y, GREEN, count=8,
                            speed=80, size=4, life=0.7, gravity=False)

    def apply_dot(self, dps, duration):
        self.dot_damage = dps
        self.dot_timer  = duration

    def die(self, killer=None):
        if not self.alive: return
        self.alive = False
        if killer:
            killer.kills += 1
            killer.level_up()
        self.death_timer = 1.5
        for _ in range(30):
            self.particles.emit(self.x, self.y, self.color, count=3,
                                speed=random.uniform(100,300),
                                size=random.randint(3,8), life=1.2)

    def level_up(self):
        self.level += 1
        self.damage_mult += 0.15 # 15% more dmg per kill
        self.size *= 1.08 # Visually larger
        self.level_up_timer = 1.5
        self.particles.emit_ring(self.x, self.y, GOLD, count=30, speed=250, size=5)
        if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')

    def update(self, dt, enemies, projectiles):
        if not self.alive:
            return
        # Sync from physics
        self.x = self.body.position.x
        self.y = self.body.position.y
        self.vx = self.body.velocity.x
        self.vy = self.body.velocity.y

        # ── WALL BOUNCE & SUPER JUMP (Anti-Camping) ──
        if hasattr(self, 'battle_ref'):
            r = self.battle_ref.arena_rect
            margin = self.size + 12
            impact = False
            impulse_x, impulse_y = 0.0, 0.0
            
            if self.x < r.left + margin:
                self.body.position = (r.left + margin + 2, self.body.position.y)
                impulse_x = 1200
                impact = True
            elif self.x > r.right - margin:
                self.body.position = (r.right - margin - 2, self.body.position.y)
                impulse_x = -1200
                impact = True
                
            if self.y < r.top + margin:
                self.body.position = (self.body.position.x, r.top + margin + 2)
                impulse_y = 1200
                impact = True
            elif self.y > r.bottom - margin:
                self.body.position = (self.body.position.x, r.bottom - margin - 2)
                impulse_y = -1800 
                impact = True

            if impact:
                self.body.apply_impulse_at_local_point((impulse_x, impulse_y))
                self.particles.emit_ring(self.x, self.y, SILVER, count=12, speed=350, size=6, life=0.5)
                if hasattr(self.battle_ref, 'sounds'): self.battle_ref.sounds.play('thud')
                self.ai_timer = max(self.ai_timer, 0.4)
                self.body.velocity *= 1.3

        # Timers
        self.hit_flash = max(0, self.hit_flash - dt)
        self.invincible_timer = max(0, self.invincible_timer - dt)
        self.stun_timer = max(0, self.stun_timer - dt)
        self.ai_timer  = max(0, self.ai_timer  - dt)
        for ab in self.abilities:
            ab.tick(dt)

        # DOT
        if self.dot_timer > 0:
            self.dot_timer -= dt
            self.take_damage(self.dot_damage * dt)
            if random.random() < 0.1:
                self.particles.emit(self.x, self.y, LIME, count=2, speed=60, size=3, life=0.4)

        if self.stun_timer > 0:
            self.body.velocity *= 0.9
            return

        # AI Targeting Logic
        alive_enemies = [e for e in enemies if e.alive]
        if alive_enemies:
            tp = getattr(self.battle_ref, 'team_priorities', {})
            priority = tp.get(self.team) if hasattr(self, 'battle_ref') else None
            if priority and priority.alive and random.random() < 0.7:
                self.ai_target = priority
            elif self.ai_timer <= 0 or not self.ai_target or not self.ai_target.alive:
                self.ai_target = min(alive_enemies, key=lambda e: math.hypot(e.x-self.x, e.y-self.y))
            
            self._run_ai(dt, projectiles)

        # Air friction
        self.body.velocity *= 0.92
        # ── HIDDEN TRAITS TRIGER LOGIC (Luck-based excitement) ──
        self.trait_label_timer = max(0, self.trait_label_timer - dt)
        self.trait_timer = max(0, self.trait_timer - dt)

        # Trigger logic: Roll a dice every few decision ticks (~once every 0.2s)
        if self.ai_timer <= 0:
            luck = random.random()
            
            # 1. RAGE (1.5% chance) -> Massive Damage
            if self.hidden_trait == "RAGE" and luck < 0.015 and self.trait_timer <= 0:
                self.trait_timer = 5.0 # Lasts 5 seconds
                self.trait_label_timer = 2.0
                self.trait_label_txt = "HIDDEN: RAGE!!"
                self.traits_activated_count += 1
                self.particles.emit_ring(self.x, self.y, RED, count=24, speed=300)
                if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            
            # 2. ASCENSION (0.8% chance) -> Fly and Heal
            elif self.hidden_trait == "ASCENSION" and luck < 0.008 and self.trait_timer <= 0:
                self.trait_timer = 4.0
                self.trait_label_timer = 2.0
                self.trait_label_txt = "HIDDEN: ASCENSION!"
                self.traits_activated_count += 1
                self.particles.emit_ring(self.x, self.y, CYAN, count=24, speed=200)
                if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('heal')

            # 3. SECOND WIND (1% chance when low HP) -> Heal back to 50%
            elif self.hidden_trait == "SECOND WIND" and self.hp < self.max_hp * 0.15 and not self.trait_triggered:
                if luck < 0.05: # 5% per tick when low = ~1% cumulative
                    self.trait_triggered = True # Only once
                    self.heal(self.max_hp * 0.5)
                    self.trait_label_timer = 2.0
                    self.trait_label_txt = "SECOND WIND!"
                    self.traits_activated_count += 1
                    self.particles.emit_ring(self.x, self.y, GREEN, count=24)
                    if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('heal')

        # Trait Active Effects
        if self.trait_timer > 0:
            if self.hidden_trait == "ASCENSION":
                self.body.apply_impulse_at_local_point((0, -250)) # Anti-gravity float
                self.heal(30 * dt) # Rapid repair
                if random.random() < 0.3:
                    self.particles.emit(self.x, self.y + 20, CYAN, count=2, speed=40, gravity=True)
            elif self.hidden_trait == "RAGE":
                # Particles glow
                if random.random() < 0.3:
                    self.particles.emit(self.x, self.y, RED, count=2, speed=100, gravity=False)

        # Recovery
        if self.hp < self.max_hp * 0.5:
            self.heal(5 * dt)
            if random.random() < 0.2:
                self.particles.emit(self.x, self.y, GREEN, count=1, gravity=False)

    def _run_ai(self, dt, projectiles):
        t = self.ai_target
        dx, dy = t.x - self.x, t.y - self.y
        dist  = max(1, math.hypot(dx, dy))
        ndx, ndy = dx/dist, dy/dist
        self.facing = 1 if dx > 0 else -1

        low_hp = self.hp < self.max_hp * 0.5
        has_ranged = any(ab.range > 220 for ab in self.abilities)

        # ── ABILITY SELECTION ──
        best_ab = None
        ready_abs = [ab for ab in self.abilities if ab.ready()]
        
        # Priority 1: Instant Heals
        heals = [ab for ab in ready_abs if ab.damage == 0]
        if heals and self.hp < self.max_hp * 0.7:
            best_ab = heals[0]

        # Priority 2: Ranged Strategy (Stay back if low HP)
        if not best_ab:
            ranged_abs = [ab for ab in ready_abs if ab.range > 220 and dist <= ab.range]
            if ranged_abs:
                # If low health, we ONLY want to use ranged if we have it
                best_ab = max(ranged_abs, key=lambda a: a.damage)
            elif not low_hp:
                # If healthy, we can use closer moves
                in_range = [ab for ab in ready_abs if dist <= ab.range]
                if in_range: best_ab = max(in_range, key=lambda a: a.damage)
            else:
                # Low health but NO ranged ready? Maybe use a quick melee if extremely close
                if dist < 100:
                    melee = [ab for ab in ready_abs if dist <= ab.range]
                    if melee: best_ab = max(melee, key=lambda a: a.damage)

        if self.ai_timer <= 0:
            self.ai_timer = random.uniform(0.3, 0.6)
            if best_ab:
                self._use_ability(best_ab, t, projectiles)
                best_ab.use()
            else:
                # Movement strategy: "Tactical Positioning"
                if low_hp and has_ranged:
                    # Low HP Ranged characters should BACK AWAY
                    self.ai_state = "strafe"
                elif dist > 350:
                    self.ai_state = "approach"
                elif dist < 120:
                    self.ai_state = random.choice(["strafe", "jump_over"])
                else:
                    self.ai_state = random.choice(["approach", "strafe", "jump_over"])

        # ── DYNAMIC DODGING / DASHING ──
        dodge_chance = 0.08
        if low_hp:
            dodge_chance *= 3.0 # Significantly higher dodge chance when hurt
        
        # If in jump_over or randomly dodging
        if (self.ai_state == "jump_over" or random.random() < dodge_chance) and dist < 450:
            side = random.choice([1, -1])
            # Dodge impulse
            angle_off = random.uniform(math.pi/3, math.pi/2) * side
            dash_vel = pygame.Vector2(ndx, ndy).rotate_rad(angle_off) * self.speed * 5.0
            self.body.apply_impulse_at_local_point((dash_vel.x, dash_vel.y))
            self.particles.emit_ring(self.x, self.y, WHITE, count=15, speed=200, life=0.3)
            self.ai_timer = 0.4 
            if low_hp: self.ai_state = "strafe" # Run away after dodging if hurt

        # ── MOVEMENT ──
        move_vec = pygame.Vector2(0, 0)
        if self.ai_state == "approach":
            move_vec = pygame.Vector2(ndx, ndy)
        elif self.ai_state == "strafe":
            # Perpendicular movement
            move_vec = pygame.Vector2(-ndy, ndx).rotate_rad(random.uniform(-0.2, 0.2))
            # Escape logic
            if low_hp and has_ranged: 
                move_vec += pygame.Vector2(-ndx, -ndy) * 0.85
            else:
                move_vec += pygame.Vector2(ndx, ndy) * (0.3 if low_hp else 0.7)

        # ── ANTI-CAMPING STEERING ──
        # Don't let yourself get pinned to a wall
        arena = self.battle_ref.arena_rect
        if self.x < arena.left + 140: move_vec.x = max(move_vec.x, 0.6)
        if self.x > arena.right - 140: move_vec.x = min(move_vec.x, -0.6)
        if self.y < arena.top + 140: move_vec.y = max(move_vec.y, 0.6)
        if self.y > arena.bottom - 140: move_vec.y = min(move_vec.y, -0.6)

        if move_vec.length() > 0:
            move_vec = move_vec.normalize() * self.speed
            self.body.velocity += (move_vec - self.body.velocity) * 0.25

        # Final safety: don't get stuck far away unless kiting
        if dist > 900 and not (low_hp and has_ranged):
            self.ai_state = "approach"


    def _use_ability(self, ab, target, projectiles):
        dx = target.x - self.x
        dy = target.y - self.y
        dist = max(1, math.hypot(dx, dy))
        ndx, ndy = dx/dist, dy/dist

        name = ab.name

        # ── WARRIOR ──
        if name == "Sword Slash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            for i in range(10):
                angle = math.atan2(ndy, ndx) + (i-5)*0.2
                self.particles.emit(self.x + math.cos(angle)*40, self.y + math.sin(angle)*40, GOLD, count=2)
            if dist < ab.range:
                # Apply Rage damage boost (2x)
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0:
                    dmg *= 2.0
                target.take_damage(dmg, knockback_x=ndx*400, knockback_y=ndy*400, attacker=self)

        elif name == "Shield Bash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            for i in range(-20, 21, 10):
                self.particles.emit(self.x + ndx*25 + (-ndy*i), self.y + ndy*25 + (ndx*i), SILVER, count=5, speed=50)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*700, knockback_y=ndy*700, attacker=self)
                target.stun_timer = 1.0

        elif name == "War Cry":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, ORANGE, count=24, size=6)

        elif name == "Berserker":
            for i in range(3):
                self.particles.emit_ring(self.x, self.y, CRIMSON, count=15, speed=100+i*100, size=8)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*500, knockback_y=-400, attacker=self)

        # ── MAGE ──
        elif name == "Fireball":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*400, ndy*400-50,
                          dmg, ORANGE, 10, self.team, RED, aoe_radius=50)
            projectiles.append(p)
            self.particles.emit(self.x, self.y, ORANGE, count=6, speed=100)

        elif name == "Ice Shard":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*520, ndy*520,
                          dmg, CYAN, 7, self.team, (150,220,255), piercing=True)
            projectiles.append(p)

        elif name == "Lightning":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y,
                                    YELLOW, count=20, size=4, life=0.25)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, knockback_x=ndx*150, attacker=self)
                target.stun_timer = 0.3

        elif name == "Meteor":
            for _ in range(5):
                ox = target.x + random.uniform(-80, 80)
                p = Projectile(ox, -50, 0, 600, ab.damage//5,
                              RED, 12, self.team, ORANGE)
                p.gravity_affected = False
                projectiles.append(p)
            self.particles.emit_ring(target.x, target.y, RED, count=30, speed=250, size=8)

        # ── NINJA ──
        elif name == "Shuriken":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for i in range(3):
                angle = math.atan2(ndy, ndx) + (i-1)*0.15
                p = Projectile(self.x, self.y,
                              math.cos(angle)*500, math.sin(angle)*500,
                              dmg, SILVER, 5, self.team)
                projectiles.append(p)

        elif name == "Shadow Step":
            self.body.position = (target.x - self.facing*60, target.y)
            self.particles.emit(target.x, target.y, PURPLE, count=20, speed=150)
            target.take_damage(ab.damage, knockback_x=self.facing*400, knockback_y=-300, attacker=self)

        elif name == "Smoke Bomb":
            self.particles.emit(self.x, self.y, (80,80,80), count=30,
                               speed=120, size=8, life=1.0, gravity=False)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.stun_timer = 1.0

        elif name == "Death Mark":
            self.particles.emit_beam(self.x, self.y, target.x, target.y,
                                    CRIMSON, count=15, life=0.4)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*200, knockback_y=-500, attacker=self)

        # ── DRAGON ──
        elif name == "Fire Breath":
            for i in range(20):
                angle = math.atan2(ndy, ndx) + random.uniform(-0.4, 0.4)
                dist_frac = random.uniform(0.2, 1.0)
                px = self.x + math.cos(angle) * ab.range * dist_frac
                py = self.y + math.sin(angle) * ab.range * dist_frac
                self.particles.emit(px, py, ORANGE, count=2, speed=50)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*100, attacker=self)
                target.apply_dot(20, 2.0)

        elif name == "Tail Whip":
            for i in range(12):
                angle = math.atan2(ndy, ndx) + math.pi + (i-6)*0.3
                v_x = math.cos(angle) * 85
                v_y = math.sin(angle) * 85
                self.particles.emit(self.x + v_x, self.y + v_y, BROWN, count=3, speed=100, size=6, life=0.5)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=-ndx*500, attacker=self)

        elif name == "Wing Slam":
            self.particles.emit_ring(self.x, self.y, RED, count=15, speed=100, size=8)
            self.particles.emit_ring(self.x, self.y, ORANGE, count=15, speed=250, size=6)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*300, knockback_y=-400, attacker=self)

        elif name == "Dragon Rage":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(8):
                angle = random.uniform(0, math.pi*2)
                p = Projectile(self.x, self.y,
                              math.cos(angle)*350, math.sin(angle)*350,
                              ab.damage//8, ORANGE, 8, self.team, RED, aoe_radius=30)
                projectiles.append(p)

        # ── DEMON ──
        elif name == "Dark Claw":
            for i in range(5):
                off = (i-2)*10
                self.particles.emit(self.x + ndx*50 + (-ndy*off), self.y + ndy*50 + (ndx*off), CRIMSON, count=5, speed=150)
            if dist < ab.range:
                stolen = target.take_damage(ab.damage, knockback_x=ndx*250, attacker=self)
                self.heal(stolen * 0.3)

        elif name == "Hell Spike":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*380, ndy*380,
                          ab.damage, (150,0,50), 9, self.team,
                          CRIMSON, homing=True)
            projectiles.append(p)

        elif name == "Soul Drain":
            self.particles.emit_beam(self.x, self.y, target.x, target.y,
                                    PURPLE, count=20, life=0.5)
            if dist < ab.range:
                stolen = target.take_damage(ab.damage, attacker=self)
                self.heal(stolen * 0.8)

        elif name == "Hellfire":
            for _ in range(6):
                px = target.x + random.uniform(-120, 120)
                p = Projectile(px, -30, 0, 500, ab.damage//6,
                              RED, 10, self.team, ORANGE)
                p.gravity_affected = False
                projectiles.append(p)

        # ── ROBOT ──
        elif name == "Laser Beam":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y,
                                    CYAN, count=15, size=3, life=0.2)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*80, attacker=self)

        elif name == "Missile":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*300, ndy*300-100,
                          ab.damage, ORANGE, 9, self.team, RED,
                          homing=True, aoe_radius=60)
            projectiles.append(p)

        elif name == "EMP Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_trap(target.x, target.y, BLUE, size=100)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.stun_timer = 1.5

        elif name == "Overdrive":
            for i in range(6):
                angle = math.atan2(ndy, ndx) + random.uniform(-0.2, 0.2)
                p = Projectile(self.x, self.y,
                              math.cos(angle)*600, math.sin(angle)*600,
                              ab.damage//6, CYAN, 5, self.team)
                projectiles.append(p)

        # ── ELEMENTAL ──
        elif name == "Gust":
            self.particles.emit(self.x + ndx*100, self.y + ndy*100,
                               CYAN, count=20, speed=250, size=5,
                               direction=math.atan2(ndy, ndx))
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*500, knockback_y=-200, attacker=self)

        elif name == "Tornado":
            self.particles.emit_ring(target.x, target.y, TEAL, count=20, speed=180)
            for _ in range(10):
                self.particles.emit(target.x + random.uniform(-40,40),
                                   target.y + random.uniform(-40,40),
                                   CYAN, count=2, speed=100)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*200, knockback_y=-600, attacker=self)

        elif name == "Thunderbolt":
            for i in range(8):
                py = target.y - i*40
                self.particles.emit(target.x + random.uniform(-10,10), py,
                                   YELLOW, count=3, speed=100, gravity=False)
            if dist < ab.range:
                target.take_damage(ab.damage, knockback_x=ndx*100, knockback_y=-300, attacker=self)
                target.stun_timer = 0.5
                if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')

        elif name == "Storm":
            for _ in range(15):
                px = random.uniform(50, WIDTH-50)
                p = Projectile(px, -20, 0, 450, ab.damage//15,
                              YELLOW, 6, self.team, CYAN)
                p.gravity_affected = False
                projectiles.append(p)

        # ── VAMPIRE ──
        elif name == "Blood Drain":
            self.particles.emit_beam(self.x, self.y, target.x, target.y,
                                    CRIMSON, count=12, life=0.4)
            if dist < ab.range:
                stolen = target.take_damage(ab.damage, attacker=self)
                self.heal(stolen * 0.6)

        elif name == "Bat Swarm":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for _ in range(5):
                angle = math.atan2(ndy, ndx) + random.uniform(-0.5, 0.5)
                p = Projectile(self.x, self.y,
                              math.cos(angle)*300, math.sin(angle)*300,
                              dmg//5, PURPLE, 6, self.team)
                projectiles.append(p)

        elif name == "Mist Form":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.invincible_timer = 2.0
            self.particles.emit(self.x, self.y, (150,150,200),
                               count=30, speed=60, size=5, life=1.5, gravity=False)

        elif name == "Drain Life":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, PINK, count=20, speed=200)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                stolen = target.take_damage(dmg, knockback_x=ndx*100, attacker=self)
                self.heal(stolen * 0.9)

        # ── ARCHER ──
        elif name == "Arrow Shot":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*650, ndy*650,
                          dmg, GOLD, 6, self.team, SILVER)
            projectiles.append(p)

        elif name == "Multi-Shot":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for i in range(5):
                angle = math.atan2(ndy, ndx) + (i-2)*0.1
                p = Projectile(self.x, self.y,
                              math.cos(angle)*550, math.sin(angle)*550,
                              dmg, GREEN, 4, self.team, LIME)
                projectiles.append(p)

        elif name == "Poison Arrow":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*500, ndy*500,
                          dmg, (100,200,50), 6, self.team, LIME)
            projectiles.append(p)

        elif name == "Rain of Arrows":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for _ in range(12):
                px = target.x + random.uniform(-100, 100)
                p = Projectile(px, -30, random.uniform(-30,30), 500,
                              dmg//12, ORANGE, 5, self.team, LIME)
                p.gravity_affected = True
                projectiles.append(p)

        # ── POSEIDON ──
        elif name == "Trident":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for i in range(3):
                angle = math.atan2(ndy, ndx) + (i-1)*0.15
                p = Projectile(self.x, self.y,
                              math.cos(angle)*450, math.sin(angle)*450,
                              dmg//3, BLUE, 7, self.team, CYAN)
                projectiles.append(p)
            self.particles.emit(self.x, self.y, CYAN, count=10, speed=150)

        elif name == "Water Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*500, ndy*500,
                          dmg, CYAN, 10, self.team, BLUE)
            projectiles.append(p)
            self.particles.emit(self.x, self.y, BLUE, count=8, speed=120)

        # ── WEB-SLINGER ──
        elif name == "Web Shot":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*500, ndy*500,
                          dmg, WHITE, 8, self.team, SILVER)
            projectiles.append(p)
            if dist < ab.range: 
                target.stun_timer = 1.0
                self.particles.emit_trap(target.x, target.y, WHITE, size=80)

        elif name == "Web Swing":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Show a web line particle effect
            for i in range(15):
                self.particles.emit(self.x + ndx*i*20, self.y + ndy*i*20 - i*10, WHITE, count=2, speed=20, size=3, gravity=False)
            self.body.velocity = (ndx*800, ndy*800 - 200)
            if dist < 100:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*400, -200, attacker=self)

        elif name == "Spider-Sense":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.invincible_timer = 1.0
            self.body.velocity = (-ndx*600, -300)
            self.particles.emit_ring(self.x, self.y, RED, count=20, speed=150, size=5)

        elif name == "Web Barrage":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for _ in range(12):
                ang = math.atan2(ndy, ndx) + random.uniform(-0.5, 0.5)
                p = Projectile(self.x, self.y, math.cos(ang)*600, math.sin(ang)*600,
                              dmg//12, WHITE, 6, self.team, SILVER)
                projectiles.append(p)

        # ── TECH-ARMOR ──
        elif name == "Repulsor":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, CYAN, count=20, size=5)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*400, attacker=self)

        elif name == "Mini-Missile":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*200, ndy*200-150,
                          dmg, ORANGE, 8, self.team, RED, homing=True, aoe_radius=40)
            projectiles.append(p)

        elif name == "Uni-Beam":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Solid energy beam
            for i in range(25):
                 self.particles.emit(self.x + ndx*i*20, self.y + ndy*i*20, WHITE, count=5, speed=100, size=8, life=0.4, gravity=False)
            self.particles.emit_beam(self.x, self.y, self.x + ndx*ab.range, self.y + ndy*ab.range,
                                    WHITE, count=40, size=12, life=0.6)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*600, -100, attacker=self)

        elif name == "Rocket Barrage":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for _ in range(10):
                p = Projectile(self.x, self.y, random.uniform(-300,300), -400-random.uniform(0,200),
                               dmg//10, RED, 7, self.team, ORANGE, homing=True)
                projectiles.append(p)

        # ── GAMMA-GIANT ──
        elif name == "Smash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            for r in range(1, 5):
                self.particles.emit_ring(self.x + ndx*50, self.y + ndy*50, GREEN, count=20, speed=80*r, size=10)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*800, -500, attacker=self)

        elif name == "Gamma Leap":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.body.velocity = (ndx*400, -800)
            self.particles.emit_ring(self.x, self.y, GREEN, count=20, speed=100)

        elif name == "Thunderclap":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Shockwave with lines
            for i in range(12):
                ang = i * (math.pi*2/12)
                self.particles.emit_beam(self.x, self.y, self.x + math.cos(ang)*200, self.y + math.sin(ang)*200, WHITE, count=5)
            self.particles.emit_ring(self.x, self.y, WHITE, count=40, speed=400, size=8)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*600, attacker=self)
                target.stun_timer = 1.5

        elif name == "Hulk Rage":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for i in range(8):
                self.particles.emit_ring(self.x, self.y, RED, count=15, speed=150+i*70, size=12-i)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*1000, -700, attacker=self)

        # ── THUNDER-GOD ──
        elif name == "Hammer Throw":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*700, ndy*700,
                          dmg, SILVER, 12, self.team, CYAN, piercing=True)
            projectiles.append(p)

        elif name == "Lightning":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Jagged lightning effect
            last_p = (target.x, -200)
            for i in range(6):
                next_p = (target.x + random.uniform(-30,30), -200 + i*100)
                self.particles.emit_beam(last_p[0], last_p[1], next_p[0], next_p[1], YELLOW, count=10, size=5)
                last_p = next_p
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            target.take_damage(dmg, 0, 100, attacker=self)
            target.stun_timer = 0.5

        elif name == "Shockwave":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, CYAN, count=30, speed=300, size=8)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*600, -300, attacker=self)

        elif name == "God Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, WHITE, count=60, speed=500, life=1.2)
            for _ in range(15):
                px = target.x + random.uniform(-150,150)
                self.particles.emit_beam(px, -200, px, target.y+50, YELLOW, count=8)
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            target.take_damage(dmg, attacker=self)

        # ── STAR-SOLDIER ──
        elif name == "Shield Toss":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*500, ndy*500,
                          dmg, SILVER, 10, self.team, BLUE, piercing=True)
            projectiles.append(p)

        elif name == "Combat Combo":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            self.particles.emit(target.x, target.y, BLUE, count=15, speed=200)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*200, attacker=self)

        elif name == "Shield Charge":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Charging trail
            for i in range(10):
                self.particles.emit(self.x - ndx*i*10, self.y, SILVER, count=2)
            self.body.velocity = (ndx*1000, 0)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*900, -150, attacker=self)

        elif name == "Final Stand":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Circular shield burst
            for r in range(1, 4):
                self.particles.emit_ring(self.x, self.y, BLUE, count=20, speed=100*r, size=10)
                self.particles.emit_ring(self.x, self.y, SILVER, count=15, speed=120*r, size=6)
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            for _ in range(8):
                target.take_damage(dmg//8, ndx*150, attacker=self)
                self.particles.emit(target.x, target.y, RED, count=10)

        # ── JUNGLE-KING ──
        elif name == "Claw Slash":
            # Triple slash lines
            for i in range(3):
                off = (i-1)*15
                self.particles.emit_beam(self.x + ndx*20, self.y+off-20, self.x + ndx*60, self.y+off+20, PURPLE, count=5)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*250, attacker=self)

        elif name == "Pounce":
            self.body.velocity = (ndx*850, -450)
            self.particles.emit(self.x, self.y, PURPLE, count=10)
            if dist < 120:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*400, attacker=self)

        elif name == "Kinetic Burst":
            self.particles.emit_ring(self.x, self.y, PINK, count=40, speed=350, size=10)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*700, -300, attacker=self)

        elif name == "Panther Hunt":
            # Invisibility puff then strike
            self.particles.emit(self.x, self.y, PURPLE, count=20, life=0.5)
            self.body.position = (target.x - self.facing*50, target.y)
            self.particles.emit(target.x, target.y, BLACK, count=15, speed=250)
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            target.take_damage(dmg, ndx*500, attacker=self)

        # ── TOXIC-WIDOW ──
        elif name == "Widow Sting":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, CYAN, count=12, size=3)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, attacker=self)
                target.stun_timer = 0.8

        elif name == "Toxic Mine":
            # Cloud of gas
            for _ in range(30):
                self.particles.emit(self.x + ndx*60 + random.uniform(-40,40), self.y + random.uniform(-40,40), 
                                   GREEN, count=1, speed=20, size=8, life=1.5, gravity=False)
            if dist < ab.range: target.apply_dot(25, 4.0)

        elif name == "Acrobat Strike":
            self.body.velocity = (ndx*500, -400)
            self.particles.emit(self.x, self.y, CYAN, count=10)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, ndx*400, -400, attacker=self)

        elif name == "Assassination":
            # Critical strike 'X' lines
            self.particles.emit_beam(target.x-30, target.y-30, target.x+30, target.y+30, RED, count=10)
            self.particles.emit_beam(target.x+30, target.y-30, target.x-30, target.y+30, RED, count=10)
            if dist < ab.range:
                dmg = ab.damage
                if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
                target.take_damage(dmg, 0, -600, attacker=self)

        # ── HAWK-ARROW ──
        elif name == "Sonic Arrow":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*600, ndy*600, dmg, WHITE, 6, self.team)
            projectiles.append(p)
            if dist < ab.range: target.stun_timer = 1.0

        elif name == "Exploding Tip":
            dmg = ab.damage
            if self.hidden_trait == "RAGE" and self.trait_timer > 0: dmg *= 2.0
            p = Projectile(self.x, self.y, ndx*500, ndy*500, dmg, ORANGE, 8, self.team, RED, aoe_radius=80)
            projectiles.append(p)

        elif name == "Electric Arrow":
            p = Projectile(self.x, self.y, ndx*550, ndy*550, ab.damage, YELLOW, 6, self.team, CYAN, piercing=True)
            projectiles.append(p)

        elif name == "Barrage":
            for _ in range(15):
                angle = math.atan2(ndy, ndx) + random.uniform(-0.2, 0.2)
                p = Projectile(self.x, self.y, math.cos(angle)*700, math.sin(angle)*700, ab.damage//15, PURPLE, 4, self.team)
                projectiles.append(p)

        # ── SORCERER-LORD ──
        elif name == "Mystic Bolt":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*450, ndy*450, ab.damage, GOLD, 10, self.team, ORANGE)
            projectiles.append(p)

        elif name == "Portal Warp":
            # Dual portal rings
            self.particles.emit_ring(self.x, self.y, ORANGE, count=20, speed=100)
            self.body.position = (target.x + random.uniform(-100,100), target.y - 150)
            self.particles.emit_ring(self.x, self.y, BLUE, count=20, speed=100)
            target.take_damage(ab.damage, attacker=self)

        elif name == "Eldritch Whip":
            # Glowing whip line
            for i in range(12):
                self.particles.emit(self.x + ndx*i*20, self.y + ndy*i*20, RED, count=3, speed=50, size=5)
            target.body.velocity = (-ndx*600, -200)
            target.take_damage(ab.damage, attacker=self)

        elif name == "Mirror Realm":
            # Glass shatter effect
            self.particles.emit_ring(target.x, target.y, PURPLE, count=50, speed=300, size=10)
            for _ in range(20):
                self.particles.emit(target.x + random.uniform(-50,50), target.y + random.uniform(-50,50), 
                                   WHITE, count=1, speed=150, size=4, life=0.8)
            target.take_damage(ab.damage, attacker=self)
            target.stun_timer = 2.0

        # ── SIZE-SHIFTER ──
        elif name == "Shrink Punch":
            self.particles.emit(target.x, target.y, RED, count=15, speed=250)
            if dist < ab.range: target.take_damage(ab.damage, ndx*150, attacker=self)

        elif name == "Ant Swarm":
            # Swarm of black dots moving towards target
            for _ in range(20):
                self.particles.emit(self.x + random.uniform(-30,30), self.y + random.uniform(-30,30), 
                                   BLACK, count=2, speed=100, size=3)
            target.apply_dot(20, 5.0)

        elif name == "Giant Stomp":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            for r in range(1, 6):
                self.particles.emit_ring(self.x, self.y, SILVER, count=25, speed=100*r, size=18-r*2)
            if dist < ab.range: target.take_damage(ab.damage, ndx*600, -700, attacker=self)

        elif name == "Disk Throw":
            p = Projectile(self.x, self.y, ndx*400, ndy*400, ab.damage, BLUE, 20, self.team, WHITE)
            projectiles.append(p)

        # ── WEATHER-SOUL ──
        elif name == "Wind Gust":
            self.particles.emit(self.x + ndx*150, self.y, CYAN, count=30, speed=400, size=6)
            if dist < ab.range: target.take_damage(ab.damage, ndx*700, -300, attacker=self)

        elif name == "Hail Storm":
            for _ in range(10):
                px = target.x + random.uniform(-80,80)
                p = Projectile(px, -30, 0, 600, ab.damage//10, WHITE, 9, self.team, CYAN)
                projectiles.append(p)

        elif name == "Thunderbolt":
            self.particles.emit_beam(target.x, -200, target.x, target.y, YELLOW, count=30, size=8)
            self.particles.emit_ring(target.x, target.y, WHITE, count=15)
            target.take_damage(ab.damage, 0, 300, attacker=self)

        elif name == "Hurricane":
            # Massive swirling cyclone
            for i in range(5):
                self.particles.emit_ring(self.x, self.y, BLUE, count=20, speed=150+i*80, life=1.5, size=10)
            target.take_damage(ab.damage, attacker=self)

        # ── OPTIC-HERO ──
        elif name == "Optic Blast":
            self.particles.emit_beam(self.x, self.y, self.x+ndx*ab.range, self.y+ndy*ab.range, RED, count=25, size=6)
            if dist < ab.range: target.take_damage(ab.damage, ndx*500, attacker=self)

        elif name == "Wide Beam":
            for i in range(7):
                ang = math.atan2(ndy, ndx) + (i-3)*0.12
                self.particles.emit_beam(self.x, self.y, self.x+math.cos(ang)*ab.range, self.y+math.sin(ang)*ab.range, RED, count=12)
            if dist < ab.range: target.take_damage(ab.damage, ndx*700, attacker=self)

        elif name == "Ricochet":
            p = Projectile(self.x, self.y, ndx*600, ndy*600, ab.damage, CRIMSON, 6, self.team, RED, piercing=True)
            projectiles.append(p)

        elif name == "Full Power":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            # Giant beam particles
            for i in range(40):
                 self.particles.emit(self.x + ndx*i*25, self.y + ndy*i*25, WHITE, count=8, speed=150, size=15, life=0.6, gravity=False)
            self.particles.emit_beam(self.x, self.y, self.x+ndx*WIDTH, self.y, WHITE, count=150, size=30, life=1.0)
            target.take_damage(ab.damage, ndx*1200, attacker=self)

        # ── FERAL-CLAW ──
        elif name == "X-Slash":
            self.particles.emit_beam(target.x-40, target.y-40, target.x+40, target.y+40, SILVER, count=15)
            self.particles.emit_beam(target.x+40, target.y-40, target.x-40, target.y+40, SILVER, count=15)
            if dist < ab.range: target.take_damage(ab.damage, ndx*300, attacker=self)

        elif name == "Lunge":
            self.body.velocity = (ndx*950, -250)
            self.particles.emit(self.x, self.y, SILVER, count=12)
            if dist < 120: target.take_damage(ab.damage, ndx*500, attacker=self)

        elif name == "Regenerate":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('heal')
            self.heal(150)
            self.particles.emit_ring(self.x, self.y, GREEN, count=20, speed=100)

        elif name == "Berserker":
            self.stun_timer = 0
            self.speed *= 1.6
            self.particles.emit_ring(self.x, self.y, CRIMSON, count=30, speed=200)
            for _ in range(6):
                target.take_damage(ab.damage//6, ndx*150, attacker=self)

        # ── MISCHIEF-LOKI ──
        elif name == "Dagger Throw":
            for i in range(2):
                p = Projectile(self.x, self.y, ndx*500, ndy*500+random.uniform(-40,40), ab.damage//2, SILVER, 5, self.team)
                projectiles.append(p)

        # ── MISCHIEF-LOKI ──
        elif name == "Dagger Throw":
            for i in range(2):
                p = Projectile(self.x, self.y, ndx*500, ndy*500+random.uniform(-40,40), ab.damage//2, SILVER, 5, self.team)
                projectiles.append(p)

        elif name == "Illusion":
            # Multiple poof rings
            for i in range(5):
                self.particles.emit_ring(self.x + random.uniform(-150,150), self.y + random.uniform(-50,50), GREEN, count=12, speed=80)

        elif name == "Scepter Blast":
            p = Projectile(self.x, self.y, ndx*450, ndy*450, ab.damage, BLUE, 10, self.team, GOLD)
            projectiles.append(p)

        elif name == "Trickery":
            # Poof then swap
            self.particles.emit(self.x, self.y, GREEN, count=25, life=0.6)
            self.body.position = (target.x + random.uniform(-100,100), target.y)
            self.particles.emit(self.x, self.y, GREEN, count=25, life=0.6)
            target.take_damage(ab.damage, attacker=self)
            target.stun_timer = 1.2

        # ── GHOST-BIKER ──
        elif name == "Hell-Chain":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, ORANGE, count=20)
            target.take_damage(ab.damage, -ndx*400, attacker=self)

        elif name == "Penance Gaze":
            self.particles.emit(target.x, target.y, RED, count=30, speed=200, gravity=False)
            target.take_damage(ab.damage, attacker=self)
            target.stun_timer = 1.5

        elif name == "Hellfire":
            self.particles.emit_ring(self.x, self.y, CRIMSON, count=30, speed=300)
            if dist < ab.range: target.take_damage(ab.damage, attacker=self)

        elif name == "Hell-Cycle":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.body.velocity = (ndx*1200, 0)
            self.particles.emit(self.x, self.y, ORANGE, count=20, speed=150)
            if dist < 150: target.take_damage(ab.damage, ndx*800, -200, attacker=self)

        # ── FOREST-GIANT ──
        elif name == "Vine Smash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            # Lashing vine animation
            for i in range(1, 10):
                self.particles.emit(self.x + ndx*i*15, self.y + ndy*i*15, GREEN, count=4, speed=50, size=5)
            if dist < ab.range: target.take_damage(ab.damage, ndx*400, -200, attacker=self)

        elif name == "Root Trap":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_trap(target.x, target.y, BROWN, size=90)
            target.stun_timer = 2.0

        elif name == "Spore Heal":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('heal')
            self.heal(80)
            self.particles.emit(self.x, self.y, LIME, count=15, gravity=False)

        elif name == "Tree Grow":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            self.particles.emit_ring(self.x, self.y, GREEN, count=40, speed=300, size=12)
            if dist < ab.range: target.take_damage(ab.damage, ndx*600, -500, attacker=self)

        # ── SPACE-RACCOON ──
        elif name == "Blaster":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*600, ndy*600, ab.damage, ORANGE, 5, self.team, YELLOW)
            projectiles.append(p)

        elif name == "Sticky Grenade":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*400, -200, ab.damage, RED, 10, self.team, BLACK, aoe_radius=100)
            projectiles.append(p)

        elif name == "Machine Gun":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            for _ in range(8):
                ang = math.atan2(ndy, ndx) + random.uniform(-0.1,0.1)
                p = Projectile(self.x, self.y, math.cos(ang)*800, math.sin(ang)*800, ab.damage//8, YELLOW, 3, self.team)
                projectiles.append(p)

        elif name == "The Big One":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            p = Projectile(self.x, self.y, ndx*300, -400, ab.damage, WHITE, 25, self.team, RED, aoe_radius=200)
            projectiles.append(p)

        # ── COSMIC-NOVA ──
        elif name == "Photon Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*700, ndy*700, ab.damage, YELLOW, 12, self.team, WHITE)
            projectiles.append(p)

        elif name == "Cosmic Dash":
            self.body.velocity = (ndx*1000, ndy*400)
            if dist < 120: target.take_damage(ab.damage, ndx*600, attacker=self)

        elif name == "Energy Shield":
            self.invincible_timer = 2.0
            self.particles.emit_ring(self.x, self.y, WHITE, count=20, speed=100)

        elif name == "Binary Power":
            self.particles.emit_ring(self.x, self.y, GOLD, count=50, speed=400)
            target.take_damage(ab.damage, attacker=self)

        # ── TRIDENT-HERO ──
        elif name == "Trident Stab":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            for i in range(3):
                target.take_damage(ab.damage//3, ndx*100, attacker=self)
            self.particles.emit(target.x, target.y, SILVER, count=15)

        elif name == "Water Wave":
            self.particles.emit(self.x + ndx*100, self.y, BLUE, count=30, speed=350)
            if dist < ab.range: target.take_damage(ab.damage, ndx*700, -300, attacker=self)

        elif name == "Shark Call":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            p = Projectile(self.x, self.y, ndx*500, 0, ab.damage, TEAL, 20, self.team, BLUE, piercing=True)
            projectiles.append(p)

        elif name == "Ocean Wrath":
            self.particles.emit_ring(target.x, target.y, BLUE, count=40, speed=300)
            target.take_damage(ab.damage, 0, -600, attacker=self)

        # ── DARK-HERO ──
        elif name == "Batarang":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*600, ndy*600, ab.damage, SILVER, 6, self.team, BLACK)
            projectiles.append(p)

        elif name == "Smoke Pellets":
            self.particles.emit(self.x, self.y, (100,100,100), count=40, speed=150, gravity=False)
            target.stun_timer = 1.5

        elif name == "Grapple Kick":
            target.body.velocity = (-ndx*500, 0)
            self.body.velocity = (ndx*600, 0)
            if dist < 100: target.take_damage(ab.damage, ndx*400, attacker=self)

        elif name == "The Knight":
            for _ in range(5):
                target.take_damage(ab.damage//5, ndx*150, attacker=self)
            self.particles.emit(target.x, target.y, SILVER, count=10)

        # ── SONIC-SPEED ──
        elif name == "Speed Punch":
            for _ in range(5):
                target.take_damage(ab.damage//5, ndx*100, attacker=self)
            self.particles.emit(target.x, target.y, WHITE, count=5)

        elif name == "Sonic Boom":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.body.velocity = (ndx*1500, 0)
            if dist < 200: target.take_damage(ab.damage, ndx*800, attacker=self)

        elif name == "Lightning Rim":
            self.particles.emit_ring(self.x, self.y, BLUE, count=30, speed=400, life=0.5)
            target.take_damage(ab.damage, attacker=self)

        elif name == "Infinite Mass":
            self.body.velocity = (ndx*2000, 0)
            target.take_damage(ab.damage, ndx*1500, -200, attacker=self)

        # ── WING-SOLDIER ──
        elif name == "Wing Slash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            self.particles.emit(target.x, target.y, SILVER, count=15)
            if dist < ab.range: target.take_damage(ab.damage, ndx*300, attacker=self)

        elif name == "Redwing":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*600, ndy*600, ab.damage, RED, 5, self.team, WHITE, homing=True)
            projectiles.append(p)

        elif name == "Dive Bomb":
            self.body.velocity = (ndx*400, 800)
            if dist < 150: target.take_damage(ab.damage, ndx*500, -300, attacker=self)

        elif name == "Air Strike":
            for _ in range(10):
                px = target.x + random.uniform(-100,100)
                p = Projectile(px, -30, 0, 600, ab.damage//10, WHITE, 6, self.team)
                projectiles.append(p)

        # ── WASP-HERO ──
        elif name == "Bio-Sting":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = Projectile(self.x, self.y, ndx*700, ndy*700, ab.damage, YELLOW, 5, self.team, WHITE)
            projectiles.append(p)

        elif name == "Swarm":
            self.body.velocity = (ndx*900, ndy*300)
            if dist < 120: target.take_damage(ab.damage, ndx*300, attacker=self)

        elif name == "Tiny Fury":
            for _ in range(8):
                target.take_damage(ab.damage//8, ndx*50, attacker=self)

        elif name == "Stinger Rain":
            for _ in range(20):
                ang = math.atan2(ndy, ndx) + random.uniform(-0.4, 0.4)
                p = Projectile(self.x, self.y, math.cos(ang)*800, math.sin(ang)*800, ab.damage//20, YELLOW, 4, self.team)
                projectiles.append(p)

        # ── ROCK-TANK ──
        elif name == "Stone Fist":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            self.particles.emit(target.x, target.y, BROWN, count=15, speed=250)
            if dist < ab.range: target.take_damage(ab.damage, ndx*600, -300, attacker=self)

        elif name == "Clobberin Time":
            self.particles.emit_ring(self.x, self.y, ORANGE, count=30, speed=400)
            if dist < ab.range: target.take_damage(ab.damage, ndx*800, -400, attacker=self)

        elif name == "Earthquake":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            self.particles.emit_ring(self.x, self.y, SILVER, count=30, speed=350)
            target.stun_timer = 1.5

        elif name == "Boulder Throw":
            p = Projectile(self.x, self.y, ndx*400, -300, ab.damage, BROWN, 30, self.team, SILVER)
            projectiles.append(p)

        # ── FIRE-BURST ──
        elif name == "Flame On":
            self.particles.emit(self.x, self.y, ORANGE, count=10, gravity=False)
            if dist < 80: target.apply_dot(30, 1.0)

        elif name == "Fireball":
            p = Projectile(self.x, self.y, ndx*500, ndy*500, ab.damage, RED, 10, self.team, ORANGE)
            projectiles.append(p)

        elif name == "Nova Blast":
            self.particles.emit_ring(self.x, self.y, GOLD, count=40, speed=400)
            if dist < ab.range: target.take_damage(ab.damage, attacker=self)

        elif name == "Supernova":
            self.particles.emit_ring(self.x, self.y, WHITE, count=100, speed=600, life=1.5)
            target.take_damage(ab.damage, attacker=self)

        # ── GENIE-MAGIC ──
        elif name == "Magic Lamp":
            # Golden stream of smoke particles
            for i in range(12):
                self.particles.emit(self.x + ndx*i*10, self.y + random.uniform(-15,15), GOLD, count=2, speed=30, size=6, life=1.0, gravity=False)
            if dist < ab.range: target.take_damage(ab.damage, attacker=self)

        elif name == "Giant Hands":
            # Clapping impact lines
            for i in range(10):
                self.particles.emit(target.x - 40, target.y - 100 + i*20, CYAN, count=3, speed=100)
                self.particles.emit(target.x + 40, target.y - 100 + i*20, CYAN, count=3, speed=-100)
            self.particles.emit_ring(target.x, target.y, CYAN, count=20, speed=200, size=10)
            target.take_damage(ab.damage, 0, 500, attacker=self)

        elif name == "Wish Grant":
            self.heal(100)
            self.invincible_timer = 1.0
            self.particles.emit_ring(self.x, self.y, PINK, count=30, speed=150, size=5)

        elif name == "Phenomenal":
            self.particles.emit_ring(self.x, self.y, PURPLE, count=50, speed=400, life=1.2)
            for _ in range(5):
                rx = self.x + random.uniform(-100, 100)
                ry = self.y + random.uniform(-100, 100)
                self.particles.emit_ring(rx, ry, GOLD, count=10, speed=100)
            target.take_damage(ab.damage, attacker=self)

        # ── PLAGUE-WALKER ──
        elif name == "Bite":
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.apply_dot(15, 5.0)

        elif name == "Vomit":
            self.particles.emit(self.x + ndx*80, self.y, GREEN, count=20, speed=150)
            if dist < ab.range: target.apply_dot(25, 3.0)

        elif name == "Horde Call":
            for _ in range(5):
                self.particles.emit(self.x + random.uniform(-50,50), self.y, BROWN, count=5)
            target.take_damage(ab.damage, attacker=self)

        elif name == "Undead Rage":
            for _ in range(6):
                target.take_damage(ab.damage//6, ndx*50, attacker=self)

        # ── VOID-TRAVELER ──
        elif name == "Ray Gun":
            p = Projectile(self.x, self.y, ndx*700, ndy*700, ab.damage, CYAN, 6, self.team, LIME)
            projectiles.append(p)

        elif name == "Abduction":
            target.body.velocity = (0, -1000)
            self.particles.emit_beam(target.x, target.y, target.x, -500, WHITE, count=15)

        elif name == "Gravity Bomb":
            p = Projectile(self.x, self.y, ndx*400, ndy*400, ab.damage, PURPLE, 15, self.team, BLACK, aoe_radius=120)
            projectiles.append(p)

        elif name == "Mothership":
            for _ in range(12):
                px = random.uniform(50, WIDTH-50)
                p = Projectile(px, -50, 0, 700, ab.damage//12, LIME, 8, self.team)
                projectiles.append(p)

        # ── PIRATE-KING ──
        elif name == "Scimitar":
            self.particles.emit(target.x, target.y, SILVER, count=15, speed=300)
            if dist < ab.range: target.take_damage(ab.damage, ndx*300, attacker=self)

        elif name == "Pistol Shot":
            p = Projectile(self.x, self.y, ndx*800, 0, ab.damage, DARK_BG, 5, self.team, SILVER)
            projectiles.append(p)

        elif name == "Cannonade":
            p = Projectile(self.x, self.y, ndx*400, -300, ab.damage, BLACK, 15, self.team, ORANGE, aoe_radius=100)
            projectiles.append(p)

        elif name == "Kraken":
            self.particles.emit_ring(target.x, target.y, BLUE, count=50, speed=300, size=15)
            target.take_damage(ab.damage, 0, -800, attacker=self)

        # ── SHADOW-KNIGHT ──
        elif name == "Shadow Slash":
            self.particles.emit(target.x, target.y, PURPLE, count=20, speed=400)
            if dist < ab.range: target.take_damage(ab.damage, ndx*200, attacker=self)

        elif name == "Dark Dash":
            self.body.position = (target.x + self.facing*60, target.y)
            self.particles.emit(self.x, self.y, BLACK, count=15)

        elif name == "Soul Reaper":
            if dist < ab.range:
                stolen = target.take_damage(ab.damage, attacker=self)
                self.heal(stolen)

        elif name == "Nightfall":
            self.particles.emit_ring(self.x, self.y, TEAL, count=60, speed=500)
            target.take_damage(ab.damage, attacker=self)
            target.stun_timer = 2.0




    def draw(self, screen, font_small):
        if not self.alive:
            return
        x, y = int(self.x), int(self.y)
        s = self.size

        # Flash white on hit
        draw_color = WHITE if self.hit_flash > 0 else self.color
        body_draw  = WHITE if self.hit_flash > 0 else self.body_color

        # Shadow
        shadow_surf = pygame.Surface((s*4, s*4), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, (0,0,0,40), (s*2, s*2), s+2)
        screen.blit(shadow_surf, (x - s*2, y - s*2 + 4))

        # Body (main circle)
        pygame.draw.circle(screen, body_draw, (x, y), s)
        pygame.draw.circle(screen, draw_color, (x, y), s, 2)

        # Eyes
        eye_x = x + self.facing * (s//3)
        eye_y = y - s//4
        pygame.draw.circle(screen, WHITE, (eye_x, eye_y), s//5)
        pygame.draw.circle(screen, BLACK, (eye_x + self.facing*1, eye_y), s//8)

        # ── DRAW WEAPON ──
        w_color = (180, 180, 180) # Default steel
        if self.weapon_type == "sword":
            # Simple sword
            sword_len = s * 1.5
            start = (x + self.facing * s, y + s//2)
            end = (x + self.facing * (s + sword_len), y - s//2)
            pygame.draw.line(screen, w_color, start, end, 4)
            pygame.draw.line(screen, (100, 100, 100), start, (x + self.facing * (s + 5), y + s//2 + 5), 6) # hilt
        elif self.weapon_type == "staff":
            staff_len = s * 2.0
            start = (x + self.facing * s, y + s)
            end = (x + self.facing * s, y - s)
            pygame.draw.line(screen, (100, 70, 30), start, end, 3)
            pygame.draw.circle(screen, self.color, end, 5) # Gem
        elif self.weapon_type == "katana":
            sword_len = s * 1.8
            start = (x + self.facing * s, y + s//4)
            end = (x + self.facing * (s + sword_len), y - s//4)
            pygame.draw.line(screen, (220, 220, 230), start, end, 2)
        elif self.weapon_type == "blaster":
            b_w, b_h = s, s//2
            bx = x + self.facing * s - (b_w if self.facing == -1 else 0)
            by = y - b_h//2
            pygame.draw.rect(screen, (80, 80, 90), (bx, by, b_w, b_h), border_radius=2)
            pygame.draw.rect(screen, CYAN, (bx + (b_w-4 if self.facing == 1 else 0), by + 2, 4, b_h-4)) # Energy glow
        elif self.weapon_type == "bow":
            arc_rect = (x + self.facing * s - s, y - s, s*2, s*2)
            start_angle = -math.pi/2 if self.facing == 1 else math.pi/2
            pygame.draw.arc(screen, (120, 80, 40), arc_rect, start_angle, start_angle + math.pi, 2)
        elif self.weapon_type == "trident":
            staff_len = s * 1.8
            start = (x + self.facing * s, y + s)
            end = (x + self.facing * s, y - s)
            pygame.draw.line(screen, (150, 150, 160), start, end, 3)
            # Prongs
            pygame.draw.line(screen, (150, 150, 160), end, (end[0]-5, end[1]-8), 2)
            pygame.draw.line(screen, (150, 150, 160), end, (end[0]+5, end[1]-8), 2)
            pygame.draw.line(screen, (150, 150, 160), end, (end[0], end[1]-12), 2)
        elif self.weapon_type == "claws":
            for i in range(3):
                off = (i-1)*5
                pygame.draw.line(screen, WHITE, (x + self.facing*s, y + off), (x + self.facing*(s+10), y + off - 5), 2)
        elif self.weapon_type == "hammer":
            staff_len = s * 1.5
            start = (x + self.facing * s, y + s)
            end = (x + self.facing * s, y - s)
            pygame.draw.line(screen, (120, 90, 50), start, end, 5) # Handle
            # Hammer head
            pygame.draw.rect(screen, (100, 100, 110), (end[0]-10, end[1]-5, 20, 15))
        elif self.weapon_type == "chain":
            start = (x + self.facing * s, y)
            for i in range(5):
                cx_ = start[0] + self.facing * i * 6
                cy_ = start[1] + math.sin(pygame.time.get_ticks()*0.01 + i)*5
                pygame.draw.circle(screen, (150, 150, 160), (int(cx_), int(cy_)), 3, 1)
            pygame.draw.circle(screen, RED, (int(start[0] + self.facing*30), int(start[1])), 5) # Weighted end
        
        # ── DRAW SHIELD ──
        if self.has_shield:
            sh_w, sh_h = s//2, s * 1.4
            shx = x + self.facing * (s - 2) - (sh_w if self.facing == -1 else 0)
            shy = y - sh_h//2
            pygame.draw.rect(screen, (150, 160, 170), (shx, shy, sh_w, sh_h), border_radius=4)
            pygame.draw.rect(screen, SILVER, (shx+2, shy+2, sh_w-4, sh_h-4), border_radius=2)

        # Stun stars
        if self.stun_timer > 0:
            for i in range(3):
                angle = pygame.time.get_ticks()*0.005 + i * 2.094
                sx = x + int(math.cos(angle)*(s+6))
                sy = y - s - 6 + int(math.sin(angle)*6)
                pygame.draw.circle(screen, YELLOW, (sx, sy), 4)

        # Invincible shimmer
        if self.invincible_timer > 0.3:
            shimmer = pygame.Surface((s*3, s*3), pygame.SRCALPHA)
            pygame.draw.circle(shimmer, (*WHITE, 40), (s*3//2, s*3//2), s+4)
            screen.blit(shimmer, (x - s*3//2, y - s*3//2))

        # HP bar
        bar_w = 60
        bar_h = 7
        bar_x = x - bar_w//2
        # HP bar
        bar_w = 60
        bar_h = 6
        bar_x = x - bar_w//2
        bar_y = y - s - 12
        pygame.draw.rect(screen, (40,40,40), (bar_x-1, bar_y-1, bar_w+2, bar_h+2))
        hp_frac = self.hp / self.max_hp
        hp_color = (int(255*(1-hp_frac)), int(255*hp_frac), 0)
        pygame.draw.rect(screen, hp_color, (bar_x, bar_y, int(bar_w*hp_frac), bar_h))
        
        # HP Centered inside circle (Video Style)
        hp_val_txt = font_small.render(f"{int(self.hp)}", True, WHITE)
        screen.blit(hp_val_txt, (x - hp_val_txt.get_width()//2, y - hp_val_txt.get_height()//2))

        # Status Label (Video Style)
        if self.stun_timer > 0:
            status_txt = font_small.render("STUNNED", True, YELLOW)
            screen.blit(status_txt, (x + s + 5, y - 5))
        elif self.dot_timer > 0:
            status_txt = font_small.render("DRAINED", True, LIME)
            screen.blit(status_txt, (x + s + 5, y - 5))

        # Name
        name_surf = font_small.render(self.name, True, self.color)
        screen.blit(name_surf, (x - name_surf.get_width()//2, bar_y - 14))

        # ── TRAIT LABEL ──
        if self.trait_label_timer > 0:
            # Shake label for impact
            lx = x + random.randint(-2, 2)
            ly = bar_y - 35 + random.randint(-2, 2)
            t_surf = font_small.render(self.trait_label_txt, True, GOLD) # Use gold for rare
            screen.blit(t_surf, (lx - t_surf.get_width()//2, ly))

        # Cooldown pips
        for i, ab in enumerate(self.abilities):
            pip_x = bar_x + i * 16
            pip_y = bar_y + bar_h + 3
            pip_color = ab.color if ab.ready() else (50,50,60)
            pygame.draw.circle(screen, pip_color, (pip_x, pip_y), 5)
            if not ab.ready():
                frac = 1 - (ab.timer / ab.cooldown)
                pygame.draw.arc(screen, ab.color,
                               (pip_x-5, pip_y-5, 10, 10),
                               math.pi/2, math.pi/2 + frac*math.pi*2, 2)

# ─── BATTLE MANAGER ────────────────────────────────────────────────────────────
class Battle:
    def __init__(self, team_a: List[str], team_b: List[str], is_br=False, arena_type="STADIUM"):
        self.space = pymunk.Space()
        self.space.gravity = (0, GRAVITY)
        self.arena_type = arena_type
        self.particles = ParticleSystem()
        self.popups: List[DamagePopup] = []
        self.shake = 0.0
        self.sounds = SoundManager()
        self.is_br = is_br
        self.over = False
        self.over_timer = 0.0
        self.hit_stop = 0.0
        self.impact_flash = 0.0
        self.timer = 0.0
        self.sd_start = 45 if is_br else 60
        self.sd_active = False
        self.orig_arena_size = 600

        # ── ARENA GENERATION ──
        self.arena_size = 600
        self.arena_rect = pygame.Rect((WIDTH-self.arena_size)//2, (HEIGHT-self.arena_size)//2, self.arena_size, self.arena_size)
        r = self.arena_rect
        static = self.space.static_body
        self.walls = []
        self.hazards = [] # Shapes that deal damage on contact

        if arena_type == "STADIUM":
            # Standard Square
            w_pts = [(r.left, r.top), (r.right, r.top), (r.right, r.bottom), (r.left, r.bottom)]
            for i in range(4):
                w = pymunk.Segment(static, w_pts[i], w_pts[(i+1)%4], 10)
                self.walls.append(w)
        
        elif arena_type == "OCTAGON":
            # 8-sided arena
            cx, cy = WIDTH//2, HEIGHT//2
            rad = 320
            pts = []
            for i in range(8):
                ang = i * (math.pi*2/8)
                pts.append((cx + math.cos(ang)*rad, cy + math.sin(ang)*rad))
            for i in range(8):
                w = pymunk.Segment(static, pts[i], pts[(i+1)%8], 10)
                # Spikes on every other wall
                if i % 2 == 1:
                    w.collision_type = 99 # Hazard type
                self.walls.append(w)

        elif arena_type == "NEXUS":
            # Square with Corner L-walls
            # Outer boundary (invisible/bouncy)
            w_pts = [(r.left, r.top), (r.right, r.top), (r.right, r.bottom), (r.left, r.bottom)]
            for i in range(4):
                self.walls.append(pymunk.Segment(static, w_pts[i], w_pts[(i+1)%4], 5))
            # Inner L-walls
            l_len = 120
            off = 100
            # TL
            self.walls.append(pymunk.Segment(static, (r.left+off, r.top+off), (r.left+off+l_len, r.top+off), 8))
            self.walls.append(pymunk.Segment(static, (r.left+off, r.top+off), (r.left+off, r.top+off+l_len), 8))
            # BR
            self.walls.append(pymunk.Segment(static, (r.right-off, r.bottom-off), (r.right-off-l_len, r.bottom-off), 8))
            self.walls.append(pymunk.Segment(static, (r.right-off, r.bottom-off), (r.right-off, r.bottom-off-l_len), 8))

        elif arena_type == "PILLARS":
            # Outer Square
            w_pts = [(r.left, r.top), (r.right, r.top), (r.right, r.bottom), (r.left, r.bottom)]
            for i in range(4):
                self.walls.append(pymunk.Segment(static, w_pts[i], w_pts[(i+1)%4], 10))
            # 4 Round Pillars
            p_off = 130
            for px, py in [(r.left+p_off, r.top+p_off), (r.right-p_off, r.top+p_off),
                           (r.left+p_off, r.bottom-p_off), (r.right-p_off, r.bottom-p_off)]:
                pill = pymunk.Circle(static, 30, (px, py))
                pill.elasticity = 0.9
                self.walls.append(pill)

        for w in self.walls:
            w.elasticity = 0.95
            w.friction = 0.1
            self.space.add(w)

        # Hazard Collision Handler (Modern Pymunk 7+ style)
        def hazard_begin(arbiter, space, data):
            fighter_shape = arbiter.shapes[0]
            for f in self.fighters:
                if f.shape == fighter_shape:
                    f.hazard_hit_count += 1 # Incremental stage hits
                    dmg = 1.0 + (f.hazard_hit_count - 1) * 0.6
                    f.take_damage(dmg, knockback_x=0, knockback_y=0) 
                    f.particles.emit(f.x, f.y, RED, count=12, speed=300)
            return True
        
        # Use on_collision for Pymunk 7.x
        self.space.on_collision(0, 99, begin=hazard_begin)

        # Fighter-to-Fighter collision sound
        def fighter_collide(arbiter, space, data):
            if arbiter.total_impulse.length > 500:
                self.sounds.play('thud')
            return True
        self.space.on_collision(0, 0, post_solve=fighter_collide)
        
        self.projectiles: List[Projectile] = []
        self.fighters: List[Fighter] = []

        # Create Fighters
        # Standard: team 0 vs team 1
        # BR: each fighter is its own team (0, 1, 2, ...)
        all_configs = []
        if is_br:
            for i, name in enumerate(team_a):
                all_configs.append((name, i))
        else:
            for name in team_a: all_configs.append((name, 0))
            for name in team_b: all_configs.append((name, 1))
        # Spread them out in the stadium
        center_x, center_y = WIDTH//2, HEIGHT//2
        count = len(all_configs)
        for i, (name, team_id) in enumerate(all_configs):
            angle = (i / count) * math.pi * 2
            dist = self.arena_size * 0.35
            fx = center_x + math.cos(angle) * dist
            fy = center_y + math.sin(angle) * dist
            f = Fighter(name, fx, fy, team_id, self.space, self.particles)
            f.battle_ref = self
            self.fighters.append(f)

        # Teams strategy (Priority Target) - must happen after fighters are spawned
        self.team_priorities = {}
        if is_br:
            for f in self.fighters:
                other_teams = [o for o in self.fighters if o.team != f.team]
                if other_teams:
                    self.team_priorities[f.team] = random.choice(other_teams)
        else:
            team_a_f = [f for f in self.fighters if f.team == 0]
            team_b_f = [f for f in self.fighters if f.team == 1]
            if team_b_f: self.team_priorities[0] = random.choice(team_b_f)
            if team_a_f: self.team_priorities[1] = random.choice(team_a_f)

        self.elapsed = 0.0

    def get_team(self, team_id):
        return [f for f in self.fighters if f.team == team_id and f.alive]

    def update(self, dt):
        self.timer += dt
        self.shake = max(0, self.shake - dt * 25) # Faster recovery for intensity
        self.impact_flash = max(0, self.impact_flash - dt)
        
        # ── SUDDEN DEATH (Shrinking Arena) ──
        if self.elapsed > self.sd_start:
            self.sd_active = True
            # Inexorably shrink the arena size (min 200)
            shrink_spd = 25 # pixels per second
            self.arena_size = max(180, self.arena_size - dt * shrink_spd)
            
            # Reposition the walls (Rect-based arenas only)
            if self.arena_type != "OCTAGON":
                self.arena_rect = pygame.Rect((WIDTH-self.arena_size)//2, (HEIGHT-self.arena_size)//2, self.arena_size, self.arena_size)
                r = self.arena_rect
                # Update existing physics walls positions
                if len(self.walls) >= 4:
                    self.walls[0].a, self.walls[0].b = (r.left, r.top), (r.right, r.top)
                    self.walls[1].a, self.walls[1].b = (r.right, r.top), (r.right, r.bottom)
                    self.walls[2].a, self.walls[2].b = (r.right, r.bottom), (r.left, r.bottom)
                    self.walls[3].a, self.walls[3].b = (r.left, r.bottom), (r.left, r.top)
                self.space.reindex_static()

        # ── START MATCH DELAY (Freeze for 1s) ──
        if self.elapsed < 1.0:
            self.elapsed += dt
            self.particles.update(dt)
            return

        self.space.step(dt)
        self.particles.update(dt)
        self.popups = [p for p in self.popups if p.update(dt)]

        if self.over:
            self.over_timer -= dt
            return

        self.elapsed += dt
        alive_fighters = [f for f in self.fighters if f.alive]

        for f in self.fighters:
            if not f.alive:
                continue
            # Sudden Death Void Damage (Incremental)
            if self.sd_active:
                if not self.arena_rect.collidepoint(f.x, f.y):
                    # For SD, we treat every 1s of exposure as a "hit"
                    f.hazard_hit_count += 1 * dt 
                    base_dmg = 2.0 * dt # Fixed low rate + incremental
                    sd_bonus = (f.hazard_hit_count) * 0.6 * dt
                    f.take_damage(base_dmg + sd_bonus, knockback_x=0, knockback_y=0)
                    if random.random() < 0.1:
                        f.particles.emit(f.x, f.y, PURPLE, count=1)
            enemies = [e for e in alive_fighters if e.team != f.team]
            f.update(dt, enemies, self.projectiles)

        # Update projectiles
        for proj in self.projectiles:
            enemies_for_proj = [f for f in alive_fighters if f.team != proj.owner_team]
            proj.update(dt, enemies_for_proj)
            # Collision check
            for f in enemies_for_proj:
                dist = math.hypot(f.x - proj.x, f.y - proj.y)
                hit_r = f.size + proj.size
                if dist < hit_r and proj.alive:
                    # AOE
                    if proj.aoe_radius > 0:
                        for ff in alive_fighters:
                            d2 = math.hypot(ff.x - proj.x, ff.y - proj.y)
                            if d2 < proj.aoe_radius and ff.team != proj.owner_team:
                                kb = (1 - d2/proj.aoe_radius)
                                dx2 = ff.x - proj.x
                                dy2 = ff.y - proj.y
                                d3  = max(1, math.hypot(dx2, dy2))
                                ff.take_damage(proj.damage,
                                              knockback_x=dx2/d3*400*kb,
                                              knockback_y=-200*kb,
                                              attacker=proj.owner)
                        self.particles.emit_ring(proj.x, proj.y, proj.color, count=20, speed=200)
                    else:
                        dx_ = f.x - proj.x
                        dy_ = f.y - proj.y
                        d_  = max(1, math.hypot(dx_, dy_))
                        f.take_damage(proj.damage,
                                     knockback_x=dx_/d_*200,
                                     knockback_y=-150,
                                     attacker=proj.owner)
                    if not proj.piercing:
                        proj.alive = False
                    self.particles.emit(proj.x, proj.y, proj.color, count=8, speed=150)
                    break

        self.projectiles = [p for p in self.projectiles if p.alive]

        # Win check
        alive_fighters = [f for f in self.fighters if f.alive]
        if self.is_br:
            if len(alive_fighters) <= 1:
                self.over = True
                self.shake = 0.0 # Stop shake for readability
                self.winner_team = alive_fighters[0].team if alive_fighters else -1
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)
        else:
            # Team Battle
            alive_a = [f for f in alive_fighters if f.team == 0]
            alive_b = [f for f in alive_fighters if f.team == 1]
            if not alive_a:
                self.over = True
                self.shake = 0.0
                self.winner_team = 1
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)
            elif not alive_b:
                self.over = True
                self.shake = 0.0
                self.winner_team = 0
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)

    def draw(self, screen, font, font_small, font_big):
        # 1. Create/Get canvas
        canvas = pygame.Surface((WIDTH, HEIGHT))
        canvas.fill((15, 15, 25))
        
        # 2. Draw World Elements to Canvas
        # ── DRAW ARENA ──
        if self.arena_type == "OCTAGON":
            cx, cy = WIDTH//2, HEIGHT//2
            rad = 320
            pts = []
            for i in range(8):
                ang = i * (math.pi*2/8)
                pts.append((cx + math.cos(ang)*rad + self.shake_off()[0], cy + math.sin(ang)*rad + self.shake_off()[1]))
            for i in range(8):
                color = RED if i%2==1 else SILVER
                pygame.draw.line(canvas, color, pts[i], pts[(i+1)%8], 6 if i%2==1 else 4)
                if i%2==1: # Draw Spikes
                    # Middle of segment
                    mx, my = (pts[i][0]+pts[(i+1)%8][0])/2, (pts[i][1]+pts[(i+1)%8][1])/2
                    pygame.draw.circle(canvas, RED, (int(mx), int(my)), 12, 2)
        else:
            # Default segment/circle drawing for other arenas
            for w in self.walls:
                if isinstance(w, pymunk.Segment):
                    p1 = (w.a.x + self.shake_off()[0], w.a.y + self.shake_off()[1])
                    p2 = (w.b.x + self.shake_off()[0], w.b.y + self.shake_off()[1])
                    color = (200, 50, 50) if getattr(w, 'collision_type', 0) == 99 else SILVER
                    pygame.draw.line(canvas, color, p1, p2, int(w.radius)*2 or 2)
                elif isinstance(w, pymunk.Circle):
                    px = w.body.position.x + w.offset.x + self.shake_off()[0]
                    py = w.body.position.y + w.offset.y + self.shake_off()[1]
                    pygame.draw.circle(canvas, SILVER, (int(px), int(py)), int(w.radius), 2)
                    pygame.draw.circle(canvas, (50, 50, 70), (int(px), int(py)), int(w.radius)-4)

        # Draw Arena Grid/Floor for Stadium/Pillars/Nexus within rect
        if self.arena_type != "OCTAGON":
            r = self.arena_rect
            for x in range(int(r.left), int(r.right)+1, 120):
                pygame.draw.line(canvas, (30, 35, 45), (x + self.shake_off()[0], r.top + self.shake_off()[1]), (x + self.shake_off()[0], r.bottom + self.shake_off()[1]))
            for y in range(int(r.top), int(r.bottom)+1, 120):
                pygame.draw.line(canvas, (30, 35, 45), (r.left + self.shake_off()[0], y + self.shake_off()[1]), (r.right + self.shake_off()[0], y + self.shake_off()[1]))
            pygame.draw.rect(canvas, (50, 60, 80), (r.left + self.shake_off()[0], r.top + self.shake_off()[1], r.width, r.height), 2)

        # Draw World Objects
        for proj in self.projectiles: proj.draw(canvas)
        self.particles.draw(canvas)
        for f in self.fighters: f.draw(canvas, font_small)
        for p in self.popups: p.draw(canvas, font_small, font_big)

        # Draw HUD (Inside shaking canvas for high-action feel)
        self._draw_hud(canvas, font, font_small)

        # 3. Final Screenshake & Blit to Screen
        off_x, off_y = (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)) if self.shake > 0 else (0,0)
        screen.blit(canvas, (off_x, off_y))

        # Draw Sudden Death Warning
        if self.sd_active:
            sd_txt = font_big.render("SUDDEN DEATH!!", True, RED)
            screen.blit(sd_txt, (WIDTH//2 - sd_txt.get_width()//2, 80))
            # Intense screen flash on SD start
            if self.elapsed < self.sd_start + 0.3:
                flash = pygame.Surface((WIDTH, HEIGHT))
                flash.fill(RED); flash.set_alpha(100)
                screen.blit(flash, (0,0))

        # ── PRE-MATCH LABELS (Ready / Fight) ──
        if self.elapsed < 1.5:
            if self.elapsed < 0.7:
                txt = font_big.render("READY?", True, GOLD)
            else:
                txt = font_big.render("FIGHT!!", True, WHITE)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 100))

        # Win screen (Always on top, no shake for readability)
        if self.over:
            if self.is_br:
                winner_name = "NONE"
                color = GOLD
                for f in self.fighters:
                    if f.team == self.winner_team:
                        winner_name, color = f.name, f.color
                        break
                msg = f"🏆 {winner_name} WINS!"
            else:
                team_name = "Team Blue" if self.winner_team == 0 else "Team Red"
                color = BLUE if self.winner_team == 0 else RED
                msg = f"🏆 {team_name} WINS!"

            # ── MATCH PERFORMANCE & MVP ──
            # Determine MVP (Kills * 200 + Damage)
            mvp = max(self.fighters, key=lambda f: f.kills * 200 + f.damage_dealt)
            
            # Winner Banner
            win_surf = font_big.render(msg, True, color)
            screen.blit(win_surf, (WIDTH//2 - win_surf.get_width()//2, 160))

            # MVP Spotlight
            mvp_txt = font.render(f"🏅 MATCH MVP: {mvp.name}", True, GOLD)
            screen.blit(mvp_txt, (WIDTH//2 - mvp_txt.get_width()//2, 240))
            
            # Stats Display
            stats_box = pygame.Rect(WIDTH//2 - 250, 290, 500, 220)
            pygame.draw.rect(screen, (20, 20, 40, 220), stats_box, border_radius=15)
            pygame.draw.rect(screen, color, stats_box, 3, border_radius=15)
            
            # Top Performers
            best_damage = max(self.fighters, key=lambda f: f.damage_dealt)
            best_traits = max(self.fighters, key=lambda f: f.traits_activated_count)
            
            y_off = 315
            stats_data = [
                ("➤ Most Kills:", mvp.name, f"({mvp.kills})", mvp.color),
                ("➤ Max Damage:", best_damage.name, f"({int(best_damage.damage_dealt)})", best_damage.color),
                ("➤ Luckiest:", best_traits.name, f"({best_traits.traits_activated_count} triggers)", GOLD)
            ]
            for label, name, val, c in stats_data:
                # 1. Label (Silver)
                lbl_s = font.render(label, True, SILVER)
                screen.blit(lbl_s, (stats_box.x + 30, y_off))
                
                # 2. Name (Character Color)
                name_s = font.render(f" {name}", True, c)
                screen.blit(name_s, (stats_box.x + 30 + lbl_s.get_width(), y_off))
                
                # 3. Value (White)
                val_s = font.render(f" {val}", True, WHITE)
                screen.blit(val_s, (stats_box.x + 30 + lbl_s.get_width() + name_s.get_width(), y_off))
                
                y_off += 50

            # Prompt
            ret_txt = font.render("PRESS [SPACE] TO RETURN TO MENU", True, WHITE if int(self.timer*2)%2==0 else SILVER)
            screen.blit(ret_txt, (WIDTH//2 - ret_txt.get_width()//2, 550))

        # ── HOVER INTEL OVERLAY ──
        mx, my = pygame.mouse.get_pos()
        hovered_f = None
        for f in self.fighters:
            if f.alive and math.hypot(f.x - mx, f.y - my) < f.size + 10:
                hovered_f = f
                break
        
        if hovered_f:
            # Draw a sleek panel at top center
            panel_w, panel_h = 450, 100
            px, py = WIDTH//2 - panel_w//2, 10
            intel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            intel_surf.fill((10, 10, 20, 200))
            pygame.draw.rect(intel_surf, hovered_f.color, (0, 0, panel_w, panel_h), 2, border_radius=10)
            screen.blit(intel_surf, (px, py))

            # Header
            name_s = font.render(f"TARGET: {hovered_f.name}", True, hovered_f.color)
            screen.blit(name_s, (px + 15, py + 8))
            
            # Abilities list
            for i, ab in enumerate(hovered_f.abilities):
                ab_y = py + 35 + (i//2)*25
                ab_x = px + 15 + (i%2)*220
                status_c = ab.color if ab.ready() else (100, 100, 100)
                txt = f"{ab.name}: {int(ab.damage)} dmg"
                ab_s = font_small.render(txt, True, status_c)
                screen.blit(ab_s, (ab_x, ab_y))
                # Small cooldown bar under each ability
                if not ab.ready():
                    frac = 1 - (ab.timer / ab.cooldown)
                    pygame.draw.rect(screen, (50,50,50), (ab_x, ab_y+16, 180, 4))
                    pygame.draw.rect(screen, ab.color, (ab_x, ab_y+16, int(180*frac), 4))

        # Timer
        mins = int(self.elapsed) // 60
        secs = int(self.elapsed) % 60
        timer_txt = font.render(f"{mins:02d}:{secs:02d}", True, WHITE)
        screen.blit(timer_txt, (WIDTH//2 - timer_txt.get_width()//2, 12))

    def shake_off(self):
        if self.shake > 0:
            return (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake))
        return (0, 0)

    def _draw_hud(self, screen, font, font_small):
        # In Battle Royale, every fighter is a separate entity
        # In Team Mode, we filter for teams 0 and 1
        if self.is_br:
            mid = (len(self.fighters) + 1) // 2
            list_a = self.fighters[:mid]
            list_b = self.fighters[mid:]
        else:
            list_a = [f for f in self.fighters if f.team == 0]
            list_b = [f for f in self.fighters if f.team == 1]

        def draw_team_panel(fighters, x_start, color):
            for i, f in enumerate(fighters):
                px = x_start
                py = (HEIGHT - len(fighters)*60)//2 + i*60
                # Panel bg
                panel = pygame.Surface((170, 55), pygame.SRCALPHA)
                panel.fill((0, 0, 0, 150))
                screen.blit(panel, (px, py))
                pygame.draw.rect(screen, color, (px, py, 170, 55), 2)
                # Name
                n_surf = font_small.render(f.name, True, color)
                screen.blit(n_surf, (px+5, py+3))
                # HP bar
                hp_frac = f.hp / f.max_hp
                hp_c = (int(220*(1-hp_frac)), int(220*hp_frac), 40)
                pygame.draw.rect(screen, (40,40,40), (px+5, py+20, 160, 12))
                pygame.draw.rect(screen, hp_c, (px+5, py+20, int(160*hp_frac), 12))
                pygame.draw.rect(screen, WHITE, (px+4, py+19, 162, 14), 1)
                # HP text
                hp_txt = font_small.render(f"{int(f.hp)}/{f.max_hp}", True, WHITE)
                screen.blit(hp_txt, (px+5, py+35))
                # Ability cooldowns
                for j, ab in enumerate(f.abilities):
                    cx = px + 5 + j*40
                    cy = py + 48
                    c = ab.color if ab.ready() else (50,50,60)
                    pygame.draw.rect(screen, c, (cx, cy, 35, 5))
                    if not ab.ready():
                        frac = 1 - (ab.timer / ab.cooldown)
                        pygame.draw.rect(screen, ab.color, (cx, cy, int(35*frac), 5))

        # Position panels left/right of arena center
        left_edge = (WIDTH - self.arena_size) // 2
        right_edge = left_edge + self.arena_size
        draw_team_panel(list_a, left_edge - 180, BLUE if not self.is_br else (100, 180, 255))
        draw_team_panel(list_b, right_edge + 10, RED if not self.is_br else (255, 150, 100))

# ─── MENU SYSTEM ──────────────────────────────────────────────────────────────
class Menu:
    def __init__(self, font, font_small, font_big):
        self.font       = font
        self.font_small = font_small
        self.font_big   = font_big

        self.state = "main"      # main, mode_select, char_select, battle
        self.mode  = "1v1"
        self.modes = ["1v1", "2v2", "1v2", "3v3", "4v4", "1v3", "2v3", "Battle Royale"]
        self.mode_idx = 0
        self.arenas = ["STADIUM", "NEXUS", "OCTAGON", "PILLARS"]
        self.arena_idx = 0

        self.chars = list(CHARACTER_DATA.keys())
        self.selected_a: List[str] = []
        self.selected_b: List[str] = []
        self.selecting_team = 0   # 0 = team A, 1 = team B
        self.needed_a = 1
        self.needed_b = 1
        self.hover_char = None

        self.particles = ParticleSystem()
        self.bg_timer = 0.0

    def needed_counts(self):
        mode = self.modes[self.mode_idx]
        if mode == "Battle Royale":
            return 8, 0 
        parts = mode.split("v")
        return int(parts[0]), int(parts[1])

    def handle_event(self, event):
        if self.state == "main":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "mode_select"
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.state = "mode_select"

        elif self.state == "mode_select":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.mode_idx = (self.mode_idx - 1) % len(self.modes)
                elif event.key == pygame.K_RIGHT:
                    self.mode_idx = (self.mode_idx + 1) % len(self.modes)
                elif event.key == pygame.K_UP: self.arena_idx = (self.arena_idx - 1) % len(self.arenas)
                elif event.key == pygame.K_DOWN: self.arena_idx = (self.arena_idx + 1) % len(self.arenas)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.needed_a, self.needed_b = self.needed_counts()
                    self.selected_a = []
                    self.selected_b = []
                    self.selecting_team = 0
                    self.state = "char_select"
                elif event.key == pygame.K_ESCAPE:
                    self.state = "main"
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # Left arrow
                if 500 < mx < 560 and HEIGHT//2 - 30 < my < HEIGHT//2 + 30:
                    self.mode_idx = (self.mode_idx - 1) % len(self.modes)
                # Right arrow
                elif WIDTH-560 < mx < WIDTH-500 and HEIGHT//2 - 30 < my < HEIGHT//2 + 30:
                    self.mode_idx = (self.mode_idx + 1) % len(self.modes)
                else:
                    self.needed_a, self.needed_b = self.needed_counts()
                    self.selected_a = []
                    self.selected_b = []
                    self.selecting_team = 0
                    self.state = "char_select"

        elif self.state == "char_select":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "mode_select"
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                card_w, card_h = 115, 90
                cols = 10
                start_x = WIDTH//2 - (cols * (card_w+12))//2
                start_y = 100
                for i, name in enumerate(self.chars):
                    col = i % cols
                    row = i // cols
                    cx = start_x + col*(card_w+12)
                    cy = start_y + row*(card_h+12)
                    if cx <= mx <= cx+card_w and cy <= my <= cy+card_h:
                        if self.selecting_team == 0 and len(self.selected_a) < self.needed_a:
                            self.selected_a.append(name)
                            self.particles.emit(mx, my, BLUE, count=15, speed=150)
                            # Auto advance/check for standard modes
                            if self.modes[self.mode_idx] != "Battle Royale":
                                if len(self.selected_a) == self.needed_a:
                                    self.selecting_team = 1
                        elif self.selecting_team == 1 and len(self.selected_b) < self.needed_b:
                            self.selected_b.append(name)
                            self.particles.emit(mx, my, RED, count=15, speed=150)
                            if len(self.selected_b) == self.needed_b:
                                self.state = "battle"

                # Independent Start button for BR
                if self.modes[self.mode_idx] == "Battle Royale":
                    if 1040 <= mx <= 1190 and 690 <= my <= 790 and len(self.selected_a) >= 2:
                        self.state = "battle"
                    elif len(self.selected_a) >= 8:
                        self.state = "battle"

    def update(self, dt):
        self.bg_timer += dt
        self.particles.update(dt)
        # Ambient particles on main menu
        if self.state == "main" and random.random() < 0.3:
            c = random.choice([BLUE, PURPLE, CYAN, GOLD])
            self.particles.emit(random.randint(0,WIDTH), HEIGHT+10,
                               c, count=1, speed=random.randint(40,120),
                               size=random.randint(2,5), life=3.0,
                               gravity=False,
                               direction=-math.pi/2 + random.uniform(-0.5,0.5))

    def draw(self, screen):
        screen.fill(DARK_BG)
        self.particles.draw(screen)

        if self.state == "main":
            self._draw_main(screen)
        elif self.state == "mode_select":
            self._draw_mode_select(screen)
        elif self.state == "char_select":
            self._draw_char_select(screen)

    def _draw_main(self, screen):
        # Title
        title = self.font_big.render("⚔️  BATTLE  SIMULATOR  ⚔️", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))

        sub = self.font.render("Physics-Based Combat Simulation", True, SILVER)
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 195))

        # Animated character previews
        chars_preview = list(CHARACTER_DATA.keys())
        for i, name in enumerate(chars_preview):
            x = 80 + i * 120
            y = 360 + int(math.sin(self.bg_timer*1.5 + i*0.5)*12)
            data = CHARACTER_DATA[name]
            pygame.draw.circle(screen, data["color"], (x, y), 22)
            pygame.draw.circle(screen, data["body_color"], (x, y), 22, 3)
            lbl = self.font_small.render(name, True, data["color"])
            screen.blit(lbl, (x - lbl.get_width()//2, y + 28))

        start_txt = self.font.render("PRESS SPACE OR CLICK TO START", True,
                                     WHITE if int(self.bg_timer*2)%2==0 else GOLD)
        screen.blit(start_txt, (WIDTH//2 - start_txt.get_width()//2, 500))

        info = self.font_small.render("10 Unique Characters  •  7 Battle Modes  •  Real Physics Engine", True, SILVER)
        screen.blit(info, (WIDTH//2 - info.get_width()//2, 560))

    def _draw_mode_select(self, screen):
        title = self.font_big.render("SELECT BATTLE MODE", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        mode = self.modes[self.mode_idx]
        if mode == "Battle Royale":
            txt = "FREE FOR ALL: 2 TO 8 FIGHTERS"
        else:
            na, nb = self.needed_counts()
            txt = f"{na} vs {nb} TEAM BATTLE"
        
        mode_txt = self.font_big.render(mode, True, WHITE)
        screen.blit(mode_txt, (WIDTH//2 - mode_txt.get_width()//2, 180))
        
        hint = self.font.render(txt, True, SILVER)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, 230))

        # Arena Selection
        arena_title = self.font.render("SELECT ARENA (UP/DOWN)", True, GOLD)
        screen.blit(arena_title, (WIDTH//2 - arena_title.get_width()//2, 580))
        
        for i, a_name in enumerate(self.arenas):
            color = WHITE if i == self.arena_idx else (100, 100, 100)
            prefix = "▶ " if i == self.arena_idx else "  "
            a_surf = self.font.render(prefix + a_name, True, color)
            screen.blit(a_surf, (WIDTH//2 - a_surf.get_width()//2, 620 + i * 30))

        # Big mode display
        mode_surf = self.font_big.render(mode, True, WHITE)
        screen.blit(mode_surf, (WIDTH//2 - mode_surf.get_width()//2, HEIGHT//2 - 60))

        # Arrows
        l_arr = self.font_big.render("◀", True, GOLD)
        r_arr = self.font_big.render("▶", True, GOLD)
        screen.blit(l_arr, (WIDTH//2 - 200, HEIGHT//2 - 60))
        screen.blit(r_arr, (WIDTH//2 + 160, HEIGHT//2 - 60))

        desc_map = {
            "1v1": "Classic 1-on-1 duel",
            "2v2": "Team battle — 2 vs 2",
            "1v2": "Outnumbered — 1 vs 2",
            "3v3": "Grand team clash — 3 vs 3",
            "4v4": "Epic army battle — 4 vs 4",
            "1v3": "Ultimate challenge — 1 vs 3",
            "2v3": "Asymmetric warfare — 2 vs 3",
        }
        desc = self.font.render(desc_map.get(mode, ""), True, SILVER)
        screen.blit(desc, (WIDTH//2 - desc.get_width()//2, HEIGHT//2 + 20))

        hint = self.font.render("← → to change  |  SPACE or CLICK to confirm", True, WHITE)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 80))

        esc_txt = self.font_small.render("ESC = back", True, SILVER)
        screen.blit(esc_txt, (20, HEIGHT - 30))

    def _draw_char_select(self, screen):

        if self.modes[self.mode_idx] == "Battle Royale":
            title_txt = "BATTLE ROYALE"
            title_c = GOLD
            needed = 8
            selected = self.selected_a
            hint_txt = f"Choose 2 to 8 Fighters ({len(selected)}/8)"
        else:
            title_txt = "SELECT TEAM BLUE" if self.selecting_team == 0 else "SELECT TEAM RED"
            title_c   = BLUE if self.selecting_team == 0 else RED
            needed = self.needed_a if self.selecting_team == 0 else self.needed_b
            selected = self.selected_a if self.selecting_team == 0 else self.selected_b
            hint_txt = f"Choose {needed} character{'s' if needed>1 else ''}  ({len(selected)}/{needed} selected)"

        title = self.font_big.render(title_txt, True, title_c)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))

        progress = self.font.render(hint_txt, True, WHITE)
        screen.blit(progress, (WIDTH//2 - progress.get_width()//2, 70))
        
        if self.modes[self.mode_idx] == "Battle Royale" and len(selected) >= 2:
            # START Button
            pygame.draw.rect(screen, GREEN, (1050, 700, 130, 80), border_radius=10)
            st_txt = self.font.render("START", True, BLACK)
            screen.blit(st_txt, (1050 + 130//2 - st_txt.get_width()//2, 700 + 80//2 - st_txt.get_height()//2))

        # Character cards
        card_w, card_h = 114, 88
        cols = 10
        start_x = WIDTH//2 - (cols * (card_w+10))//2
        start_y = 120
        mx, my = pygame.mouse.get_pos()

        hover_target = None

        for i, name in enumerate(self.chars):
            col = i % cols
            row = i // cols
            cx = start_x + col*(card_w+10)
            cy = start_y + row*(card_h+10)
            data = CHARACTER_DATA[name]

            in_a = name in self.selected_a
            in_b = name in self.selected_b
            hovered = cx <= mx <= cx+card_w and cy <= my <= cy+card_h
            if hovered: hover_target = (cx, cy, name, data)

            # Card background
            bg_c = (25,25,50)
            if in_a: bg_c = (10,20,60)
            if in_b: bg_c = (60,10,20)
            if hovered: bg_c = (35,35,65)
            pygame.draw.rect(screen, bg_c, (cx, cy, card_w, card_h), border_radius=8)

            # Border
            border_c = (60,60,80)
            if in_a: border_c = BLUE
            if in_b: border_c = RED
            if hovered and not in_a and not in_b: border_c = GOLD
            pygame.draw.rect(screen, border_c, (cx, cy, card_w, card_h), 2, border_radius=8)

            # Character circle
            cc_x = cx + card_w//2
            cc_y = cy + 28
            pygame.draw.circle(screen, data["color"], (cc_x, cc_y), 18)
            pygame.draw.circle(screen, WHITE, (cc_x, cc_y), 18, 2)

            # Team indicators (Updated for multiple selections)
            if self.modes[self.mode_idx] == "Battle Royale":
                cnt = self.selected_a.count(name)
                if cnt > 0:
                    txt = f"x{cnt}"
                    t = self.font_small.render(txt, True, GOLD)
                    screen.blit(t, (cx+4, cy+4))
            else:
                if in_a:
                    count_a = self.selected_a.count(name)
                    txt = "A" if count_a == 1 else f"A x{count_a}"
                    t = self.font_small.render(txt, True, WHITE)
                    screen.blit(t, (cx+4, cy+4))
                if in_b:
                    count_b = self.selected_b.count(name)
                    txt = "B" if count_b == 1 else f"B x{count_b}"
                    t = self.font_small.render(txt, True, WHITE)
                    screen.blit(t, (cx + card_w - t.get_width() - 4, cy+4))

            # Name
            n_surf = self.font_small.render(name, True, data["color"])
            screen.blit(n_surf, (cc_x - n_surf.get_width()//2, cy + 50))

        # ── DRAW TOOLTIP LAST (Always On Top) ──
        if hover_target:
            cx, cy, name, data = hover_target
            # Tooltip geometry
            desc_lines = data["description"].split("\n")
            tip_w = 300 
            tip_x = cx + card_w + 8
            if tip_x + tip_w > WIDTH: tip_x = cx - tip_w - 8
            tip_y = cy - 20 # Offset up slightly
            
            # Height includes: Name, Descr, Abiliries, and the new Hidden Trait pool
            tip_h = 50 + len(desc_lines)*18 + len(data.get("abilities", []))*20 + 45
            
            tip_surf = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
            tip_surf.fill((10, 10, 30, 245)) # Slightly more opaque for premium feel
            pygame.draw.rect(tip_surf, GOLD, (0, 0, tip_w, tip_h), 2, border_radius=12)
            screen.blit(tip_surf, (tip_x, tip_y))
            
            y_off = 15
            # Header with Icon
            icon_txt = "💎"
            n_s = self.font.render(f"{icon_txt} {name}", True, data["color"])
            screen.blit(n_s, (tip_x+12, tip_y+y_off)); y_off += 32
            
            # Description
            for line in desc_lines:
                l_s = self.font_small.render(line.strip(), True, SILVER)
                screen.blit(l_s, (tip_x+12, tip_y+y_off)); y_off += 18
            
            y_off += 8
            # Abilities
            for ab in data["abilities"]:
                # Draw small bullet
                pygame.draw.rect(screen, ab.color, (tip_x+12, tip_y+y_off+5, 4, 4))
                ab_s = self.font_small.render(f"  {ab.name}: {int(ab.damage)} dmg", True, WHITE)
                screen.blit(ab_s, (tip_x+18, tip_y+y_off)); y_off += 20

            # ── HIDDEN TRAIT POOL ──
            y_off += 10
            pygame.draw.line(screen, (50, 50, 70), (tip_x+10, tip_y+y_off), (tip_x+tip_w-10, tip_y+y_off), 1)
            y_off += 8
            trait_lbl = self.font_small.render("Rare Hidden Traits Pool (Luck-based):", True, GOLD)
            screen.blit(trait_lbl, (tip_x+12, tip_y+y_off)); y_off += 16
            traits_txt = self.font_small.render("• RAGE   • ASCENSION   • WIND   • REBIRTH", True, (255, 230, 150))
            screen.blit(traits_txt, (tip_x+12, tip_y+y_off))

        # Selected display
        sel_y = start_y + ((len(self.chars)-1)//cols + 1)*(card_h+12) + 10
        a_lbl = self.font.render("Team Blue: " + ("  ".join(self.selected_a) or "---"), True, BLUE)
        b_lbl = self.font.render("Team Red:  " + ("  ".join(self.selected_b) or "---"), True, RED)
        screen.blit(a_lbl, (20, sel_y))
        screen.blit(b_lbl, (20, sel_y+28))

        self.particles.draw(screen)
        esc_txt = self.font_small.render("ESC = back to mode select", True, SILVER)
        screen.blit(esc_txt, (20, HEIGHT-28))

# ─── MAIN GAME LOOP ───────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("⚔️ Physics Battle Simulator")
    clock  = pygame.time.Clock()

    # Fonts
    try:
        font_big   = pygame.font.SysFont("segoeuiemoji,arial", 48, bold=True)
        font       = pygame.font.SysFont("segoeuiemoji,arial", 24)
        font_small = pygame.font.SysFont("segoeuiemoji,arial", 14)
    except:
        font_big   = pygame.font.Font(None, 56)
        font       = pygame.font.Font(None, 28)
        font_small = pygame.font.Font(None, 18)

    menu   = Menu(font, font_small, font_big)
    battle: Optional[Battle] = None
    state  = "menu"

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and state == "battle":
                    state = "menu"
                    menu.state = "main"
                    battle = None
                if event.key == pygame.K_SPACE and state == "battle":
                    if battle and battle.over:
                        state = "menu"
                        menu.state = "main"
                        battle = None

            if state == "menu":
                menu.handle_event(event)

        if state == "menu":
            menu.update(dt)
            menu.draw(screen)
            if menu.state == "battle":
                is_br = (menu.modes[menu.mode_idx] == "Battle Royale")
                battle = Battle(menu.selected_a, menu.selected_b, is_br=is_br, 
                               arena_type=menu.arenas[menu.arena_idx])
                state = "battle"
                menu.state = "main"
        elif state == "battle" and battle:
            battle.update(dt)
            battle.draw(screen, font, font_small, font_big)
            # FPS
            fps_txt = font_small.render(f"FPS: {int(clock.get_fps())}", True, (80,80,100))
            screen.blit(fps_txt, (WIDTH-70, HEIGHT-20))
            # ESC hint
            esc_h = font_small.render("ESC = menu", True, (60,60,80))
            screen.blit(esc_h, (10, HEIGHT-20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
