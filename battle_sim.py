import pygame
import pymunk
import pymunk.pygame_util
import math
import random
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import numpy as np
from pokemon_legendaries import (
    LEGENDARY_COUNTER_MOVES,
    LEGENDARY_MOVE_TYPES,
    LEGENDARY_POKEMON_DATA,
    LEGENDARY_SPRITES,
    LEGENDARY_TYPE_EFFECTIVENESS,
)

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 540, 960
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
        dur = 0.25  # slightly longer but softer
        t = np.linspace(0, dur, int(sr*dur))
        freq = np.linspace(100, 30, len(t)) # lower freq
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-12 * t)
        buf = (snd * env * 0.15 * 32767).astype(np.int16) # volume dropped from 0.6 -> 0.15
        stereo = np.column_stack((buf, buf))
        self.sounds['thud'] = pygame.sndarray.make_sound(stereo)

    def _gen_jump(self):
        sr = 44100
        dur = 0.15
        t = np.linspace(0, dur, int(sr*dur))
        freq = np.linspace(200, 400, len(t)) # sweeps up
        snd = np.sin(2 * np.pi * freq * t)
        env = np.exp(-15 * t)
        buf = (snd * env * 0.1 * 32767).astype(np.int16) # very soft jump sound
        stereo = np.column_stack((buf, buf))
        self.sounds['jump'] = pygame.sndarray.make_sound(stereo)

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

    def _gen_pokemon_bgm(self):
        sr = 44100
        dur = 3.2
        t = np.linspace(0, dur, int(sr*dur))
        freqs = [[261.63, 329.63, 392.00], [349.23, 440.00, 523.25]]
        mixed = np.zeros_like(t)
        seg = len(t) // len(freqs)
        for i, chord in enumerate(freqs):
            tt = t[i*seg : min((i+1)*seg, len(t))]
            env = np.sin(np.pi * (tt - tt[0]) / ((len(tt)/sr) + 1e-6))
            for f in chord:
                snd = np.sin(2 * np.pi * f * tt) * 0.5 + np.sin(2 * np.pi * f * 2 * tt) * 0.1
                mixed[i*seg : min((i+1)*seg, len(t))] += snd * env
        mixed = mixed / (np.max(np.abs(mixed)) + 1e-6) * 0.05
        buf = (mixed * 32767).astype(np.int16)
        stereo = np.column_stack((buf, buf))
        self.sounds['bgm_pokemon'] = pygame.sndarray.make_sound(stereo)

    def _build_sounds(self):
        self._gen_hit()
        self._gen_shoot()
        self._gen_slash()
        self._gen_thud()
        self._gen_jump()
        self._gen_heal()
        self._gen_pokemon_bgm()

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_bgm(self, name):
        if getattr(self, "bgm_channel", None) is None:
            self.bgm_channel = pygame.mixer.Channel(7)
        if name in self.sounds:
            self.bgm_channel.play(self.sounds[name], loops=-1, fade_ms=1000)
            
    def stop_bgm(self):
        if getattr(self, "bgm_channel", None) is not None:
            self.bgm_channel.fadeout(1000)

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

TYPE_EFFECTIVENESS = {
    "grass": {"water": 2.0, "ground": 2.0, "rock": 2.0, "fire": 0.5, "grass": 0.5, "poison": 0.5, "flying": 0.5, "dragon": 0.5, "steel": 0.5},
    "fire": {"grass": 2.0, "ice": 2.0, "bug": 2.0, "steel": 2.0, "fire": 0.5, "water": 0.5, "rock": 0.5, "dragon": 0.5},
    "water": {"fire": 2.0, "ground": 2.0, "rock": 2.0, "water": 0.5, "grass": 0.5, "dragon": 0.5},
    "poison": {"grass": 2.0, "fairy": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0},
    "ground": {"fire": 2.0, "electric": 2.0, "poison": 2.0, "rock": 2.0, "steel": 2.0, "grass": 0.5, "bug": 0.5, "flying": 0.0},
    "flying": {"grass": 2.0, "fighting": 2.0, "bug": 2.0, "electric": 0.5, "rock": 0.5, "steel": 0.5},
    "ice": {"grass": 2.0, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "fire": 0.5, "water": 0.5, "ice": 0.5, "steel": 0.5},
    "dark": {"psychic": 2.0, "ghost": 2.0, "fighting": 0.5, "dark": 0.5, "fairy": 0.5},
    "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "fighting": {"normal": 2.0, "rock": 2.0, "steel": 2.0, "ice": 2.0, "dark": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "fairy": 0.5, "ghost": 0.0},
    "steel": {"ice": 2.0, "rock": 2.0, "fairy": 2.0, "fire": 0.5, "water": 0.5, "electric": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "steel": 0.5, "dark": 0.0},
}

MOVE_TYPE_MAP = {
    "Solar Beam": "grass",
    "Sludge Bomb": "poison",
    "Energy Ball": "grass",
    "Earthquake": "ground",
    "Flamethrower": "fire",
    "Fire Blast": "fire",
    "Air Slash": "flying",
    "Dragon Claw": "dragon",
    "Hydro Pump": "water",
    "Surf": "water",
    "Ice Beam": "ice",
    "Dark Pulse": "dark",
    "Giga Drain": "grass",
    "Body Slam": "normal",
    "Eruption": "fire",
    "Focus Blast": "fighting",
    "Waterfall": "water",
    "Ice Punch": "ice",
    "Crunch": "dark",
    "Leaf Blade": "grass",
    "Dragon Pulse": "dragon",
    "Flare Blitz": "fire",
    "Blaze Kick": "fire",
    "High Jump Kick": "fighting",
    "Brave Bird": "flying",
    "Wood Hammer": "grass",
    "Stone Edge": "rock",
    "Close Combat": "fighting",
    "Mach Punch": "fighting",
    "Flash Cannon": "steel",
    "Leaf Storm": "grass",
    "Heat Crash": "fire",
    "Hammer Arm": "fighting",
    "Wild Charge": "electric",
    "Megahorn": "bug",
    "Drain Punch": "fighting",
    "Psychic": "psychic",
    "Shadow Ball": "ghost",
}

POKEMON_SPRITE_INDEX = {
    "🍃 Venusaur": {"dex": 3, "folders": [("generation-5", "black-white"), ("generation-3", "emerald"), ("generation-1", "yellow")]},
    "🔥 Charizard": {"dex": 6, "folders": [("generation-5", "black-white"), ("generation-3", "emerald"), ("generation-1", "yellow")]},
    "💧 Blastoise": {"dex": 9, "folders": [("generation-5", "black-white"), ("generation-3", "emerald"), ("generation-1", "yellow")]},
    "🌸 Meganium": {"dex": 154, "folders": [("generation-5", "black-white"), ("generation-3", "emerald"), ("generation-2", "crystal")]},
    "🔥 Typhlosion": {"dex": 157, "folders": [("generation-5", "black-white"), ("generation-3", "emerald"), ("generation-2", "crystal")]},
    "💧 Feraligatr": {"dex": 160, "folders": [("generation-5", "black-white"), ("generation-3", "emerald"), ("generation-2", "crystal")]},
    "🍃 Sceptile": {"dex": 254, "folders": [("generation-3", "emerald")]},
    "🔥 Blaziken": {"dex": 257, "folders": [("generation-3", "emerald")]},
    "💧 Swampert": {"dex": 260, "folders": [("generation-3", "emerald")]},
    "🍃 Torterra": {"dex": 389, "folders": [("generation-4", "platinum")]},
    "🔥 Infernape": {"dex": 392, "folders": [("generation-4", "platinum")]},
    "💧 Empoleon": {"dex": 395, "folders": [("generation-4", "platinum")]},
    "🍃 Serperior": {"dex": 497, "folders": [("generation-5", "black-white")]},
    "🔥 Emboar": {"dex": 500, "folders": [("generation-5", "black-white")]},
    "💧 Samurott": {"dex": 503, "folders": [("generation-5", "black-white")]},
    "🍃 Chesnaught": {"dex": 652, "folders": [("gen6", "gen6")]},
    "🔥 Delphox": {"dex": 655, "folders": [("gen6", "gen6")]},
    "💧 Greninja": {"dex": 658, "folders": [("gen6", "gen6")]},
}

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

    def emit_slash(self, x, y, direction, color, size=60, count=12):
        # A semi-circular slash arc
        for i in range(count):
            ang = direction + (i - count//2) * 0.18
            px = x + math.cos(ang) * size
            py = y + math.sin(ang) * size
            self.particles.append(Particle(px, py, math.cos(ang)*50, math.sin(ang)*50, color, 5, 0.4, False))

    def emit_impact(self, x, y, color, count=15, speed=300):
        for _ in range(count):
            ang = random.uniform(0, math.pi*2)
            spd = random.uniform(speed*0.5, speed)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            self.particles.append(Particle(x, y, vx, vy, color, 4, 0.6, True))

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

class PowerUp:
    def __init__(self, x, y, type_name):
        self.x, self.y = float(x), float(y)
        self.type = type_name # "Shield", "Rage", "Speed"
        self.size = 18
        self.alive = True
        self.life = 12.0 # Despawns if not collected
        self.color = BLUE if type_name == "Shield" else RED if type_name == "Rage" else GREEN
        self.bob_timer = 0
        
    def update(self, dt):
        self.life -= dt
        self.bob_timer += dt * 5
        # Subtle floating effect
        return self.life > 0

    def draw(self, screen, font_small):
        # Glow
        glow_size = self.size * 2 + math.sin(pygame.time.get_ticks()*0.01)*5
        glow = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 60), (glow_size, glow_size), glow_size)
        screen.blit(glow, (int(self.x - glow_size), int(self.y - glow_size)))
        
        # Main icon
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.size, 2)
        
        # Symbol
        sym = "S" if self.type == "Shield" else "R" if self.type == "Rage" else "V"
        txt = font_small.render(sym, True, WHITE)
        screen.blit(txt, (int(self.x - txt.get_width()//2), int(self.y - txt.get_height()//2)))

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


class BattlefieldEffect:
    def __init__(self, effect_type, x, y, color, life, **kwargs):
        self.type = effect_type
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.life = float(life)
        self.max_life = float(life)
        self.radius = kwargs.get("radius", 40.0)
        self.owner_team = kwargs.get("owner_team", -1)
        self.damage = kwargs.get("damage", 0.0)
        self.interval = kwargs.get("interval", 0.7)
        self.timer = kwargs.get("timer", self.interval)
        self.secondary = kwargs.get("secondary", WHITE)
        self.angle = kwargs.get("angle", 0.0)
        self.length = kwargs.get("length", 80.0)
        self.shape = kwargs.get("shape")
        self.meta = dict(kwargs)

    def update(self, dt, battle, fighters, projectiles):
        self.life -= dt
        self.angle += dt * self.meta.get("spin", 2.4)
        if self.life <= 0:
            if self.shape is not None and self.shape in battle.space.shapes:
                battle.space.remove(self.shape)
            return False

        self.timer -= dt
        enemy_candidates = [f for f in fighters if f.alive and f.team != self.owner_team]

        if self.type in {"cloud", "field", "vortex", "cage", "swarm", "mine", "ritual", "quake"} and self.timer <= 0:
            self.timer = self.interval
            for f in enemy_candidates:
                dist = math.hypot(f.x - self.x, f.y - self.y)
                if dist <= self.radius:
                    if self.type == "cloud":
                        f.apply_dot(max(8, self.damage * 0.25), 1.5)
                        f.take_damage(self.damage * 0.18, attacker=None)
                    elif self.type == "field":
                        f.take_damage(self.damage * 0.22, attacker=None)
                        f.stun_timer = max(f.stun_timer, 0.35)
                    elif self.type == "vortex":
                        pull = max(60, self.radius - dist)
                        dx = self.x - f.x
                        dy = self.y - f.y
                        d = max(1, math.hypot(dx, dy))
                        f.body.velocity = (f.body.velocity.x + dx / d * pull * 2.0, f.body.velocity.y + dy / d * pull * 2.0)
                        f.take_damage(self.damage * 0.15, attacker=None)
                    elif self.type == "cage":
                        f.take_damage(self.damage * 0.20, attacker=None)
                        f.stun_timer = max(f.stun_timer, 0.6)
                    elif self.type == "mine":
                        battle.particles.emit_ring(self.x, self.y, self.color, count=18, speed=160, size=6)
                        for ff in enemy_candidates:
                            d2 = math.hypot(ff.x - self.x, ff.y - self.y)
                            if d2 <= self.radius * 1.35:
                                kb = max(0.2, 1 - d2 / max(1, self.radius * 1.35))
                                ff.take_damage(self.damage, knockback_x=(ff.x - self.x) * kb * 4, knockback_y=-220 * kb, attacker=None)
                        self.life = min(self.life, 0.05)
                        break
                    elif self.type == "swarm":
                        f.take_damage(self.damage * 0.16, attacker=None)
                        f.apply_dot(max(6, self.damage * 0.18), 1.8)
                    elif self.type == "ritual":
                        f.take_damage(self.damage * 0.24, attacker=None)
                        f.apply_dot(max(8, self.damage * 0.12), 2.2)
                    elif self.type == "quake":
                        falloff = max(0.2, 1.0 - dist / max(1, self.radius))
                        f.take_damage(self.damage * (0.18 + 0.22 * falloff), knockback_x=(f.x - self.x) * 2.2, knockback_y=-180, attacker=None)
                        f.stun_timer = max(f.stun_timer, 0.22 + 0.18 * falloff)
                        f.body.velocity = (f.body.velocity.x * 0.18, f.body.velocity.y * 0.12)

        if self.type == "turret" and self.timer <= 0:
            self.timer = self.interval
            if enemy_candidates:
                target = min(enemy_candidates, key=lambda f: math.hypot(f.x - self.x, f.y - self.y))
                dx = target.x - self.x
                dy = target.y - self.y
                d = max(1, math.hypot(dx, dy))
                spread = random.uniform(-0.12, 0.12)
                angle = math.atan2(dy, dx) + spread
                proj = Projectile(
                    self.x,
                    self.y,
                    math.cos(angle) * 720,
                    math.sin(angle) * 720,
                    max(8, self.damage * 0.35),
                    self.color,
                    5,
                    self.owner_team,
                    self.secondary,
                )
                projectiles.append(proj)
                battle.particles.emit(self.x, self.y, self.secondary, count=6, speed=120, spread=0.3, gravity=False, direction=angle)

        if self.type == "clone" and self.timer <= 0:
            self.timer = self.interval
            if enemy_candidates:
                target = min(enemy_candidates, key=lambda f: math.hypot(f.x - self.x, f.y - self.y))
                angle = math.atan2(target.y - self.y, target.x - self.x)
                proj = Projectile(
                    self.x,
                    self.y,
                    math.cos(angle) * 420,
                    math.sin(angle) * 420,
                    max(8, self.damage * 0.30),
                    self.color,
                    7,
                    self.owner_team,
                    self.secondary,
                    homing=True,
                )
                projectiles.append(proj)
                battle.particles.emit_ring(self.x, self.y, self.color, count=8, speed=70, size=4)

        if self.type == "mothership":
            self.x += math.sin(self.angle * 0.35) * 22 * dt
            if self.timer <= 0:
                self.timer = self.interval
                for _ in range(3):
                    tx = self.meta["target_x"] + random.uniform(-150, 150)
                    proj = Projectile(tx, self.y + 25, 0, 620, max(10, self.damage * 0.22), self.secondary, 9, self.owner_team, self.color, aoe_radius=40)
                    projectiles.append(proj)
        return True

    def draw(self, screen, battle):
        alpha = max(0.0, self.life / self.max_life)
        x = self.x + battle.shake_off()[0]
        y = self.y + battle.shake_off()[1]

        if self.type == "wall":
            if self.shape is not None:
                p1 = (self.shape.a.x + battle.shake_off()[0], self.shape.a.y + battle.shake_off()[1])
                p2 = (self.shape.b.x + battle.shake_off()[0], self.shape.b.y + battle.shake_off()[1])
            else:
                dx = math.cos(self.angle) * self.length
                dy = math.sin(self.angle) * self.length
                p1 = (x - dx, y - dy)
                p2 = (x + dx, y + dy)
            pygame.draw.line(screen, self.color, p1, p2, 12)
            pygame.draw.line(screen, self.secondary, p1, p2, 4)
            return

        if self.type == "turret":
            pygame.draw.circle(screen, self.color, (int(x), int(y)), 18)
            pygame.draw.circle(screen, self.secondary, (int(x), int(y)), 12, 3)
            barrel_x = x + math.cos(self.angle) * 22
            barrel_y = y + math.sin(self.angle) * 22
            pygame.draw.line(screen, self.secondary, (x, y), (barrel_x, barrel_y), 6)
            pygame.draw.circle(screen, (255, 180, 80), (int(barrel_x), int(barrel_y)), 4)
            return

        if self.type == "clone":
            ghost = pygame.Surface((80, 80), pygame.SRCALPHA)
            body = (*self.color, int(90 * alpha))
            accent = (*self.secondary, int(120 * alpha))
            pygame.draw.ellipse(ghost, body, (20, 18, 40, 46))
            pygame.draw.ellipse(ghost, accent, (18, 16, 44, 50), 2)
            pygame.draw.circle(ghost, accent, (48, 32), 4)
            screen.blit(ghost, (x - 40, y - 40))
            return

        if self.type == "quake":
            crack_count = 6
            for i in range(crack_count):
                ang = (math.pi * 2 / crack_count) * i + math.sin(self.angle + i) * 0.15
                length = self.radius * (0.35 + 0.45 * ((i % 3) + 1) / 3)
                end_x = x + math.cos(ang) * length
                end_y = y + math.sin(ang) * length * 0.45
                mid_x = x + math.cos(ang) * length * 0.55 + math.sin(self.angle * 3 + i) * 12
                mid_y = y + math.sin(ang) * length * 0.25 + math.cos(self.angle * 2 + i) * 8
                pygame.draw.line(screen, self.color, (x, y + 8), (mid_x, mid_y), 4)
                pygame.draw.line(screen, self.secondary, (mid_x, mid_y), (end_x, end_y), 2)
            ring_rect = pygame.Rect(x - self.radius, y - self.radius * 0.45, self.radius * 2, self.radius * 0.9)
            pygame.draw.ellipse(screen, (*self.secondary, int(70 * alpha)), ring_rect, 2)
            return

        if self.type in {"cloud", "ritual"}:
            surf = pygame.Surface((int(self.radius * 2.8), int(self.radius * 2.8)), pygame.SRCALPHA)
            center = surf.get_width() // 2
            for i in range(4):
                rad = int(self.radius * (0.55 + i * 0.18))
                pygame.draw.circle(surf, (*self.color, int((40 - i * 6) * alpha)), (center, center), rad)
            if self.type == "ritual":
                pts = []
                for i in range(6):
                    ang = self.angle + i * math.pi / 3
                    pts.append((center + math.cos(ang) * self.radius * 0.9, center + math.sin(ang) * self.radius * 0.9))
                pygame.draw.polygon(surf, (*self.secondary, int(110 * alpha)), pts, 2)
            screen.blit(surf, (x - center, y - center))
            return

        if self.type == "field":
            surf = pygame.Surface((int(self.radius * 3), int(self.radius * 3)), pygame.SRCALPHA)
            center = surf.get_width() // 2
            pygame.draw.circle(surf, (*self.color, int(35 * alpha)), (center, center), int(self.radius))
            pygame.draw.circle(surf, (*self.secondary, int(120 * alpha)), (center, center), int(self.radius), 3)
            for i in range(3):
                ang = self.angle * 1.6 + i * math.pi * 2 / 3
                px = center + math.cos(ang) * self.radius * 0.7
                py = center + math.sin(ang) * self.radius * 0.7
                pygame.draw.circle(surf, (*self.secondary, int(150 * alpha)), (int(px), int(py)), 4)
            screen.blit(surf, (x - center, y - center))
            return

        if self.type == "vortex":
            for i in range(3):
                rad = self.radius * (0.45 + i * 0.28)
                rect = pygame.Rect(0, 0, rad * 2, rad * 1.2)
                rect.center = (x, y)
                start = self.angle + i * 0.6
                pygame.draw.arc(screen, self.color if i % 2 == 0 else self.secondary, rect, start, start + math.pi * 1.3, 3)
            pygame.draw.circle(screen, self.secondary, (int(x), int(y)), max(4, int(self.radius * 0.12)))
            return

        if self.type == "cage":
            for i in range(6):
                ang = self.angle + i * math.pi / 3
                ex = x + math.cos(ang) * self.radius
                ey = y + math.sin(ang) * self.radius
                pygame.draw.line(screen, self.color, (x, y), (ex, ey), 2)
                pygame.draw.circle(screen, self.secondary, (int(ex), int(ey)), 6, 2)
            pygame.draw.circle(screen, self.secondary, (int(x), int(y)), int(self.radius), 2)
            return

        if self.type == "swarm":
            for i in range(10):
                ang = self.angle * (1.2 + i * 0.07) + i * 0.62
                rad = self.radius * (0.45 + (i % 3) * 0.18)
                px = x + math.cos(ang) * rad
                py = y + math.sin(ang) * rad * 0.75
                pygame.draw.circle(screen, self.color if i % 2 == 0 else self.secondary, (int(px), int(py)), 4 if i % 2 == 0 else 3)
            return

        if self.type == "mine":
            pygame.draw.circle(screen, self.color, (int(x), int(y)), 14)
            pygame.draw.circle(screen, self.secondary, (int(x), int(y)), 20, 2)
            for i in range(4):
                ang = self.angle + i * math.pi / 2
                pygame.draw.line(screen, self.secondary, (x, y), (x + math.cos(ang) * 22, y + math.sin(ang) * 22), 2)
            return

        if self.type == "mothership":
            ship = pygame.Rect(0, 0, 90, 28)
            ship.center = (x, y)
            pygame.draw.ellipse(screen, self.color, ship)
            pygame.draw.ellipse(screen, self.secondary, ship, 3)
            pygame.draw.circle(screen, (180, 255, 180), (int(x), int(y - 6)), 10)
            return

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
        "hp": 750,
        "speed": 220,
        "mass": 3.0,
        "size": 18,
        "description": "Heavily armored melee fighter\nHigh HP, slow but deadly at close range",
        "abilities": [
            Ability("Sword Slash",   0.8,  40, 80.0,  GOLD,   "Powerful melee swing"),
            Ability("Shield Bash",   2.0,  60, 60.0,  SILVER, "Knocks enemy back hard"),
            Ability("War Cry",       8.0,  90, 200.0, ORANGE, "AOE shout damages all nearby"),
            Ability("Berserker",    15.0, 200, 90.0,  CRIMSON,"Devastating power attack"),
        ],
        "dodge_rate": 0.1,
        "weapon_type": "sword",
        "has_shield": True
    },
    "🔮 Mage": {
        "color": (100, 80, 220),
        "body_color": (80, 60, 200),
        "hp": 520,
        "speed": 200,
        "mass": 1.8,
        "size": 16,
        "description": "Arcane spellcaster\nLow HP but powerful ranged magic",
        "abilities": [
            Ability("Fireball",     1.0,  28, 500.0, ORANGE, "Explosive fire projectile"),
            Ability("Ice Shard",    0.7,  30, 600.0, CYAN,   "Piercing ice projectile"),
            Ability("Lightning",    1.5,  65, 450.0, YELLOW, "Chain lightning bolt"),
            Ability("Meteor",      12.0, 200, 600.0, RED,    "Massive meteor strike"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🥷 Ninja": {
        "color": (60, 60, 80),
        "body_color": (40, 40, 60),
        "hp": 480,
        "speed": 340,
        "mass": 1.5,
        "size": 15,
        "description": "Shadow assassin\nExtreme speed, teleport, combo attacks",
        "abilities": [
            Ability("Shuriken",     0.5,  20, 500.0, SILVER, "3x rapid shurikens"),
            Ability("Shadow Step",  3.0,  65, 100.0, PURPLE, "Teleport + backstab"),
            Ability("Smoke Bomb",   5.0,  80, 150.0, (100,100,100), "Confuse + area damage"),
            Ability("Death Mark",  10.0, 190, 300.0, CRIMSON,"Guaranteed critical hit"),
        ],
        "dodge_rate": 0.35,
        "weapon_type": "katana",
        "has_shield": False
    },
    "🐉 Dragon": {
        "color": (180, 50, 30),
        "body_color": (140, 30, 20),
        "hp": 900,
        "speed": 180,
        "mass": 4.0,
        "size": 22,
        "description": "Ancient fire dragon\nMassive HP, fire breath, flight",
        "abilities": [
            Ability("Fire Breath",  0.9,  45, 250.0, ORANGE, "Cone of fire particles"),
            Ability("Tail Whip",    1.5,  60, 100.0, BROWN,  "Sweeping tail AOE"),
            Ability("Wing Slam",    4.0,  95, 180.0, RED,    "Shockwave from wings"),
            Ability("Dragon Rage", 14.0, 220, 300.0, CRIMSON,"Full power fire explosion"),
        ],
        "dodge_rate": 0.05,
        "weapon_type": "claws",
        "has_shield": False
    },
    "👿 Demon": {
        "color": (160, 30, 30),
        "body_color": (120, 20, 20),
        "hp": 650,
        "speed": 240,
        "mass": 2.5,
        "size": 19,
        "description": "Hellish demon lord\nLife steal, dark magic, curses",
        "abilities": [
            Ability("Dark Claw",    0.7,  35, 90.0,  CRIMSON,"Life-stealing melee"),
            Ability("Hell Spike",   1.2,  50, 400.0, (150,0,50), "Homing dark projectile"),
            Ability("Soul Drain",   5.0,  85, 200.0, PURPLE, "Drains HP, heals self"),
            Ability("Hellfire",    11.0, 70, 350.0, ORANGE, "Rain of fire pillars"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "trident",
        "has_shield": False
    },
    "🤖 Robot": {
        "color": (100, 130, 160),
        "body_color": (80, 110, 140),
        "hp": 700,
        "speed": 210,
        "mass": 3.5,
        "size": 20,
        "description": "Combat android\nPrecise laser targeting, missiles, shield",
        "abilities": [
            Ability("Laser Beam",   0.6,  25, 600.0, CYAN,   "Precise energy beam"),
            Ability("Missile",      1.5,  60, 700.0, ORANGE, "Homing rocket"),
            Ability("EMP Blast",    6.0,  100, 250.0, BLUE,   "AOE electric pulse"),
            Ability("Overdrive",   13.0, 200, 500.0, YELLOW, "Rapid-fire laser barrage"),
        ],
        "dodge_rate": 0.12
    },
    "🌪️ Elemental": {
        "color": (80, 180, 220),
        "body_color": (60, 160, 200),
        "hp": 580,
        "speed": 260,
        "mass": 1.2,
        "size": 17,
        "description": "Wind & storm spirit\nTornado, lightning storm, levitation",
        "abilities": [
            Ability("Gust",         0.6,  30, 300.0, CYAN,   "Wind pushes enemies back"),
            Ability("Tornado",      2.5,  75, 200.0, TEAL,   "Spinning wind vortex"),
            Ability("Thunderbolt",  1.8,  60, 500.0, YELLOW, "Direct lightning strike"),
            Ability("Storm",       12.0, 195, 400.0, BLUE,   "Full screen storm barrage"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🧛 Vampire": {
        "color": (130, 50, 130),
        "body_color": (100, 30, 100),
        "hp": 600,
        "speed": 250,
        "mass": 2.0,
        "size": 17,
        "description": "Undead bloodsucker\nLife steal, bats, transform into mist",
        "abilities": [
            Ability("Blood Drain",  0.8,  35, 100.0, CRIMSON,"Suck life from enemy"),
            Ability("Bat Swarm",    2.0,  60, 350.0, PURPLE, "Launch swarm of bats"),
            Ability("Mist Form",    5.0,  0, 150.0, (150,150,200), "Phase through attacks"),
            Ability("Drain Life",   9.0, 170, 250.0, PINK,   "Massive HP steal attack"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🏹 Archer": {
        "color": (80, 150, 60),
        "body_color": (60, 120, 40),
        "hp": 500,
        "speed": 280,
        "mass": 1.6,
        "size": 15,
        "description": "Precision marksman\nLong range, rapid shots, explosive arrows",
        "abilities": [
            Ability("Arrow Shot",   0.4,  20, 700.0, LIME,   "Quick precision arrow"),
            Ability("Multi-Shot",   1.5,  55, 650.0, GREEN,  "5 arrows at once"),
            Ability("Poison Arrow", 2.0,  40, 600.0, (100,200,50), "Poison DOT arrow"),
            Ability("Rain of Arrows",10.0,180,500.0, ORANGE, "Arrow storm on target"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "bow",
        "has_shield": False
    },
    "🔱 Poseidon": {
        "color": (30, 100, 200),
        "body_color": (20, 80, 180),
        "hp": 780,
        "speed": 200,
        "mass": 3.0,
        "size": 20,
        "description": "God of the seas\nWater waves, trident attacks, tidal force",
        "abilities": [
            Ability("Trident",      0.9,  45, 150.0, BLUE,   "Powerful trident thrust"),
            Ability("Water Blast",  1.3,  55, 450.0, CYAN,   "High-pressure water shot"),
            Ability("Tidal Wave",   5.0, 100, 300.0, BLUE,   "Sweeping wave knockback"),
            Ability("Maelstrom",   13.0, 210, 400.0, TEAL,   "Massive water vortex"),
        ],
        "dodge_rate": 0.12,
        "weapon_type": "trident",
        "has_shield": False
    },
    "🕸️ Web-Slinger": {
        "color": (200, 30, 30),
        "body_color": (30, 50, 200),
        "hp": 560,
        "speed": 320,
        "mass": 1.8,
        "size": 16,
        "description": "Web-swinging hero\nHigh mobility, stuns, and rapid melee",
        "abilities": [
            Ability("Web Shot",     0.6,  25, 500.0, WHITE,  "Stuns enemy with webs"),
            Ability("Web Swing",    2.5,  70, 400.0, BLUE,   "Dashing kick attack"),
            Ability("Spider-Sense", 6.0,  85, 150.0, RED,    "Quick dodge & counter"),
            Ability("Web Barrage", 12.0, 195, 500.0, WHITE,  "Multiple webs trap all"),
        ],
        "dodge_rate": 0.3
    },
    "🚀 Tech-Armor": {
        "color": (200, 50, 50),
        "body_color": (220, 200, 50),
        "hp": 680,
        "speed": 230,
        "mass": 2.8,
        "size": 18,
        "description": "High-tech armored suit\nEnergy beams, missiles, and flight",
        "abilities": [
            Ability("Repulsor",    0.7,  35, 550.0, CYAN,   "Energy blast from palm"),
            Ability("Mini-Missile", 1.8,  70, 650.0, ORANGE, "Homing mini-rockets"),
            Ability("Uni-Beam",     7.0, 110, 700.0, WHITE,  "Massive chest laser"),
            Ability("Rocket Barrage", 14.0, 210, 500.0, RED, "Full weapon discharge"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🟢 Gamma-Giant": {
        "color": (50, 180, 50),
        "body_color": (120, 50, 180),
        "hp": 1000,
        "speed": 160,
        "mass": 5.0,
        "size": 25,
        "description": "Unstoppable force\nHuge HP, massive smash damage",
        "abilities": [
            Ability("Smash",        1.0,  60, 100.0, GREEN,  "Powerful ground punch"),
            Ability("Gamma Leap",   3.0,  80, 300.0, LIME,   "Jumps and lands hard"),
            Ability("Thunderclap",  5.0,  100, 250.0, WHITE,  "Shockwave stuns nearby"),
            Ability("Hulk Rage",   15.0, 220, 350.0, RED,    "Devastating multi-smash"),
        ],
        "dodge_rate": 0.03,
        "weapon_type": "fists",
        "has_shield": False
    },
    "⚡ Thunder-God": {
        "color": (100, 200, 255),
        "body_color": (180, 180, 200),
        "hp": 820,
        "speed": 190,
        "mass": 3.5,
        "size": 20,
        "description": "God of Thunder\nLightning strikes & Mjolnir throws",
        "abilities": [
            Ability("Hammer Throw", 0.9,  45, 600.0, SILVER, "Mjolnir flies and returns"),
            Ability("Lightning",    1.5,  65, 450.0, YELLOW, "Call down a bolt"),
            Ability("Shockwave",    4.0,  95, 200.0, CYAN,   "Hammer slam AOE"),
            Ability("God Blast",   13.0, 205, 500.0, WHITE,  "Ultimate lightning storm"),
        ],
        "dodge_rate": 0.1,
        "weapon_type": "hammer",
        "has_shield": False
    },
    "🛡️ Star-Soldier": {
        "color": (30, 80, 200),
        "body_color": (200, 30, 30),
        "hp": 760,
        "speed": 250,
        "mass": 2.5,
        "size": 18,
        "description": "Peak human soldier\nMaster of shield combat & defense",
        "abilities": [
            Ability("Shield Toss",  1.0,  40, 550.0, SILVER, "Ricochet shield attack"),
            Ability("Combat Combo", 0.7,  30, 90.0,  BLUE,   "Rapid martial arts"),
            Ability("Shield Charge",3.0,  75, 250.0, WHITE,  "Unstoppable dash bash"),
            Ability("Final Stand", 12.0, 195, 300.0, RED,    "Heroic series of blows"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "shield_only",
        "has_shield": True
    },
    "🐾 Jungle-King": {
        "color": (40, 40, 40),
        "body_color": (150, 120, 255),
        "hp": 650,
        "speed": 310,
        "mass": 2.0,
        "size": 17,
        "description": "Vibranium-enhanced warrior\nFast claws & kinetic energy",
        "abilities": [
            Ability("Claw Slash",   0.6,  30, 80.0,  PURPLE, "Quick vibranium slashes"),
            Ability("Pounce",       2.5,  70, 300.0, DARK_BG,"Lunging leap attack"),
            Ability("Kinetic Burst",6.0,  105, 220.0, PINK,   "Releases stored energy"),
            Ability("Panther Hunt",11.0, 190, 400.0, SILVER, "Stealthy rapid strikes"),
        ],
        "dodge_rate": 0.3,
        "weapon_type": "claws",
        "has_shield": False
    },
    "🧪 Toxic-Widow": {
        "color": (30, 30, 30),
        "body_color": (200, 30, 30),
        "hp": 520,
        "speed": 290,
        "mass": 1.6,
        "size": 16,
        "description": "Master spy\nVenom blasts & acrobatic combat",
        "abilities": [
            Ability("Widow Sting",  0.7,  30, 400.0, CYAN,   "Electric wrist blast"),
            Ability("Toxic Mine",   3.5,  55, 300.0, GREEN,  "Poison gas trap"),
            Ability("Acrobat Strike",2.0, 50, 120.0, RED,    "Spinning kick combo"),
            Ability("Assassination",10.0, 185, 350.0, SILVER, "Precise lethal strike"),
        ],
        "dodge_rate": 0.32,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🏹 Hawk-Arrow": {
        "color": (100, 30, 150),
        "body_color": (50, 50, 100),
        "hp": 510,
        "speed": 280,
        "mass": 1.6,
        "size": 15,
        "description": "Grandmaster archer\nVariety of trick arrows",
        "abilities": [
            Ability("Sonic Arrow",  1.0,  40, 600.0, WHITE,  "Stuns with high sound"),
            Ability("Exploding Tip",1.8,  75, 650.0, ORANGE, "Massive AOE arrow"),
            Ability("Electric Arrow",2.5, 55, 550.0, YELLOW, "Chain lightning effect"),
            Ability("Barrage",     12.0, 195, 500.0, PURPLE, "Rain of 20 arrows"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "bow",
        "has_shield": False
    },
    "🌀 Sorcerer-Lord": {
        "color": (200, 50, 30),
        "body_color": (30, 50, 150),
        "hp": 530,
        "speed": 210,
        "mass": 1.7,
        "size": 16,
        "description": "Master of mystic arts\nShields, portals, and spells",
        "abilities": [
            Ability("Mystic Bolt",  0.8,  40, 500.0, GOLD,   "Arcane energy blast"),
            Ability("Portal Warp",  4.0,  85, 400.0, ORANGE, "Teleport and strike"),
            Ability("Eldritch Whip",1.5,  50, 250.0, RED,    "Energy whip pull"),
            Ability("Mirror Realm",14.0, 205, 600.0, PURPLE, "Bends space for damage"),
        ],
        "dodge_rate": 0.18,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🐜 Size-Shifter": {
        "color": (200, 30, 30),
        "body_color": (40, 40, 40),
        "hp": 580,
        "speed": 260,
        "mass": 1.8,
        "size": 16,
        "description": "Pym particle user\nShrink to dodge, grow to smash",
        "abilities": [
            Ability("Shrink Punch", 0.6,  25, 400.0, RED,    "Tiny but fast punch"),
            Ability("Ant Swarm",    3.0,  70, 350.0, BLACK,  "Summons biting ants"),
            Ability("Giant Stomp",  8.0, 140, 300.0, SILVER, "Grows huge & crushes"),
            Ability("Disk Throw",  10.0, 175, 500.0, BLUE,   "Enlarges objects to hit"),
        ],
        "dodge_rate": 0.35,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🌪️ Weather-Soul": {
        "color": (255, 255, 255),
        "body_color": (30, 30, 80),
        "hp": 580,
        "speed": 240,
        "mass": 1.5,
        "size": 17,
        "description": "Elemental goddess\nControls wind, rain, & lighting",
        "abilities": [
            Ability("Wind Gust",    0.8,  30, 450.0, CYAN,   "Pushes enemies away"),
            Ability("Hail Storm",   3.0,  80, 500.0, WHITE,  "Raining ice chunks"),
            Ability("Thunderbolt",  1.5,  60, 550.0, YELLOW, "Direct precise strike"),
            Ability("Hurricane",   13.0, 200, 600.0, BLUE,   "Total screen storm"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "staff",
        "has_shield": False
    },
    "🕶️ Optic-Hero": {
        "color": (50, 50, 200),
        "body_color": (200, 180, 50),
        "hp": 600,
        "speed": 220,
        "mass": 2.0,
        "size": 18,
        "description": "Field leader\nContinuous optic concussive beams",
        "abilities": [
            Ability("Optic Blast",  0.5,  22, 700.0, RED,    "Fast concussive beam"),
            Ability("Wide Beam",    2.5,  75, 500.0, RED,    "Wide area blast"),
            Ability("Ricochet",     1.8,  50, 600.0, CRIMSON,"Bouncing beam shot"),
            Ability("Full Power",  12.0, 210, 800.0, WHITE,  "Destructive mega beam"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🐱 Feral-Claw": {
        "color": (220, 160, 50),
        "body_color": (30, 50, 150),
        "hp": 720,
        "speed": 280,
        "mass": 2.2,
        "size": 17,
        "description": "Mutant with healing factor\nAdamantium claws & berserker rage",
        "abilities": [
            Ability("X-Slash",      0.5,  30, 80.0,  SILVER, "Fast claw cross-cut"),
            Ability("Lunge",        2.0,  65, 250.0, BROWN,  "Lunging slash attack"),
            Ability("Regenerate",   7.0,  0,  0.0,   GREEN,  "Heals significant HP"),
            Ability("Berserker",   14.0, 200, 150.0, RED,    "Unstoppable claw flurry"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "claws",
        "has_shield": False
    },
    "🃏 Mischief-Loki": {
        "color": (50, 150, 50),
        "body_color": (200, 180, 50),
        "hp": 560,
        "speed": 250,
        "mass": 2.0,
        "size": 17,
        "description": "God of Mischief\nClones, illusions, and daggers",
        "abilities": [
            Ability("Dagger Throw", 0.6,  30, 500.0, SILVER, "Quick throw daggers"),
            Ability("Illusion",     4.0,  20, 200.0, GREEN,  "Clones distract enemy"),
            Ability("Scepter Blast",1.8,  60, 450.0, BLUE,   "Mind stone energy shot"),
            Ability("Trickery",    12.0, 185, 400.0, PURPLE, "Massive illusion strike"),
        ],
        "dodge_rate": 0.38,
        "weapon_type": "katana",
        "has_shield": False
    },
    "💀 Ghost-Biker": {
        "color": (200, 80, 30),
        "body_color": (20, 20, 20),
        "hp": 700,
        "speed": 260,
        "mass": 2.8,
        "size": 19,
        "description": "Spirit of Vengeance\nHellfire chains & hellcycle",
        "abilities": [
            Ability("Hell-Chain",   0.8,  40, 400.0, ORANGE, "Flame chain whip"),
            Ability("Penance Gaze", 5.0, 90, 150.0, RED,    "Stuns and burns"),
            Ability("Hellfire",     2.5,  70, 350.0, CRIMSON,"AOE fire explosion"),
            Ability("Hell-Cycle",  13.0, 200, 500.0, ORANGE, "Flaming bike charge"),
        ],
        "dodge_rate": 0.1,
        "weapon_type": "chain",
        "has_shield": False
    },
    "🌳 Forest-Giant": {
        "color": (80, 150, 60),
        "body_color": (120, 90, 50),
        "hp": 900,
        "speed": 170,
        "mass": 4.5,
        "size": 23,
        "description": "Sentient tree warrior\nRegeneration & vine attacks",
        "abilities": [
            Ability("Vine Smash",   1.0,  50, 120.0, GREEN,  "Lashing vine sweep"),
            Ability("Root Trap",    3.5,  40, 400.0, BROWN,  "Enemies can't move"),
            Ability("Spore Heal",   8.0,  0,  0.0,   LIME,   "Healing spores"),
            Ability("Tree Grow",   14.0, 210, 300.0, GREEN,  "Massive growth smash"),
        ],
        "dodge_rate": 0.04,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🦝 Space-Raccoon": {
        "color": (100, 80, 60),
        "body_color": (50, 100, 200),
        "hp": 520,
        "speed": 270,
        "mass": 1.4,
        "size": 14,
        "description": "Ordnance expert\nHeavy weapons & explosives",
        "abilities": [
            Ability("Blaster",      0.5,  22, 600.0, ORANGE, "Rapid laser fire"),
            Ability("Sticky Grenade",2.0, 70, 450.0, RED,    "Delayed explosion"),
            Ability("Machine Gun",  5.0, 100, 550.0, YELLOW, "Hail of bullets"),
            Ability("The Big One", 14.0, 210, 650.0, WHITE,  "Massive experimental bomb"),
        ],
        "dodge_rate": 0.3,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🌟 Cosmic-Nova": {
        "color": (255, 255, 100),
        "body_color": (50, 80, 200),
        "hp": 660,
        "speed": 250,
        "mass": 2.5,
        "size": 18,
        "description": "Cosmic powerhouse\nEnergy blasts & flight",
        "abilities": [
            Ability("Photon Blast", 0.7,  40, 550.0, YELLOW, "Concentrated energy"),
            Ability("Cosmic Dash",  2.5,  65, 350.0, CYAN,   "High-speed tackle"),
            Ability("Energy Shield",6.0,  0, 100.0, WHITE,  "Temporary invincibility"),
            Ability("Binary Power",13.0, 205, 500.0, GOLD,   "Full cosmic release"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "fists",
        "has_shield": True
    },
    "🔱 Trident-Hero": {
        "color": (0, 150, 150),
        "body_color": (200, 150, 50),
        "hp": 740,
        "speed": 230,
        "mass": 3.0,
        "size": 20,
        "description": "King of the deep\nWater control & trident master",
        "abilities": [
            Ability("Trident Stab", 0.8,  40, 100.0, SILVER, "Quick triple thrust"),
            Ability("Water Wave",   2.5,  70, 400.0, BLUE,   "Tidal surge push"),
            Ability("Shark Call",   6.0,  90, 450.0, TEAL,   "Summons a spectral shark"),
            Ability("Ocean Wrath", 12.0, 200, 500.0, BLUE,   "Massive whirlpool"),
        ],
        "weapon_type": "trident",
        "has_shield": False
    },
    "🦇 Dark-Hero": {
        "color": (20, 20, 20),
        "body_color": (80, 80, 80),
        "hp": 640,
        "speed": 280,
        "mass": 2.2,
        "size": 18,
        "description": "Detective & vigilante\nGadgets and martial arts",
        "abilities": [
            Ability("Batarang",     0.6,  28, 500.0, SILVER, "Quick throwing weapon"),
            Ability("Smoke Pellets",4.0,  20, 200.0, (100,100,100), "Confuses enemies"),
            Ability("Grapple Kick", 2.5,  65, 350.0, BLACK,  "Pull and kick combo"),
            Ability("The Knight",  12.0, 185, 400.0, DARK_BG,"Perfect combat series"),
        ],
        "dodge_rate": 0.3,
        "weapon_type": "katana",
        "has_shield": False
    },
    "🏃 Sonic-Speed": {
        "color": (220, 30, 30),
        "body_color": (255, 255, 100),
        "hp": 480,
        "speed": 450,
        "mass": 1.5,
        "size": 16,
        "description": "Fastest man alive\nExtreme speed & sonic booms",
        "abilities": [
            Ability("Speed Punch",  0.4,  18, 100.0, YELLOW, "Ultra-fast punches"),
            Ability("Sonic Boom",   3.0,  70, 300.0, WHITE,  "Dash creates shockwave"),
            Ability("Lightning Rim",6.0,  90, 400.0, BLUE,   "Circular speed attack"),
            Ability("Infinite Mass",14.0, 210, 200.0, GOLD,  "The ultimate punch"),
        ],
        "dodge_rate": 0.4
    },
    "🦅 Wing-Soldier": {
        "color": (200, 30, 30),
        "body_color": (150, 150, 150),
        "hp": 620,
        "speed": 340,
        "mass": 2.0,
        "size": 17,
        "description": "Aerial combatant\nWings & tactical drones",
        "abilities": [
            Ability("Wing Slash",   0.7,  32, 150.0, SILVER, "Blade-wing strike"),
            Ability("Redwing",      3.0,  65, 500.0, RED,    "Support drone laser"),
            Ability("Dive Bomb",    4.0,  80, 400.0, DARK_BG,"Diving tackle"),
            Ability("Air Strike",  11.0, 190, 500.0, WHITE,  "Full aerial assault"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "katana",
        "has_shield": False
    },
    "🧚 Wasp-Hero": {
        "color": (220, 200, 30),
        "body_color": (30, 30, 30),
        "hp": 480,
        "speed": 360,
        "mass": 1.2,
        "size": 14,
        "description": "Miniature fighter\nBio-stings & rapid flight",
        "abilities": [
            Ability("Bio-Sting",    0.5,  20, 450.0, YELLOW, "Rapid energy stingers"),
            Ability("Swarm",        3.5,  65, 300.0, GOLD,   "Dashing multiple hits"),
            Ability("Tiny Fury",    6.0,  85, 200.0, WHITE,  "Frenzy of small attacks"),
            Ability("Stinger Rain",12.0, 185, 500.0, YELLOW, "Massive sting barrage"),
        ],
        "dodge_rate": 0.45,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🧱 Rock-Tank": {
        "color": (150, 100, 80),
        "body_color": (100, 80, 60),
        "hp": 980,
        "speed": 180,
        "mass": 4.8,
        "size": 24,
        "description": "Solid stone hero\nIncredible defense & strength",
        "abilities": [
            Ability("Stone Fist",   1.0,  55, 100.0, BROWN,  "Heavy rock punch"),
            Ability("Clobberin Time",3.5, 90, 150.0, ORANGE, "Massive impact strike"),
            Ability("Earthquake",   6.0,  100, 350.0, SILVER, "Stuns nearby enemies"),
            Ability("Boulder Throw",12.0, 215, 600.0, BROWN,  "Yeets a huge rock"),
        ],
        "dodge_rate": 0.03,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🔥 Fire-Burst": {
        "color": (255, 100, 30),
        "body_color": (255, 230, 50),
        "hp": 560,
        "speed": 270,
        "mass": 1.6,
        "size": 16,
        "description": "Living flame\nFire manipulation & flight",
        "abilities": [
            Ability("Flame On",     1.0,  30, 300.0, ORANGE, "Passive burn damage"),
            Ability("Fireball",     0.8,  28, 500.0, RED,    "Projected fire"),
            Ability("Nova Blast",   7.0, 105, 400.0, GOLD,   "Explosive fire release"),
            Ability("Supernova",   15.0, 215, 600.0, WHITE,  "Full power explosion"),
        ],
        "dodge_rate": 0.2,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🧞 Genie-Magic": {
        "color": (80, 180, 255),
        "body_color": (200, 150, 50),
        "hp": 620,
        "speed": 220,
        "mass": 2.0,
        "size": 18,
        "description": "Cosmic genie\nWishes and magic smoke",
        "abilities": [
            Ability("Magic Lamp",   0.9,  38, 450.0, GOLD,   "Blasts magic smoke"),
            Ability("Giant Hands",  3.0,  80, 200.0, CYAN,   "Smack from above"),
            Ability("Wish Grant",   8.0,  0,  0.0,   PINK,   "Random buff/heal"),
            Ability("Phenomenal",  13.0, 200, 500.0, PURPLE, "Ultimate magic show"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🧟 Plague-Walker": {
        "color": (150, 180, 100),
        "body_color": (80, 100, 60),
        "hp": 700,
        "speed": 150,
        "mass": 2.5,
        "size": 18,
        "description": "Undead plague\nInfects and survives",
        "abilities": [
            Ability("Bite",         0.7,  30, 80.0,  LIME,   "Infects with poison"),
            Ability("Vomit",        2.5,  65, 300.0, GREEN,  "Acid splash DOT"),
            Ability("Horde Call",   6.0,  90, 400.0, BROWN,  "Summons small zombies"),
            Ability("Undead Rage", 12.0, 195, 250.0, RED,    "Frenzy of bites"),
        ],
        "dodge_rate": 0.05,
        "weapon_type": "fists",
        "has_shield": False
    },
    "🛸 Void-Traveler": {
        "color": (100, 255, 200),
        "body_color": (40, 60, 100),
        "hp": 610,
        "speed": 230,
        "mass": 1.8,
        "size": 17,
        "description": "Alien voyager\nAdvanced tech and beams",
        "abilities": [
            Ability("Ray Gun",      0.6,  28, 550.0, CYAN,   "Plasma energy shot"),
            Ability("Abduction",    4.0,  80, 300.0, WHITE,  "Lifts enemy up"),
            Ability("Gravity Bomb", 5.0,  95, 400.0, PURPLE, "Crushes with gravity"),
            Ability("Mothership",  13.0, 205, 600.0, LIME,   "Full ship bombardment"),
        ],
        "dodge_rate": 0.18,
        "weapon_type": "blaster",
        "has_shield": False
    },
    "🏴‍☠️ Pirate-King": {
        "color": (160, 30, 30),
        "body_color": (50, 40, 40),
        "hp": 700,
        "speed": 240,
        "mass": 2.4,
        "size": 18,
        "description": "King of the seas\nCannons and scimitar",
        "abilities": [
            Ability("Scimitar",     0.7,  35, 90.0,  SILVER, "Masterful sword cut"),
            Ability("Pistol Shot",  1.5,  55, 500.0, DARK_BG,"Lead bullet shot"),
            Ability("Cannonade",    5.0,  95, 550.0, BLACK,  "Fire the ship's big gun"),
            Ability("Kraken",      14.0, 210, 450.0, BLUE,   "Summons the beast"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "sword",
        "has_shield": False
    },
    "🤺 Shadow-Knight": {
        "color": (60, 60, 70),
        "body_color": (40, 40, 50),
        "hp": 640,
        "speed": 300,
        "mass": 1.9,
        "size": 17,
        "description": "Cursed ronin\nShadow blades & speed",
        "abilities": [
            Ability("Shadow Slash", 0.5,  28, 90.0,  PURPLE, "Ultra-fast cut"),
            Ability("Dark Dash",    2.5,  70, 350.0, BLACK,  "Phases through enemy"),
            Ability("Soul Reaper",  6.0,  100, 150.0, CRIMSON,"Health drain strike"),
            Ability("Nightfall",   12.0, 200, 500.0, TEAL,   "Total darkness flurry"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "katana",
        "has_shield": False
    },

    # ═══════════════════════════════════════════
    # NEW SPECIAL CHARACTERS
    # ═══════════════════════════════════════════

    "👁️ Phantom": {
        "color": (180, 100, 255),
        "body_color": (100, 40, 180),
        "hp": 520,
        "speed": 300,
        "mass": 1.4,
        "size": 16,
        "description": "Interdimensional ghost\nTeleports constantly, phases through reality",
        "abilities": [
            Ability("Phase Blink",   0.6,  25, 400, PURPLE, "Teleports behind enemy and strikes"),
            Ability("Ghost Strike",  1.8,  65, 300, (180,100,255), "Phases through defenses"),
            Ability("Void Step",     4.0,  85, 500, (100,0,200), "Multi-blink confusion attack"),
            Ability("Phantom Surge",12.0, 200, 350, WHITE,  "Reality-shattering teleport barrage"),
        ],
        "dodge_rate": 0.40,
        "weapon_type": "katana",
        "has_shield": False
    },

    "⏰ Time-Lord": {
        "color": (200, 180, 50),
        "body_color": (80, 60, 20),
        "hp": 580,
        "speed": 220,
        "mass": 1.8,
        "size": 17,
        "description": "Master of time and space\nSlows enemies, rewinds self",
        "abilities": [
            Ability("Time Bolt",     0.8,  35, 500, GOLD,   "Temporal projectile"),
            Ability("Slow Field",    3.0,  55, 300, YELLOW, "Slows enemy in time bubble"),
            Ability("Rewind",        6.0,   0,   0, CYAN,   "Rewinds own HP to 10s ago"),
            Ability("Timestop",     13.0, 205, 400, WHITE,  "Freezes enemy, then massive hit"),
        ],
        "dodge_rate": 0.18,
        "weapon_type": "staff",
        "has_shield": False
    },

    "💀 Necromancer": {
        "color": (80, 200, 80),
        "body_color": (30, 50, 30),
        "hp": 500,
        "speed": 190,
        "mass": 1.9,
        "size": 16,
        "description": "Master of undeath\nRaises fallen, curses enemies",
        "abilities": [
            Ability("Cursed Bolt",   0.8,  30, 450, (80,200,80), "Spreading curse projectile"),
            Ability("Death Touch",   2.5,  70, 100, (50,150,50), "Rotting melee strike"),
            Ability("Plague Cloud",  5.0,  90, 300, LIME,   "Toxic AOE cloud"),
            Ability("Army of Dead", 14.0, 210, 500, (100,255,100), "Summons bone barrage"),
        ],
        "dodge_rate": 0.15,
        "weapon_type": "staff",
        "has_shield": False
    },

    "🪞 Mirror-Mage": {
        "color": (200, 220, 255),
        "body_color": (100, 120, 200),
        "hp": 540,
        "speed": 210,
        "mass": 1.7,
        "size": 16,
        "description": "Reality reflector\nReflects damage, creates clones",
        "abilities": [
            Ability("Mirror Shard", 0.7,  30, 500, (200,220,255), "Bouncing mirror projectile"),
            Ability("Reflect",      3.0,  55, 200, WHITE,  "Reflects next attack back"),
            Ability("Clone Army",   6.0,  80, 300, SILVER, "3 mirror clones distract enemy"),
            Ability("Prism Burst", 12.0, 200, 500, WHITE,  "Shatters into blinding shards"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "staff",
        "has_shield": False
    },

    "🌑 Black-Hole": {
        "color": (50, 0, 80),
        "body_color": (20, 0, 40),
        "hp": 620,
        "speed": 180,
        "mass": 3.0,
        "size": 19,
        "description": "Singularity incarnate\nPulls enemies in, crushes with gravity",
        "abilities": [
            Ability("Gravity Pull", 0.9,  35, 450, (100,0,150), "Yanks enemy toward self"),
            Ability("Event Horizon",2.5,  70, 300, PURPLE, "Gravity well circles self"),
            Ability("Dark Matter",  5.0,  95, 400, (50,0,80),  "Dense energy bomb"),
            Ability("Singularity", 14.0, 215, 500, BLACK,  "Collapse — massive gravity crush"),
        ],
        "dodge_rate": 0.10,
        "weapon_type": "fists",
        "has_shield": False
    },

    "⚗️ Alchemist": {
        "color": (200, 150, 30),
        "body_color": (100, 60, 20),
        "hp": 560,
        "speed": 210,
        "mass": 1.9,
        "size": 17,
        "description": "Potion-flinging scientist\nPoisons, explosions, transmutation",
        "abilities": [
            Ability("Acid Flask",    0.7,  30, 450, (150,200,50), "Splashes poison acid"),
            Ability("Fire Potion",   1.5,  60, 500, ORANGE, "Explosive fire vial"),
            Ability("Transmute",     5.0,  85, 200, GOLD,   "Turns enemy weak temporarily"),
            Ability("Grand Elixir", 13.0, 205, 400, PURPLE, "Ultimate multi-element bomb"),
        ],
        "dodge_rate": 0.17,
        "weapon_type": "blaster",
        "has_shield": False
    },

    "🧲 Magnetar": {
        "color": (100, 200, 255),
        "body_color": (50, 80, 150),
        "hp": 640,
        "speed": 210,
        "mass": 2.5,
        "size": 18,
        "description": "Magnetic powerhouse\nAttracts and repels with massive force",
        "abilities": [
            Ability("Magnetic Pull", 0.8,  30, 400, BLUE,   "Pulls enemy violently close"),
            Ability("Repulse Blast", 1.8,  60, 300, CYAN,   "Blasts enemy far away"),
            Ability("Iron Storm",    5.0,  90, 450, SILVER, "Magnetic shrapnel barrage"),
            Ability("Polarity Flip",13.0, 210, 500, WHITE,  "Massive EM pulse reversal"),
        ],
        "dodge_rate": 0.13,
        "weapon_type": "fists",
        "has_shield": False
    },

    "🌊 Tsunami": {
        "color": (0, 150, 220),
        "body_color": (0, 80, 150),
        "hp": 700,
        "speed": 200,
        "mass": 2.8,
        "size": 19,
        "description": "Living tidal force\nCrashes into foes with wall of water",
        "abilities": [
            Ability("Water Jet",     0.7,  28, 500, BLUE,   "High-pressure water beam"),
            Ability("Riptide",       2.0,  65, 350, CYAN,   "Sweeping current slash"),
            Ability("Wave Crash",    4.0,  95, 300, BLUE,   "Wall of water smash"),
            Ability("Mega Tsunami", 13.0, 210, 500, (0,100,200), "Arena-wide tidal surge"),
        ],
        "dodge_rate": 0.12,
        "weapon_type": "staff",
        "has_shield": False
    },

    "🎯 Bounty-Hunter": {
        "color": (150, 120, 50),
        "body_color": (80, 60, 20),
        "hp": 600,
        "speed": 260,
        "mass": 2.0,
        "size": 17,
        "description": "Ruthless tracker\nMarks targets, traps, and precision shots",
        "abilities": [
            Ability("Stun Dart",     0.6,  22, 600, BROWN,  "Fast blowgun dart"),
            Ability("Trip Mine",     2.5,  75, 350, ORANGE, "Proximity explosive trap"),
            Ability("Headshot",      3.5,  95, 700, SILVER, "Pinpoint lethal shot"),
            Ability("Obliterate",   12.0, 205, 600, RED,    "Full arsenal discharge"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "blaster",
        "has_shield": False
    },

    "🔮 Crystal-Witch": {
        "color": (180, 80, 220),
        "body_color": (100, 30, 140),
        "hp": 490,
        "speed": 215,
        "mass": 1.6,
        "size": 15,
        "description": "Dark crystal magic\nCrystal spikes, hexes, and curses",
        "abilities": [
            Ability("Crystal Bolt", 0.7,  28, 480, (180,80,220), "Piercing crystal shard"),
            Ability("Hex Curse",    2.5,  60, 300, PINK,   "Weakens enemy defenses"),
            Ability("Crystal Cage", 5.0,  85, 350, PURPLE, "Traps enemy in crystal"),
            Ability("Dark Ritual", 13.0, 205, 400, (100,0,150), "Sacrifices HP for massive blast"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "staff",
        "has_shield": False
    },

    "🌋 Lava-Titan": {
        "color": (220, 80, 20),
        "body_color": (100, 30, 10),
        "hp": 920,
        "speed": 165,
        "mass": 4.5,
        "size": 23,
        "description": "Molten behemoth\nLeaves lava trails, erupts in fire",
        "abilities": [
            Ability("Lava Fist",     1.0,  55, 100, ORANGE, "Burning melee strike"),
            Ability("Magma Hurl",    2.0,  70, 450, RED,    "Lobs molten rock"),
            Ability("Eruption",      6.0, 110, 300, GOLD,   "Volcanic AOE explosion"),
            Ability("Caldera",      14.0, 215, 500, (220,80,20), "Total volcanic release"),
        ],
        "dodge_rate": 0.04,
        "weapon_type": "fists",
        "has_shield": False
    },

    "🦋 Psionic": {
        "color": (180, 100, 220),
        "body_color": (220, 150, 255),
        "hp": 490,
        "speed": 250,
        "mass": 1.5,
        "size": 15,
        "description": "Telekinetic mind warrior\nMoves enemies with thought alone",
        "abilities": [
            Ability("Mind Bolt",     0.6,  22, 500, PINK,   "Psychic energy shot"),
            Ability("Telekinesis",   2.0,  65, 400, (180,100,220), "Hurls enemy across arena"),
            Ability("Mind Crush",    4.5,  90, 350, PURPLE, "Psychic implosion"),
            Ability("Psionic Storm",13.0, 200, 600, WHITE,  "Telepathic barrage of pain"),
        ],
        "dodge_rate": 0.30,
        "weapon_type": "staff",
        "has_shield": False
    },

    "🐺 Werewolf": {
        "color": (140, 110, 80),
        "body_color": (80, 60, 40),
        "hp": 680,
        "speed": 310,
        "mass": 2.2,
        "size": 18,
        "description": "Moon-cursed beast\nFeral speed, howl, regenerates",
        "abilities": [
            Ability("Rend",          0.5,  25, 90,  BROWN,  "Brutal claw tear"),
            Ability("Pounce",        2.0,  70, 300, (140,110,80), "Leaping lunge attack"),
            Ability("Howl",          5.0,  30, 250, WHITE,  "Intimidating AOE roar"),
            Ability("Full Moon Rage",12.0, 205, 200, SILVER, "Unstoppable bestial frenzy"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "claws",
        "has_shield": False
    },

    "⚡ Stormborn": {
        "color": (100, 180, 255),
        "body_color": (30, 60, 120),
        "hp": 540,
        "speed": 290,
        "mass": 1.6,
        "size": 16,
        "description": "Born from lightning\nElectric dashes, charge attacks",
        "abilities": [
            Ability("Spark Shot",    0.5,  22, 550, YELLOW, "Fast electric bolt"),
            Ability("Thunder Dash",  2.0,  65, 350, CYAN,   "Lightning speed charge"),
            Ability("Ball Lightning",4.0,  90, 400, WHITE,  "Bouncing electric orb"),
            Ability("Supercell",    12.0, 200, 500, (100,180,255), "Massive storm discharge"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "blaster",
        "has_shield": False
    },

    "🏯 Samurai": {
        "color": (220, 180, 100),
        "body_color": (50, 50, 80),
        "hp": 660,
        "speed": 270,
        "mass": 2.1,
        "size": 17,
        "description": "Honorable blade master\nPerfect counters and iaijutsu",
        "abilities": [
            Ability("Iai Strike",    0.5,  28, 150, SILVER, "Lightning-fast draw cut"),
            Ability("Parry",         3.0,  70, 100, GOLD,   "Deflects attack and counters"),
            Ability("Blade Storm",   4.5,  95, 200, (220,180,100), "Spinning sword hurricane"),
            Ability("Seppuku Edge", 13.0, 210, 300, CRIMSON,"Ultimate sacrificial slash"),
        ],
        "dodge_rate": 0.30,
        "weapon_type": "katana",
        "has_shield": False
    },

    "🔫 Gunsmith": {
        "color": (180, 130, 60),
        "body_color": (100, 70, 30),
        "hp": 610,
        "speed": 240,
        "mass": 2.2,
        "size": 17,
        "description": "Master weapons engineer\nBuilds guns, turrets and fires on demand",
        "abilities": [
            Ability("Quick Draw",    0.5,  25, 650, (180,130,60), "Rapid pistol shot"),
            Ability("Deploy Turret", 3.5,  65, 500, SILVER,  "Plants auto-firing gun on stage"),
            Ability("Shotgun Blast", 2.0,  80, 200, ORANGE,  "Point-blank spread shot"),
            Ability("Gatling Storm",13.0, 205, 600, RED,     "Rains down 20 bullets"),
        ],
        "dodge_rate": 0.20,
        "weapon_type": "blaster",
        "has_shield": False
    },

    "🏗️ Architect": {
        "color": (120, 170, 220),
        "body_color": (60, 90, 140),
        "hp": 720,
        "speed": 205,
        "mass": 2.8,
        "size": 18,
        "description": "Tactical builder\nErects walls for cover, defence and crushing",
        "abilities": [
            Ability("Stone Throw",   0.7,  28, 400, (120,170,220), "Hurls a brick as projectile"),
            Ability("Build Wall",    3.0,  40, 250, SILVER,  "Raises a blocking wall near enemy"),
            Ability("Fortify",       5.0,   0,   0, BLUE,    "Hardens self — gains shield"),
            Ability("Wall Collapse",12.0, 210, 350, BROWN,   "Smashes all walls into enemies"),
        ],
        "dodge_rate": 0.10,
        "weapon_type": "fists",
        "has_shield": True
    },

    "👥 Clone-Master": {
        "color": (80, 220, 200),
        "body_color": (40, 140, 130),
        "hp": 540,
        "speed": 250,
        "mass": 1.8,
        "size": 16,
        "description": "Shape-shifting duplicator\nSpawns clones that fight independently",
        "abilities": [
            Ability("Shadow Punch",  0.6,  28, 120, (80,220,200), "Quick melee strike"),
            Ability("Spawn Clone",   4.0,  55, 300, TEAL,    "Creates a fighting clone"),
            Ability("Twin Strike",   2.5,  70, 250, CYAN,    "Clone and self attack together"),
            Ability("Clone Army",   13.0, 205, 400, WHITE,   "Spawns 4 clones at once"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "fists",
        "has_shield": False
    },

    "🍃 Venusaur": {
        "color": (90, 170, 110),
        "body_color": (55, 120, 75),
        "hp": 820,
        "speed": 220,
        "mass": 3.8,
        "size": 20,
        "description": "Kanto grass tank\nBulb cannon, toxic seeds, and seismic stomps",
        "abilities": [
            Ability("Solar Beam",   5.0, 120, 650, YELLOW, "Charges and unleashes a piercing solar beam"),
            Ability("Sludge Bomb",  2.4,  90, 520, PURPLE, "Lobs toxic sludge that bursts into poison"),
            Ability("Energy Ball",  1.6,  90, 500, GREEN,  "Launches a compact orb of nature energy"),
            Ability("Earthquake",   4.5, 100, 220, BROWN,  "Shakes the arena with a heavy ground slam"),
        ],
        "dodge_rate": 0.10,
        "weapon_type": "fists",
        "render_style": "venusaur",
        "species_group": "pokemon",
        "element_types": ["grass", "poison"]
    },
    "🔥 Charizard": {
        "color": (235, 125, 50),
        "body_color": (180, 75, 35),
        "hp": 760,
        "speed": 300,
        "mass": 2.4,
        "size": 19,
        "description": "Kanto aerial fire dragon\nSweeping flames, wing slashes, and savage claws",
        "abilities": [
            Ability("Flamethrower", 1.0,  90, 420, ORANGE, "Sustained flame stream"),
            Ability("Fire Blast",   2.4, 110, 520, RED,    "Explosive fire sigil projectile"),
            Ability("Air Slash",    1.2,  75, 480, WHITE,  "Cuts the air into sharp crescents"),
            Ability("Dragon Claw",  1.5,  80, 140, CYAN,   "Ferocious draconic claw combo"),
        ],
        "dodge_rate": 0.19,
        "weapon_type": "claws",
        "render_style": "charizard",
        "species_group": "pokemon",
        "element_types": ["fire", "flying"]
    },
    "💧 Blastoise": {
        "color": (75, 145, 220),
        "body_color": (45, 95, 160),
        "hp": 860,
        "speed": 210,
        "mass": 4.2,
        "size": 21,
        "description": "Kanto shell fortress\nHeavy cannons, waves, and icy pressure shots",
        "abilities": [
            Ability("Hydro Pump", 1.8, 110, 620, CYAN,  "Twin shell cannons fire a crushing water lance"),
            Ability("Surf",       2.0,  90, 420, BLUE,  "Summons a surging wall of water"),
            Ability("Ice Beam",   1.4,  90, 560, WHITE, "Freezing water beam"),
            Ability("Dark Pulse", 1.5,  80, 480, PURPLE,"Dark shockwave from the shell core"),
        ],
        "dodge_rate": 0.10,
        "weapon_type": "blaster",
        "render_style": "blastoise",
        "species_group": "pokemon",
        "element_types": ["water"]
    },
    "🌸 Meganium": {
        "color": (130, 205, 110),
        "body_color": (85, 150, 70),
        "hp": 840,
        "speed": 215,
        "mass": 3.6,
        "size": 20,
        "description": "Johto guardian herbivore\nRadiant petals with restorative and seismic power",
        "abilities": [
            Ability("Giga Drain",  1.3,  75, 420, GREEN,  "Drains life through flowering energy"),
            Ability("Solar Beam",  5.0, 120, 650, YELLOW, "Charges and fires concentrated sunlight"),
            Ability("Earthquake",  4.5, 100, 220, BROWN,  "Cracks the field with a body slam"),
            Ability("Body Slam",   1.6,  85, 150, SILVER, "Leaps forward with crushing weight"),
        ],
        "dodge_rate": 0.11,
        "weapon_type": "fists",
        "render_style": "meganium",
        "species_group": "pokemon",
        "element_types": ["grass"]
    },
    "🔥 Typhlosion": {
        "color": (235, 120, 60),
        "body_color": (75, 80, 95),
        "hp": 760,
        "speed": 300,
        "mass": 2.3,
        "size": 19,
        "description": "Johto volcanic striker\nIgnites collar flames and erupts violently",
        "abilities": [
            Ability("Eruption",     7.0, 150, 420, ORANGE, "Unleashes a volcanic blast from full power"),
            Ability("Flamethrower", 1.0,  90, 420, RED,    "Streams hot fire straight ahead"),
            Ability("Fire Blast",   2.4, 110, 520, ORANGE, "Detonating fire sigil"),
            Ability("Focus Blast",  3.0, 120, 460, GOLD,   "Compressed aura sphere that explodes"),
        ],
        "dodge_rate": 0.17,
        "weapon_type": "claws",
        "render_style": "typhlosion",
        "species_group": "pokemon",
        "element_types": ["fire"]
    },
    "💧 Feraligatr": {
        "color": (70, 150, 220),
        "body_color": (45, 105, 165),
        "hp": 820,
        "speed": 225,
        "mass": 3.7,
        "size": 20,
        "description": "Johto river bruiser\nSavage jaws, icy fists, and crushing water rushes",
        "abilities": [
            Ability("Waterfall",  1.2,  80, 140, CYAN,   "Bursts upward in a rising water strike"),
            Ability("Hydro Pump", 1.8, 110, 620, BLUE,   "Fires a heavy water cannon"),
            Ability("Ice Punch",  1.2,  75, 120, WHITE,  "Freezing melee smash"),
            Ability("Crunch",     1.1,  80, 120, PURPLE, "Dark bite that crushes defenses"),
        ],
        "dodge_rate": 0.13,
        "weapon_type": "claws",
        "render_style": "feraligatr",
        "species_group": "pokemon",
        "element_types": ["water"]
    },
    "🍃 Sceptile": {
        "color": (80, 200, 95),
        "body_color": (45, 145, 70),
        "hp": 720,
        "speed": 330,
        "mass": 2.0,
        "size": 17,
        "description": "Hoenn leaf duelist\nBlade leaves, forest orbs, and draconic pulses",
        "abilities": [
            Ability("Leaf Blade",   1.0,  90, 150, GREEN,  "Twin forearm leaves slash rapidly"),
            Ability("Energy Ball",  1.5,  90, 500, LIME,   "Fast sphere of natural force"),
            Ability("Dragon Pulse", 1.7,  85, 520, CYAN,   "Dragon-energy shockwave"),
            Ability("Focus Blast",  3.0, 120, 460, GOLD,   "Large aura blast"),
        ],
        "dodge_rate": 0.24,
        "weapon_type": "katana",
        "render_style": "sceptile",
        "species_group": "pokemon",
        "element_types": ["grass"]
    },
    "🔥 Blaziken": {
        "color": (235, 90, 60),
        "body_color": (220, 185, 80),
        "hp": 780,
        "speed": 255,
        "mass": 2.5,
        "size": 19,
        "description": "Hoenn martial inferno\nExplosive kicks, diving strikes, and blazing rushes",
        "abilities": [
            Ability("Flare Blitz",    2.0, 120, 160, ORANGE, "Ignites itself in a reckless flaming charge"),
            Ability("Blaze Kick",     1.3,  85, 130, RED,    "Fiery spinning kick"),
            Ability("High Jump Kick", 2.3, 130, 180, GOLD,   "Leaping martial strike with huge payoff"),
            Ability("Brave Bird",     2.0, 120, 220, WHITE,  "Diving avian tackle"),
        ],
        "dodge_rate": 0.17,
        "weapon_type": "claws",
        "render_style": "blaziken",
        "species_group": "pokemon",
        "element_types": ["fire", "fighting"]
    },
    "💧 Swampert": {
        "color": (80, 135, 205),
        "body_color": (225, 120, 70),
        "hp": 900,
        "speed": 180,
        "mass": 4.4,
        "size": 22,
        "description": "Hoenn amphibious tank\nMudquake stomps with brutal water-powered impacts",
        "abilities": [
            Ability("Earthquake",  4.5, 100, 220, BROWN, "Massive ground shock"),
            Ability("Waterfall",   1.2,  80, 140, CYAN,  "Rising water smash"),
            Ability("Hydro Pump",  1.8, 110, 620, BLUE,  "High-pressure flood burst"),
            Ability("Ice Punch",   1.2,  75, 120, WHITE, "Frozen fist strike"),
        ],
        "dodge_rate": 0.08,
        "weapon_type": "hammer",
        "render_style": "swampert",
        "species_group": "pokemon",
        "element_types": ["water", "ground"]
    },
    "🍃 Torterra": {
        "color": (95, 150, 80),
        "body_color": (90, 115, 65),
        "hp": 920,
        "speed": 170,
        "mass": 4.8,
        "size": 23,
        "description": "Sinnoh living continent\nCarries a forest shell and crushes the ground",
        "abilities": [
            Ability("Wood Hammer", 1.8, 120, 150, GREEN,  "Heavy recoil slam with a trunk-like charge"),
            Ability("Earthquake",  4.5, 100, 220, BROWN,  "Arena-shaking stomp"),
            Ability("Stone Edge",  2.3, 100, 420, SILVER, "Jagged stone pillars erupt upward"),
            Ability("Crunch",      1.1,  80, 120, PURPLE, "Dark jaw clamp"),
        ],
        "dodge_rate": 0.07,
        "weapon_type": "hammer",
        "render_style": "torterra",
        "species_group": "pokemon",
        "element_types": ["grass", "ground"]
    },
    "🔥 Infernape": {
        "color": (235, 130, 65),
        "body_color": (180, 65, 45),
        "hp": 760,
        "speed": 320,
        "mass": 2.2,
        "size": 18,
        "description": "Sinnoh acrobatic striker\nRelentless combos, fire arts, and fast interrupts",
        "abilities": [
            Ability("Flamethrower", 1.0,  90, 420, ORANGE, "Jets a focused stream of fire"),
            Ability("Fire Blast",   2.4, 110, 520, RED,    "Explosive flame mark"),
            Ability("Close Combat", 1.9, 120, 150, GOLD,   "Flurry of martial blows"),
            Ability("Mach Punch",   0.5,  40, 120, WHITE,  "Instant close-range jab"),
        ],
        "dodge_rate": 0.24,
        "weapon_type": "claws",
        "render_style": "infernape",
        "species_group": "pokemon",
        "element_types": ["fire", "fighting"]
    },
    "💧 Empoleon": {
        "color": (80, 120, 200),
        "body_color": (40, 70, 130),
        "hp": 820,
        "speed": 185,
        "mass": 3.6,
        "size": 20,
        "description": "Sinnoh steel emperor\nCommanding surf, cannons, and icy royal strikes",
        "abilities": [
            Ability("Surf",          2.0,  90, 420, BLUE,   "Summons a broad water surge"),
            Ability("Hydro Pump",    1.8, 110, 620, CYAN,   "Piercing hydro blast"),
            Ability("Flash Cannon",  1.7,  80, 520, SILVER, "Steel energy cannon"),
            Ability("Ice Beam",      1.4,  90, 560, WHITE,  "Freezing lance"),
        ],
        "dodge_rate": 0.11,
        "weapon_type": "trident",
        "render_style": "empoleon",
        "species_group": "pokemon",
        "element_types": ["water", "steel"]
    },
    "🍃 Serperior": {
        "color": (90, 205, 110),
        "body_color": (55, 145, 75),
        "hp": 720,
        "speed": 335,
        "mass": 1.8,
        "size": 18,
        "description": "Unova royal serpent\nElegant coils with storms of leaves and draining vines",
        "abilities": [
            Ability("Leaf Storm",   2.8, 130, 520, GREEN, "Whips the arena with a leaf cyclone"),
            Ability("Energy Ball",  1.5,  90, 500, LIME,  "Fast nature orb"),
            Ability("Dragon Pulse", 1.7,  85, 520, CYAN,  "Serpentine dragon wave"),
            Ability("Giga Drain",   1.3,  75, 420, GREEN, "Saps vitality with plant energy"),
        ],
        "dodge_rate": 0.25,
        "weapon_type": "staff",
        "render_style": "serperior",
        "species_group": "pokemon",
        "element_types": ["grass"]
    },
    "🔥 Emboar": {
        "color": (210, 85, 55),
        "body_color": (70, 60, 70),
        "hp": 900,
        "speed": 175,
        "mass": 4.5,
        "size": 22,
        "description": "Unova brute-force boar\nMassive crashes, flaming tackles, and electric bursts",
        "abilities": [
            Ability("Flare Blitz",  2.0, 120, 160, ORANGE, "Burning body charge"),
            Ability("Heat Crash",   1.8, 105, 150, RED,    "Overwhelms foes with fiery weight"),
            Ability("Hammer Arm",   1.6, 100, 140, BROWN,  "Heavy arm smash"),
            Ability("Wild Charge",  1.8,  90, 170, YELLOW, "Electrified tackle"),
        ],
        "dodge_rate": 0.07,
        "weapon_type": "hammer",
        "render_style": "emboar",
        "species_group": "pokemon",
        "element_types": ["fire", "fighting"]
    },
    "💧 Samurott": {
        "color": (95, 145, 215),
        "body_color": (50, 85, 150),
        "hp": 800,
        "speed": 205,
        "mass": 3.2,
        "size": 20,
        "description": "Unova shell blade warrior\nDraws seamitars with slicing water pressure",
        "abilities": [
            Ability("Hydro Pump", 1.8, 110, 620, BLUE,   "High-pressure shell cannon"),
            Ability("Surf",       2.0,  90, 420, CYAN,   "Summons a cresting water rush"),
            Ability("Megahorn",   1.8, 120, 150, GOLD,   "Horn-first charge"),
            Ability("Ice Beam",   1.4,  90, 560, WHITE,  "Freezing lance"),
        ],
        "dodge_rate": 0.13,
        "weapon_type": "katana",
        "render_style": "samurott",
        "species_group": "pokemon",
        "element_types": ["water"]
    },
    "🍃 Chesnaught": {
        "color": (95, 150, 70),
        "body_color": (115, 80, 55),
        "hp": 900,
        "speed": 170,
        "mass": 4.6,
        "size": 22,
        "description": "Kalos armored bruiser\nSpiked shell, crushing punches, and quake slams",
        "abilities": [
            Ability("Wood Hammer",  1.8, 120, 150, GREEN,  "Spiked body slam"),
            Ability("Hammer Arm",   1.6, 100, 140, BROWN,  "Heavy armored punch"),
            Ability("Drain Punch",  1.4,  75, 130, GOLD,   "Restorative close strike"),
            Ability("Earthquake",   4.5, 100, 220, BROWN,  "Ground-shaking smash"),
        ],
        "dodge_rate": 0.08,
        "weapon_type": "hammer",
        "render_style": "chesnaught",
        "species_group": "pokemon",
        "element_types": ["grass", "fighting"]
    },
    "🔥 Delphox": {
        "color": (220, 110, 70),
        "body_color": (145, 60, 45),
        "hp": 740,
        "speed": 300,
        "mass": 2.0,
        "size": 18,
        "description": "Kalos mystic fox\nSpellfire caster with wand flourishes and shadow orbs",
        "abilities": [
            Ability("Flamethrower", 1.0,  90, 420, ORANGE, "Spellfire stream"),
            Ability("Fire Blast",   2.4, 110, 520, RED,    "Exploding fire sigil"),
            Ability("Psychic",      1.6,  90, 500, PINK,   "Telekinetic burst"),
            Ability("Shadow Ball",  1.5,  80, 480, PURPLE, "Dark sorcery orb"),
        ],
        "dodge_rate": 0.22,
        "weapon_type": "staff",
        "render_style": "delphox",
        "species_group": "pokemon",
        "element_types": ["fire", "psychic"]
    },
    "💧 Greninja": {
        "color": (65, 115, 200),
        "body_color": (35, 70, 135),
        "hp": 720,
        "speed": 340,
        "mass": 1.7,
        "size": 17,
        "description": "Kalos stealth amphibian\nWater shuriken style strikes, ice, and dark pulses",
        "abilities": [
            Ability("Hydro Pump", 1.8, 110, 620, CYAN,   "Compressed water blast"),
            Ability("Surf",       2.0,  90, 420, BLUE,   "Slides a water wave through the field"),
            Ability("Dark Pulse", 1.5,  80, 480, PURPLE, "Shadowy pulse blast"),
            Ability("Ice Beam",   1.4,  90, 560, WHITE,  "Narrow freezing beam"),
        ],
        "dodge_rate": 0.28,
        "weapon_type": "katana",
        "render_style": "greninja",
        "species_group": "pokemon",
        "element_types": ["water", "dark"]
    },

}

POKEMON_CHARACTER_NAMES = [
    "🍃 Venusaur", "🔥 Charizard", "💧 Blastoise",
    "🌸 Meganium", "🔥 Typhlosion", "💧 Feraligatr",
    "🍃 Sceptile", "🔥 Blaziken", "💧 Swampert",
    "🍃 Torterra", "🔥 Infernape", "💧 Empoleon",
    "🍃 Serperior", "🔥 Emboar", "💧 Samurott",
    "🍃 Chesnaught", "🔥 Delphox", "💧 Greninja",
]

ORIGINAL_CHARACTER_NAMES = [name for name in CHARACTER_DATA.keys() if name not in POKEMON_CHARACTER_NAMES]
LEGENDARY_CHARACTER_NAMES = []
STARTER_POKEMON_NAMES = list(POKEMON_CHARACTER_NAMES)

POKEMON_COUNTER_MOVES = {
    "🍃 Venusaur": {"move": "Earthquake", "targets": ["fire", "flying", "poison", "steel"]},
    "🔥 Charizard": {"move": "Dragon Claw", "targets": ["water", "electric", "rock"]},
    "💧 Blastoise": {"move": "Ice Beam", "targets": ["grass", "electric"]},
    "🌸 Meganium": {"move": "Earthquake", "targets": ["fire", "flying", "ice", "poison", "bug"]},
    "🔥 Typhlosion": {"move": "Focus Blast", "targets": ["water", "rock", "ground"]},
    "💧 Feraligatr": {"move": "Ice Punch", "targets": ["grass", "electric"]},
    "🍃 Sceptile": {"move": "Dragon Pulse", "targets": ["fire", "ice", "flying", "bug"]},
    "🔥 Blaziken": {"move": "Brave Bird", "targets": ["water", "ground", "psychic"]},
    "💧 Swampert": {"move": "Ice Punch", "targets": ["grass"]},
    "🍃 Torterra": {"move": "Stone Edge", "targets": ["ice", "fire", "flying", "bug"]},
    "🔥 Infernape": {"move": "Mach Punch", "targets": ["water", "flying", "ground", "psychic"]},
    "💧 Empoleon": {"move": "Ice Beam", "targets": ["electric", "ground", "fighting"]},
    "🍃 Serperior": {"move": "Dragon Pulse", "targets": ["fire", "ice", "bug", "flying"]},
    "🔥 Emboar": {"move": "Wild Charge", "targets": ["water", "ground", "psychic"]},
    "💧 Samurott": {"move": "Megahorn", "targets": ["grass", "electric"]},
    "🍃 Chesnaught": {"move": "Earthquake", "targets": ["fire", "flying", "psychic", "fairy"]},
    "🔥 Delphox": {"move": "Psychic", "targets": ["water", "ground", "rock", "dark"]},
    "💧 Greninja": {"move": "Ice Beam", "targets": ["grass", "electric", "fighting"]},
}

TYPE_EFFECTIVENESS.update(LEGENDARY_TYPE_EFFECTIVENESS)
MOVE_TYPE_MAP.update(LEGENDARY_MOVE_TYPES)
POKEMON_SPRITE_INDEX.update(LEGENDARY_SPRITES)
POKEMON_COUNTER_MOVES.update(LEGENDARY_COUNTER_MOVES)

_legendary_entries = {}
for _legend_name, _legend_data in LEGENDARY_POKEMON_DATA.items():
    _entry = dict(_legend_data)
    _entry["abilities"] = [Ability(*ab) for ab in _legend_data["abilities"]]
    _legendary_entries[_legend_name] = _entry

CHARACTER_DATA.update(_legendary_entries)
POKEMON_CHARACTER_NAMES.extend(_legendary_entries.keys())
LEGENDARY_CHARACTER_NAMES = list(_legendary_entries.keys())
STARTER_POKEMON_NAMES = [name for name in POKEMON_CHARACTER_NAMES if name not in LEGENDARY_CHARACTER_NAMES]
ORIGINAL_CHARACTER_NAMES = [name for name in CHARACTER_DATA.keys() if name not in POKEMON_CHARACTER_NAMES]

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
        self.render_style = data.get("render_style", "")
        self.species_group = data.get("species_group", "original")
        self.element_types = data.get("element_types", [])
        self.legendary_theme = data.get("legendary_theme", "")
        if not self.legendary_theme and self.species_group == "pokemon" and self.name in LEGENDARY_SPRITES:
            if "electric" in self.element_types:
                self.legendary_theme = "storm"
            elif "ice" in self.element_types:
                self.legendary_theme = "ice"
            elif "ground" in self.element_types or "rock" in self.element_types:
                self.legendary_theme = "earth"
            elif "dark" in self.element_types or "ghost" in self.element_types:
                self.legendary_theme = "dark"
            elif "dragon" in self.element_types:
                self.legendary_theme = "dragon"
            elif "psychic" in self.element_types or "fairy" in self.element_types:
                self.legendary_theme = "cosmic"
            else:
                self.legendary_theme = "aura"
        self.move_types = data.get("move_types", {})
        counter_info = POKEMON_COUNTER_MOVES.get(char_name, {})
        self.counter_move = counter_info.get("move")
        self.counter_targets = counter_info.get("targets", [])
        self.sprite = self._load_sprite()

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
        self.shape.collision_type = 1 # Fighter type
        self.shape.fighter = self # Self reference for collision callbacks
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
        self.cast_flash_timer = 0.0
        self.cast_ring_timer = 0.0
        self.cast_color = self.color
        self.cast_accent = self.body_color
        self.cast_style = self.weapon_type
        self.afterimages = []
        self.collision_recover_timer = 0.0
        self.ambient_phase = random.uniform(0.0, math.pi * 2)

        self.hazard_hit_count = 0
        self.dot_damage = 0.0
        self.dot_timer  = 0.0

    @property
    def pos(self):
        return (int(self.x), int(self.y))

    def _sprite_candidates(self):
        if self.species_group != "pokemon":
            return []
        candidates = []
        sprite_info = POKEMON_SPRITE_INDEX.get(self.name, {})
        dex = sprite_info.get("dex")
        for rel_path in sprite_info.get("files", []):
            for gen_folder, sprite_folder in sprite_info.get("folders", []):
                candidates.append(Path(gen_folder) / sprite_folder / rel_path)
                candidates.append(Path(gen_folder) / rel_path)
        for gen_folder, sprite_folder in sprite_info.get("folders", []):
            candidates.extend([
                Path(gen_folder) / "pokemon" / "main-sprites" / sprite_folder / f"{dex}.png",
                Path(gen_folder) / sprite_folder / f"{dex}.png",
                Path(gen_folder) / f"{dex}.png",
            ])
        slug = self.name.split(" ", 1)[-1].lower().replace(".", "").replace("'", "").replace(" ", "_").replace("-", "_")
        base = Path("assets") / "pokemon_sprites"
        candidates.extend([
            base / f"{slug}.png",
            base / f"{slug}_front.png",
            base / f"{slug}_idle.png",
        ])
        return candidates

    def _load_sprite(self):
        for path in self._sprite_candidates():
            if path.exists():
                try:
                    return pygame.image.load(str(path)).convert_alpha()
                except Exception:
                    return None
        return None

    def _move_type(self, move_name):
        return MOVE_TYPE_MAP.get(move_name)

    def _effectiveness_multiplier(self, move_name, target):
        if self.species_group != "pokemon" or target.species_group != "pokemon":
            return 1.0
        move_type = self._move_type(move_name)
        if not move_type:
            return 1.0
        mult = 1.0
        table = TYPE_EFFECTIVENESS.get(move_type, {})
        for defender_type in target.element_types:
            mult *= table.get(defender_type, 1.0)
        return mult

    def _mix_color(self, c1, c2, t=0.5):
        t = max(0.0, min(1.0, t))
        return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

    def _spawn_afterimages(self, count, color=None, spread=18):
        base_color = color or self.cast_color
        for idx in range(count):
            offset = (idx - count // 2) * spread * 0.35
            self.afterimages.append({
                "x": self.x - self.facing * offset,
                "y": self.y + math.sin(idx * 1.7) * 5,
                "size": self.size * (1.0 - idx * 0.06),
                "life": 0.28 + idx * 0.03,
                "max_life": 0.28 + idx * 0.03,
                "color": base_color,
            })

    def _trigger_ability_visual(self, ab, target, ndx, ndy, dist):
        aim_angle = math.atan2(ndy, ndx)
        intensity = 1.0
        if ab.cooldown >= 10 or ab.damage >= 180:
            intensity = 1.9
        elif ab.cooldown >= 5 or ab.damage >= 90:
            intensity = 1.45
        elif ab.damage == 0:
            intensity = 1.25

        self.cast_color = self._mix_color(self.color, ab.color, 0.65)
        self.cast_accent = self._mix_color(self.body_color, WHITE, 0.35)
        self.cast_flash_timer = 0.18 + intensity * 0.08
        self.cast_ring_timer = 0.30 + intensity * 0.14
        self.cast_style = self.weapon_type

        if ab.damage == 0:
            self.cast_style = "support"
        elif ab.cooldown >= 10:
            self.cast_style = f"{self.weapon_type}_ultimate"

        self.particles.emit_ring(
            self.x,
            self.y,
            self.cast_color,
            count=int(10 + intensity * 6),
            speed=120 + intensity * 90,
            size=3 + intensity * 2,
            life=0.35 + intensity * 0.08,
        )

        if ab.range > 280:
            tip_x = self.x + ndx * min(dist, ab.range * 0.55)
            tip_y = self.y + ndy * min(dist, ab.range * 0.55)
            self.particles.emit_beam(
                self.x,
                self.y,
                tip_x,
                tip_y,
                self.cast_accent,
                count=int(8 + intensity * 5),
                size=2 + int(intensity),
                life=0.18 + intensity * 0.05,
            )

        if self.weapon_type == "sword":
            self.particles.emit_slash(self.x, self.y, aim_angle, self.cast_color, size=int(self.size * (2.1 + 0.3 * intensity)), count=int(12 + intensity * 4))
            self.particles.emit(self.x, self.y, GOLD, count=int(8 + intensity * 3), speed=180, spread=0.55, gravity=False, direction=aim_angle)
            self._spawn_afterimages(int(2 + intensity), self.cast_accent)
        elif self.weapon_type == "staff":
            orbit_r = int(self.size * (2.1 + 0.4 * intensity))
            for i in range(int(6 + intensity * 2)):
                ang = aim_angle + (i / max(1, int(6 + intensity * 2))) * math.pi * 2
                px = self.x + math.cos(ang) * orbit_r
                py = self.y + math.sin(ang) * orbit_r
                self.particles.emit(px, py, self.cast_color, count=2, speed=50, size=4, life=0.45, gravity=False)
            self.particles.emit_ring(self.x, self.y, self.cast_accent, count=int(8 + intensity * 3), speed=70, size=4, life=0.5)
        elif self.weapon_type == "katana":
            self.particles.emit_slash(self.x, self.y, aim_angle + 0.22, self.cast_color, size=int(self.size * (2.4 + 0.25 * intensity)), count=int(10 + intensity * 3))
            self.particles.emit_slash(self.x, self.y, aim_angle - 0.22, self.cast_accent, size=int(self.size * (1.9 + 0.2 * intensity)), count=int(10 + intensity * 3))
            self._spawn_afterimages(int(3 + intensity), self.cast_color, spread=24)
        elif self.weapon_type == "blaster":
            muzzle_x = self.x + ndx * (self.size + 12)
            muzzle_y = self.y + ndy * (self.size * 0.3)
            self.particles.emit(muzzle_x, muzzle_y, self.cast_color, count=int(10 + intensity * 4), speed=220, spread=0.35, size=4, life=0.35, gravity=False, direction=aim_angle)
            self.particles.emit_beam(self.x, self.y, muzzle_x + ndx * 80, muzzle_y + ndy * 80, CYAN, count=int(7 + intensity * 3), size=3, life=0.2)
        elif self.weapon_type == "bow":
            anchor_x = self.x - ndx * 8
            anchor_y = self.y - ndy * 8
            for i in range(int(3 + intensity * 2)):
                fan = (i - 1) * 0.18
                self.particles.emit(anchor_x, anchor_y, self.cast_color, count=3, speed=180, spread=0.12, size=3, life=0.4, gravity=False, direction=aim_angle + fan)
            self.particles.emit_beam(anchor_x, anchor_y, anchor_x + ndx * 55, anchor_y + ndy * 55, self.cast_accent, count=int(6 + intensity * 3), size=2, life=0.18)
        elif self.weapon_type == "trident":
            for fork in (-0.16, 0.0, 0.16):
                tx = self.x + math.cos(aim_angle + fork) * self.size * 2.4
                ty = self.y + math.sin(aim_angle + fork) * self.size * 2.4
                self.particles.emit_beam(self.x, self.y, tx, ty, self.cast_color, count=int(6 + intensity * 2), size=3, life=0.24)
            self.particles.emit_ring(self.x, self.y, BLUE, count=int(9 + intensity * 3), speed=140, size=4, life=0.4)
        elif self.weapon_type == "claws":
            for claw in (-10, 0, 10):
                ox = self.x - ndy * claw
                oy = self.y + ndx * claw
                self.particles.emit_slash(ox, oy, aim_angle, self.cast_color, size=int(self.size * (1.8 + 0.15 * intensity)), count=int(8 + intensity * 3))
            self._spawn_afterimages(int(2 + intensity), self.cast_color, spread=20)
        elif self.weapon_type == "hammer":
            self.particles.emit_ring(self.x, self.y, self.cast_color, count=int(12 + intensity * 4), speed=240, size=5, life=0.42)
            self.particles.emit(self.x, self.y + self.size, SILVER, count=int(10 + intensity * 4), speed=220, size=4, life=0.45)
        elif self.weapon_type == "chain":
            prev_x, prev_y = self.x, self.y
            for i in range(1, int(6 + intensity * 2)):
                seg_x = self.x + ndx * i * 16 + math.sin(i * 0.9) * 8 * ndy
                seg_y = self.y + ndy * i * 16 - math.sin(i * 0.9) * 8 * ndx
                self.particles.emit_beam(prev_x, prev_y, seg_x, seg_y, self.cast_color, count=4, size=2, life=0.18)
                prev_x, prev_y = seg_x, seg_y
            self.particles.emit(prev_x, prev_y, RED, count=int(7 + intensity * 3), speed=120, size=4, life=0.4)
        elif self.cast_style == "support":
            self.particles.emit_ring(self.x, self.y, GREEN, count=int(14 + intensity * 3), speed=160, size=5, life=0.55)
            for i in range(5):
                ang = aim_angle + i * (math.pi * 2 / 5)
                self.particles.emit(self.x + math.cos(ang) * self.size, self.y + math.sin(ang) * self.size, self.cast_accent, count=3, speed=70, size=3, life=0.5, gravity=False)
        else:
            self.particles.emit_ring(self.x, self.y, self.cast_color, count=int(10 + intensity * 2), speed=160, size=4, life=0.35)

        if ab.cooldown >= 10:
            crown_y = self.y - self.size * 1.8
            for i in range(6):
                ang = aim_angle + i * (math.pi / 3)
                self.particles.emit_beam(
                    self.x,
                    crown_y,
                    self.x + math.cos(ang) * (28 + intensity * 8),
                    crown_y + math.sin(ang) * (28 + intensity * 8),
                    self.cast_accent,
                    count=5,
                    size=2 + int(intensity),
                    life=0.24,
                )

    def _draw_ambient_fx(self, screen, x, y, s):
        t = pygame.time.get_ticks() * 0.001 + self.ambient_phase

        if self.weapon_type == "staff":
            for i in range(3):
                ang = t * 1.7 + i * (math.pi * 2 / 3)
                rad = s + 14
                px = x + math.cos(ang) * rad
                py = y + math.sin(ang) * (rad * 0.7)
                pygame.draw.circle(screen, self.cast_color if self.cast_flash_timer > 0 else self.color, (int(px), int(py)), 4)
                pygame.draw.circle(screen, WHITE, (int(px), int(py)), 2)

        elif self.weapon_type == "blaster":
            for i in range(2):
                ang = t * 2.4 + i * math.pi
                rad = s + 10
                px = x + math.cos(ang) * rad
                py = y + math.sin(ang) * 8
                pygame.draw.circle(screen, CYAN, (int(px), int(py)), 3)
            arc_rect = pygame.Rect(x - s - 10, y - s - 6, (s + 10) * 2, (s + 6) * 2)
            pygame.draw.arc(screen, (*self.color[:2], self.color[2]) if len(self.color) == 3 else self.color, arc_rect, t, t + math.pi * 0.9, 2)

        elif self.weapon_type == "trident":
            for i in range(2):
                ang = t * 1.4 + i * math.pi
                rad = s + 16
                px = x + math.cos(ang) * rad
                py = y + math.sin(ang) * rad * 0.5
                pygame.draw.circle(screen, BLUE, (int(px), int(py)), 5, 2)
                pygame.draw.circle(screen, CYAN, (int(px), int(py)), 2)

        elif self.weapon_type == "bow":
            for i in range(3):
                ang = t * 1.8 + i * 0.45
                px = x - self.facing * (s + 10 + i * 7)
                py = y + math.sin(ang) * 10
                pygame.draw.line(screen, self.color, (int(px), int(py)), (int(px + self.facing * 14), int(py - 6)), 2)

        elif self.weapon_type in {"katana", "claws"}:
            for i in range(2):
                ang = t * 2.6 + i * math.pi
                px = x + math.cos(ang) * (s + 8)
                py = y + math.sin(ang) * 6
                pygame.draw.circle(screen, self.body_color, (int(px), int(py)), 3)

        name = self.name.encode("ascii", "ignore").decode("ascii")
        if "Dragon" in name or "Phoenix" in name or "Fire" in name or "Lava" in name:
            for i in range(2):
                ang = t * 1.9 + i * math.pi
                px = x + math.cos(ang) * (s + 6)
                py = y + s * 0.8 + math.sin(ang * 1.3) * 6
                pygame.draw.circle(screen, ORANGE, (int(px), int(py)), 4)
                pygame.draw.circle(screen, RED, (int(px), int(py)), 2)

        if "Ghost" in name or "Phantom" in name or "Shadow" in name or "Void" in name:
            ghost = pygame.Surface((int((s + 18) * 2), int((s + 18) * 2)), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*PURPLE, 22), (ghost.get_width() // 2, ghost.get_height() // 2), s + 12)
            screen.blit(ghost, (x - ghost.get_width() // 2, y - ghost.get_height() // 2))

        if "Storm" in name or "Thunder" in name or "Weather" in name or "Lightning" in name:
            for i in range(2):
                ang = t * 3.2 + i * math.pi
                px = x + math.cos(ang) * (s + 18)
                py = y - s - 4 + math.sin(ang * 1.8) * 8
                pygame.draw.line(screen, YELLOW, (int(px), int(py - 5)), (int(px + 4), int(py + 5)), 2)
                pygame.draw.line(screen, WHITE, (int(px + 1), int(py - 4)), (int(px + 3), int(py + 3)), 1)

        if "Cosmic" in name or "Nova" in name or "Sorcerer" in name or "Mirror" in name:
            for i in range(4):
                ang = t * 1.1 + i * (math.pi / 2)
                rad = s + 22
                px = x + math.cos(ang) * rad
                py = y + math.sin(ang) * rad * 0.7
                pygame.draw.circle(screen, self.cast_accent if self.cast_flash_timer > 0 else WHITE, (int(px), int(py)), 2)

        theme = self.legendary_theme
        if theme == "storm":
            for i in range(3):
                ang = t * 2.4 + i * (math.pi * 2 / 3)
                px = x + math.cos(ang) * (s + 16)
                py = y - s * 0.6 + math.sin(ang * 1.4) * 8
                pygame.draw.line(screen, YELLOW, (int(px), int(py - 4)), (int(px + 5), int(py + 5)), 2)
        elif theme == "aura":
            for i in range(3):
                ang = t * 1.4 + i * (math.pi * 2 / 3)
                px = x + math.cos(ang) * (s + 18)
                py = y + math.sin(ang) * (s * 0.55)
                pygame.draw.circle(screen, GOLD, (int(px), int(py)), 3)
                pygame.draw.circle(screen, WHITE, (int(px), int(py)), 1)
        elif theme == "cosmic":
            for i in range(5):
                ang = t * 0.9 + i * (math.pi * 2 / 5)
                px = x + math.cos(ang) * (s + 20)
                py = y + math.sin(ang) * (s * 0.75)
                pygame.draw.circle(screen, WHITE, (int(px), int(py)), 2)
        elif theme == "dragon":
            for i in range(2):
                ang = t * 1.7 + i * math.pi
                px = x + math.cos(ang) * (s + 12)
                py = y + math.sin(ang) * 8
                pygame.draw.arc(screen, CYAN, (px - 10, py - 6, 20, 12), 0.2, math.pi + 0.4, 2)
        elif theme == "dark":
            halo = pygame.Surface((int((s + 20) * 2), int((s + 20) * 2)), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*PURPLE, 20), (halo.get_width() // 2, halo.get_height() // 2), s + 14)
            screen.blit(halo, (x - halo.get_width() // 2, y - halo.get_height() // 2))
        elif theme == "earth":
            for i in range(4):
                px = x - s + i * (s * 0.65)
                py = y + s + math.sin(t * 2 + i) * 2
                pygame.draw.line(screen, BROWN, (int(px), int(py)), (int(px + 8), int(py - 6)), 2)
        elif theme == "ice":
            for i in range(3):
                ang = t * 1.3 + i * (math.pi * 2 / 3)
                px = x + math.cos(ang) * (s + 14)
                py = y + math.sin(ang) * (s * 0.6)
                pygame.draw.line(screen, WHITE, (int(px - 4), int(py)), (int(px + 4), int(py)), 1)
                pygame.draw.line(screen, WHITE, (int(px), int(py - 4)), (int(px), int(py + 4)), 1)

    def _draw_pokemon_details(self, screen, x, y, s, body_draw, draw_color):
        style = self.render_style
        if not style:
            return

        t = pygame.time.get_ticks() * 0.001 + self.ambient_phase
        accent = self.cast_color if self.cast_flash_timer > 0 else draw_color

        if style == "venusaur":
            bulb = pygame.Rect(x - s - 6, y - s - 14, s * 2 + 12, s + 10)
            pygame.draw.ellipse(screen, (40, 110, 55), bulb)
            pygame.draw.ellipse(screen, (65, 155, 85), bulb, 3)
            pygame.draw.circle(screen, (210, 105, 135), (x, y - s - 10), s // 2 + 6)
            for ang in (-1.2, -0.35, 0.35, 1.2):
                leaf = [(x, y - s - 2), (x + math.cos(ang) * (s + 18), y - s - 10 + math.sin(ang) * 16), (x + math.cos(ang) * (s + 8), y - s - 24)]
                pygame.draw.polygon(screen, (70, 155, 90), leaf)
        elif style == "charizard":
            left_wing = [(x - s, y - 6), (x - s - 26, y - s - 16), (x - 8, y - s + 4)]
            right_wing = [(x + s, y - 6), (x + s + 26, y - s - 16), (x + 8, y - s + 4)]
            pygame.draw.polygon(screen, (70, 105, 150), left_wing)
            pygame.draw.polygon(screen, (70, 105, 150), right_wing)
            pygame.draw.polygon(screen, (235, 175, 90), [(x, y + s - 2), (x + self.facing * (s + 18), y + s + 10), (x + self.facing * (s + 8), y + s + 18)])
            flame_x = x + self.facing * (s + 18)
            flame_y = y + s + 10
            pygame.draw.circle(screen, ORANGE, (int(flame_x), int(flame_y)), 5)
            pygame.draw.circle(screen, YELLOW, (int(flame_x + self.facing * 2), int(flame_y - 2)), 3)
        elif style == "blastoise":
            shell = pygame.Rect(x - s - 4, y - s + 4, s * 2 + 8, s * 2 - 6)
            pygame.draw.ellipse(screen, (90, 75, 55), shell)
            pygame.draw.ellipse(screen, (180, 170, 140), (x - s + 4, y - s + 10, s * 2 - 8, s * 2 - 18), 3)
            for side in (-1, 1):
                start = (x + side * (s - 4), y - s + 4)
                end = (x + side * (s + 16), y - s - 14 + math.sin(t * 1.5) * 3)
                pygame.draw.line(screen, SILVER, start, end, 6)
                pygame.draw.circle(screen, CYAN, (int(end[0]), int(end[1])), 4)
        elif style == "meganium":
            for i in range(6):
                ang = i * math.pi / 3 + math.sin(t) * 0.08
                px = x + math.cos(ang) * (s + 6)
                py = y - s + math.sin(ang) * (s * 0.7)
                pygame.draw.circle(screen, (235, 120, 150), (int(px), int(py)), 6)
            pygame.draw.circle(screen, (245, 235, 120), (x, y - s + 2), 5)
            pygame.draw.line(screen, accent, (x - 6, y - s - 2), (x - 12, y - s - 16), 2)
            pygame.draw.line(screen, accent, (x + 6, y - s - 2), (x + 12, y - s - 16), 2)
        elif style == "typhlosion":
            for dx in (-14, 0, 14):
                peak = [(x + dx - 6, y - s + 2), (x + dx, y - s - 18 - abs(dx) * 0.2), (x + dx + 6, y - s + 2)]
                pygame.draw.polygon(screen, ORANGE, peak)
                pygame.draw.polygon(screen, YELLOW, [(peak[0][0] + 2, peak[0][1]), peak[1], (peak[2][0] - 2, peak[2][1])])
        elif style == "feraligatr":
            for dy in (-12, 0, 12):
                pygame.draw.polygon(screen, RED, [(x - 4, y + dy), (x - 14, y + dy - 6), (x - 10, y + dy + 6)])
                pygame.draw.polygon(screen, RED, [(x + 4, y + dy), (x + 14, y + dy - 6), (x + 10, y + dy + 6)])
        elif style == "sceptile":
            for side in (-1, 1):
                pygame.draw.polygon(screen, (85, 200, 110), [(x + side * (s - 4), y), (x + side * (s + 18), y - 10), (x + side * (s + 10), y + 8)])
            tail = [(x, y + s - 2), (x - 10, y + s + 18), (x + 10, y + s + 18)]
            pygame.draw.polygon(screen, (90, 210, 105), tail)
        elif style == "blaziken":
            for side in (-1, 1):
                pygame.draw.polygon(screen, (245, 235, 180), [(x + side * 8, y + 6), (x + side * 18, y + s + 8), (x + side * 4, y + s + 4)])
            crest = [(x - 6, y - s + 6), (x, y - s - 16), (x + 6, y - s + 6)]
            pygame.draw.polygon(screen, RED, crest)
        elif style == "swampert":
            pygame.draw.line(screen, (240, 120, 70), (x - 8, y - s + 6), (x - 20, y - s - 8), 6)
            pygame.draw.line(screen, (240, 120, 70), (x + 8, y - s + 6), (x + 20, y - s - 8), 6)
            pygame.draw.circle(screen, (240, 120, 70), (x - s + 4, y - 2), 5)
            pygame.draw.circle(screen, (240, 120, 70), (x + s - 4, y - 2), 5)
        elif style == "torterra":
            shell = pygame.Rect(x - s - 4, y - s + 2, s * 2 + 8, s * 2 - 2)
            pygame.draw.ellipse(screen, (90, 80, 55), shell)
            trunk = pygame.Rect(x - 4, y - s - 18, 8, 18)
            pygame.draw.rect(screen, (110, 80, 45), trunk)
            pygame.draw.circle(screen, (60, 150, 70), (x, y - s - 22), 14)
        elif style == "infernape":
            flame = [(x - 7, y - s + 6), (x, y - s - 18), (x + 7, y - s + 6)]
            pygame.draw.polygon(screen, ORANGE, flame)
            pygame.draw.circle(screen, (235, 205, 95), (x - s + 6, y + 2), 4)
            pygame.draw.circle(screen, (235, 205, 95), (x + s - 6, y + 2), 4)
        elif style == "empoleon":
            pygame.draw.polygon(screen, (235, 210, 100), [(x - 5, y - s + 8), (x, y - s - 16), (x + 5, y - s + 8)])
            pygame.draw.polygon(screen, (235, 210, 100), [(x - 14, y - s + 12), (x - 5, y - s - 2), (x - 1, y - s + 12)])
            pygame.draw.polygon(screen, (235, 210, 100), [(x + 14, y - s + 12), (x + 5, y - s - 2), (x + 1, y - s + 12)])
            pygame.draw.polygon(screen, (240, 180, 70), [(x - 6, y + 2), (x + 6, y + 2), (x, y + 10)])
        elif style == "serperior":
            for i in range(3):
                rad = s + 6 + i * 5
                pygame.draw.arc(screen, (95, 220, 110), (x - rad, y - rad * 0.6, rad * 2, rad * 1.2), math.pi * 0.1, math.pi * 0.9, 3)
            for side in (-1, 1):
                pygame.draw.polygon(screen, (220, 235, 120), [(x + side * 8, y - s + 2), (x + side * 24, y - s - 8), (x + side * 16, y - s + 12)])
        elif style == "emboar":
            for side in (-1, 1):
                pygame.draw.circle(screen, ORANGE, (x + side * (s - 2), y), 5, 2)
            beard = [(x - 10, y + 2), (x, y + s + 10), (x + 10, y + 2)]
            pygame.draw.polygon(screen, ORANGE, beard)
        elif style == "samurott":
            pygame.draw.polygon(screen, (240, 230, 180), [(x - 5, y - s + 10), (x, y - s - 16), (x + 5, y - s + 10)])
            for side in (-1, 1):
                pygame.draw.line(screen, SILVER, (x + side * (s - 6), y - 2), (x + side * (s + 12), y - 12), 4)
            pygame.draw.arc(screen, WHITE, (x - s - 4, y - s + 2, s * 2 + 8, s * 2 - 2), 0.1, math.pi - 0.1, 2)
        elif style == "chesnaught":
            for ang in [0.4, 0.9, 1.3, 1.8, 2.2, 2.7]:
                px = x + math.cos(ang) * (s + 6)
                py = y + math.sin(ang) * (s + 2)
                pygame.draw.polygon(screen, (180, 220, 90), [(px, py), (px + 6, py + 2), (px + 2, py - 8)])
        elif style == "delphox":
            robe = [(x - s + 4, y + 6), (x - 8, y + s + 12), (x + 8, y + s + 12), (x + s - 4, y + 6)]
            pygame.draw.polygon(screen, (170, 70, 55), robe)
            pygame.draw.line(screen, (120, 80, 50), (x + self.facing * (s - 4), y + 2), (x + self.facing * (s + 16), y - 14), 3)
            pygame.draw.circle(screen, ORANGE, (int(x + self.facing * (s + 16)), int(y - 14)), 4)
        elif style == "greninja":
            scarf = pygame.Rect(x - s - 4, y - 4, s * 2 + 8, 8)
            pygame.draw.ellipse(screen, (230, 90, 130), scarf)
            for side in (-1, 1):
                pygame.draw.polygon(screen, (160, 220, 255), [(x + side * 6, y - s + 10), (x + side * 16, y - s - 6), (x + side * 2, y - s + 2)])

    def _ability_damage(self, ab, scale=1.0, target=None):
        dmg = ab.damage * scale
        if self.hidden_trait == "RAGE" and self.trait_timer > 0:
            dmg *= 2.0
        if target is not None:
            move_type = self._move_type(ab.name)
            if move_type and move_type in self.element_types:
                dmg *= 1.2
            dmg *= self._effectiveness_multiplier(ab.name, target)
            if self.counter_move == ab.name and any(t in target.element_types for t in self.counter_targets):
                dmg *= 1.35
        return dmg

    def _spawn_ability_projectile(self, projectiles, ab, vx, vy, color, size, trail=None, piercing=False, homing=False, aoe_radius=0, target=None):
        p = Projectile(self.x, self.y, vx, vy, self._ability_damage(ab, target=target), color, size, self.team, trail or color, piercing=piercing, homing=homing, aoe_radius=aoe_radius, owner=self)
        projectiles.append(p)
        return p

    def _apply_pokemon_hit(self, target, ab, knockback_x=0, knockback_y=-200, scale=1.0):
        dmg = self._ability_damage(ab, scale=scale, target=target)
        dealt = target.take_damage(dmg, knockback_x=knockback_x, knockback_y=knockback_y, attacker=self)
        mult = self._effectiveness_multiplier(ab.name, target)
        if mult > 1.01:
            target.trait_label_txt = "SUPER EFFECTIVE!"
            target.trait_label_timer = 1.0
        elif mult < 0.99:
            target.trait_label_txt = "NOT VERY EFFECTIVE"
            target.trait_label_timer = 0.8
        return dealt

    def _spawn_quake_zone(self, x, y, color, damage, life=0.9, radius=150):
        if hasattr(self, "battle_ref"):
            self.battle_ref.shake = max(self.battle_ref.shake, 14)
            self.battle_ref.add_field_effect(
                "quake",
                x,
                y,
                color,
                life,
                radius=radius,
                owner_team=self.team,
                damage=damage,
                secondary=SILVER,
                spin=0.0,
                interval=0.18,
            )

    def _handle_legendary_move(self, name, ab, target, projectiles, ndx, ndy, dist):
        attack_angle = math.atan2(ndy, ndx)
        if name in {"Roost", "Recover", "Moonlight", "Jungle Healing"}:
            heal_frac = 0.26 if name == "Roost" else 0.34 if name in {"Recover", "Jungle Healing"} else 0.3
            self.heal(self.max_hp * heal_frac)
            self.invincible_timer = max(self.invincible_timer, 0.55)
            self.particles.emit_ring(self.x, self.y, ab.color, count=24, speed=120, size=6, life=0.6)
            return True

        if name in {"Calm Mind", "Cosmic Power", "Geomancy", "Iron Defense", "Tail Glow"}:
            self.damage_mult += 0.18 if name not in {"Geomancy", "Tail Glow"} else 0.28
            self.invincible_timer = max(self.invincible_timer, 0.35 if name != "Iron Defense" else 0.6)
            self.heal(self.max_hp * (0.08 if name != "Geomancy" else 0.14))
            self.particles.emit_ring(self.x, self.y, ab.color, count=28, speed=110, size=7, life=0.8)
            return True

        if name in {"Blizzard", "Heat Wave", "Fiery Wrath", "Astral Barrage", "Hurricane", "Dark Void", "Diamond Storm", "Hyperspace Hole", "Hyperspace Fury", "Steam Eruption", "Seed Flare", "Judgment", "Searing Shot"}:
            self.particles.emit_ring(target.x, target.y, ab.color, count=32, speed=180, size=6, life=0.7)
            if hasattr(self, "battle_ref"):
                effect_type = "cloud" if name in {"Blizzard", "Fiery Wrath", "Astral Barrage", "Dark Void", "Steam Eruption"} else "field"
                secondary = WHITE if name == "Blizzard" else RED
                if name == "Fiery Wrath":
                    secondary = PURPLE
                    self.battle_ref.impact_flash = max(self.battle_ref.impact_flash, 0.04)
                elif name == "Astral Barrage":
                    secondary = (220, 180, 255)
                    self.battle_ref.impact_flash = max(self.battle_ref.impact_flash, 0.06)
                elif name == "Hurricane":
                    secondary = CYAN
                self.battle_ref.add_field_effect(effect_type, target.x, target.y, ab.color, 2.8,
                                                 radius=100, owner_team=self.team, damage=ab.damage,
                                                 secondary=secondary, spin=1.2 if name != "Hurricane" else 3.8, interval=0.3)
            if name == "Fiery Wrath":
                self.particles.emit_beam(self.x, self.y, target.x, target.y, CRIMSON, count=18, size=4, life=0.3)
                self.particles.emit_ring(target.x, target.y, PURPLE, count=18, speed=150, size=5, life=0.5)
            elif name == "Astral Barrage":
                for i in range(4):
                    ox = target.x + random.uniform(-70, 70)
                    oy = target.y + random.uniform(-70, 70)
                    self.particles.emit_beam(self.x, self.y, ox, oy, (205, 180, 255), count=12, size=3, life=0.25)
            elif name == "Hurricane":
                for i in range(3):
                    arc_angle = attack_angle + i * 2.1
                    self.particles.emit(self.x + math.cos(arc_angle) * 30, self.y + math.sin(arc_angle) * 30,
                                        CYAN, count=6, speed=180, size=4, life=0.45, gravity=False,
                                        direction=arc_angle + math.pi * 0.5)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, knockback_x=ndx*180, knockback_y=-180)
                if name in {"Blizzard", "Hurricane"}:
                    target.stun_timer = max(target.stun_timer, 0.35)
            return True

        if name in {"Thunder", "Psystrike", "Aura Sphere", "Aeroblast", "Ancient Power", "Moonblast", "Blue Flare", "Photon Geyser", "Dynamax Cannon", "Dazzling Gleam", "Mystical Fire", "Oblivion Wing", "Thunder Cage", "Psycho Boost", "Water Pulse", "Relic Song", "Techno Blast", "Fleur Cannon", "Focus Blast", "Dark Pulse", "Ice Beam", "Surf"}:
            if name == "Thunder":
                self.particles.emit_beam(target.x, target.y - 180, target.x, target.y, ab.color, count=22, size=4, life=0.28)
                if dist < ab.range:
                    self._apply_pokemon_hit(target, ab, knockback_x=ndx*100, knockback_y=-260)
                    target.stun_timer = max(target.stun_timer, 0.5)
                return True
            if name == "Thunder Cage":
                self.particles.emit_trap(target.x, target.y, ab.color, size=90, count=18)
                if hasattr(self, "battle_ref"):
                    self.battle_ref.add_field_effect("cage", target.x, target.y, ab.color, 2.6,
                                                     radius=78, owner_team=self.team, damage=ab.damage,
                                                     secondary=WHITE, spin=1.4, interval=0.28)
                if dist < ab.range:
                    self._apply_pokemon_hit(target, ab, knockback_x=ndx*120, knockback_y=-120)
                return True
            if name == "Dazzling Gleam":
                self.particles.emit_ring(self.x, self.y, ab.color, count=26, speed=200, size=5, life=0.4)
                if dist < ab.range:
                    self._apply_pokemon_hit(target, ab, knockback_x=ndx*140, knockback_y=-160)
                return True
            if name == "Blue Flare":
                self.particles.emit_ring(self.x, self.y, CYAN, count=18, speed=140, size=5, life=0.4)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, CYAN, count=14, size=3, life=0.22)
                self.particles.emit_ring(target.x, target.y, WHITE, count=18, speed=210, size=6, life=0.3)
                self._spawn_ability_projectile(projectiles, ab, ndx*500, ndy*500, CYAN, 10, trail=WHITE, aoe_radius=70, target=target)
                return True
            if name == "Photon Geyser":
                for i in range(3):
                    off = (i - 1) * 12
                    self.particles.emit_beam(self.x, self.y + off, target.x, target.y - off, WHITE, count=12, size=3, life=0.25)
                self.particles.emit_ring(self.x, self.y, GOLD, count=10, speed=70, size=6, life=0.45)
                self.particles.emit_ring(target.x, target.y, WHITE, count=16, speed=180, size=5, life=0.35)
                self._spawn_ability_projectile(projectiles, ab, ndx*560, ndy*560, WHITE, 9, trail=GOLD, piercing=True, target=target)
                return True
            if name == "Dynamax Cannon":
                self.particles.emit_beam(self.x, self.y, target.x, target.y, PINK, count=28, size=4, life=0.3)
                if hasattr(self, "battle_ref"):
                    self.battle_ref.impact_flash = max(self.battle_ref.impact_flash, 0.08)
                    self.battle_ref.shake = min(18.0, self.battle_ref.shake + 3.0)
                self._spawn_ability_projectile(projectiles, ab, ndx*620, ndy*620, PINK, 11, trail=CYAN, piercing=True, aoe_radius=85, target=target)
                return True
            if name == "Oblivion Wing":
                self.particles.emit_slash(self.x, self.y, attack_angle - 0.35, ab.color, size=int(self.size * 2.4), count=10)
                self.particles.emit_slash(self.x, self.y, attack_angle + 0.35, ab.color, size=int(self.size * 2.4), count=10)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, ab.color, count=18, size=4, life=0.35)
                if dist < ab.range:
                    dealt = self._apply_pokemon_hit(target, ab, knockback_x=ndx*160, knockback_y=-180)
                    self.heal(dealt * 0.55)
                return True
            if name == "Moongeist Beam":
                self.particles.emit_ring(self.x, self.y, (200, 190, 255), count=14, speed=90, size=5, life=0.4)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, (190, 180, 255), count=24, size=4, life=0.28)
                if dist < ab.range:
                    self._apply_pokemon_hit(target, ab, knockback_x=ndx*220, knockback_y=-240)
                return True
            trail = WHITE if name in {"Aeroblast", "Moonblast", "Dazzling Gleam"} else CYAN if name == "Dynamax Cannon" else None
            self._spawn_ability_projectile(projectiles, ab, ndx*520, ndy*520, ab.color, 8 if ab.damage >= 100 else 7, trail=trail, target=target)
            return True

        if name in {"Sacred Fire", "Origin Pulse"}:
            self.particles.emit_ring(self.x, self.y, ab.color, count=20, speed=160, size=5, life=0.45)
            for i in range(3):
                angle = math.atan2(ndy, ndx) + (i - 1) * (0.2 if name == "Origin Pulse" else 0.1)
                vx = math.cos(angle) * (460 if name == "Origin Pulse" else 420)
                vy = math.sin(angle) * (460 if name == "Origin Pulse" else 420)
                self._spawn_ability_projectile(projectiles, ab, vx, vy, ab.color, 8 if name == "Origin Pulse" else 7, trail=WHITE, target=target)
            return True

        if name in {"Precipice Blades", "Earth Power", "Thousand Arrows"}:
            self._spawn_quake_zone(target.x, target.y, ab.color, ab.damage, life=1.05 if name == "Precipice Blades" else 0.85, radius=165 if name == "Precipice Blades" else 135)
            if name == "Precipice Blades":
                for i in range(5):
                    px = target.x - 80 + i * 40
                    self.particles.emit_beam(px, target.y + 70, px + random.uniform(-10, 10), target.y - 40, BROWN, count=8, size=4, life=0.35)
            elif name == "Thousand Arrows":
                for i in range(6):
                    ang = attack_angle + (i - 2.5) * 0.18
                    self.particles.emit_beam(self.x, self.y, self.x + math.cos(ang) * 160, self.y + math.sin(ang) * 160, GREEN, count=8, size=3, life=0.25)
            if dist < ab.range * 1.4:
                self._apply_pokemon_hit(target, ab, knockback_x=ndx*320, knockback_y=-220)
                target.stun_timer = max(target.stun_timer, 0.45)
            return True

        if name in {"Dragon Ascent", "Sacred Sword", "Shadow Force", "Sunsteel Strike", "Thunderous Kick", "Play Rough", "Behemoth Blade", "Behemoth Bash", "Wicked Blow", "Glacial Lance", "Horn Leech", "Iron Head", "Secret Sword", "V-create", "Double Iron Bash", "Plasma Fists", "Spectral Thief"}:
            if name == "Behemoth Blade":
                self.particles.emit_slash(self.x, self.y, attack_angle, WHITE, size=int(self.size * 3.2), count=22)
                self.particles.emit_slash(self.x, self.y, attack_angle + 0.12, CYAN, size=int(self.size * 3.6), count=18)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, CYAN, count=14, size=3, life=0.2)
            elif name == "Behemoth Bash":
                self.particles.emit_ring(self.x, self.y, SILVER, count=20, speed=220, size=7, life=0.32)
                self.particles.emit_ring(target.x, target.y, WHITE, count=14, speed=140, size=5, life=0.25)
            elif name == "Sunsteel Strike":
                self.particles.emit_ring(self.x, self.y, GOLD, count=24, speed=180, size=7, life=0.28)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, WHITE, count=18, size=4, life=0.2)
            elif name == "Shadow Force":
                self._spawn_afterimages(7, color=(170, 120, 255), spread=28)
                self.invincible_timer = max(self.invincible_timer, 0.2)
            elif name == "Thunderous Kick":
                self.particles.emit_beam(self.x, self.y, target.x, target.y, YELLOW, count=10, size=3, life=0.18)
            elif name == "Glacial Lance":
                self.particles.emit_beam(self.x, self.y, target.x, target.y, (180, 240, 255), count=12, size=4, life=0.26)
                self.particles.emit_ring(target.x, target.y, WHITE, count=12, speed=110, size=5, life=0.4)
            self.body.velocity = (ndx * 860, ndy * 260 - 120)
            self.particles.emit_slash(self.x, self.y, attack_angle, ab.color, size=int(self.size * 2.4), count=16)
            if dist < ab.range * 1.25:
                dealt = self._apply_pokemon_hit(target, ab, knockback_x=ndx*520, knockback_y=-300)
                if name in {"Thunderous Kick", "Glacial Lance"}:
                    target.stun_timer = max(target.stun_timer, 0.35)
                if name in {"Behemoth Blade", "Behemoth Bash", "Sunsteel Strike"} and hasattr(self, "battle_ref"):
                    self.battle_ref.shake = min(20.0, self.battle_ref.shake + 4.5)
                    self.battle_ref.impact_flash = max(self.battle_ref.impact_flash, 0.06)
                if name == "Horn Leech":
                    self.heal(dealt * 0.45)
            return True

        if name in {"Roar of Time", "Spacial Rend", "Dragon Energy", "Moongeist Beam", "Nature's Madness", "Doom Desire", "Magical Leaf", "Air Slash", "Energy Ball"}:
            if name == "Nature's Madness":
                self.particles.emit_ring(target.x, target.y, ab.color, count=22, speed=160, size=5, life=0.5)
                if dist < ab.range:
                    self._apply_pokemon_hit(target, ab, knockback_x=ndx*180, knockback_y=-120)
                return True
            if name == "Roar of Time":
                self.particles.emit_ring(self.x, self.y, (160, 210, 255), count=14, speed=80, size=7, life=0.5)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, (150, 220, 255), count=32, size=5, life=0.34)
                if hasattr(self, "battle_ref"):
                    self.battle_ref.impact_flash = max(self.battle_ref.impact_flash, 0.05)
            elif name == "Spacial Rend":
                for offset in (-16, 0, 16):
                    self.particles.emit_beam(self.x - ndy * offset, self.y + ndx * offset,
                                             target.x - ndy * offset, target.y + ndx * offset,
                                             PINK, count=12, size=3, life=0.22)
                self.particles.emit_slash(target.x, target.y, attack_angle + math.pi * 0.5, PINK, size=70, count=10)
            elif name == "Dragon Energy":
                self.particles.emit_ring(self.x, self.y, GREEN, count=16, speed=100, size=6, life=0.45)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, GREEN, count=28, size=4, life=0.3)
            elif name == "Moongeist Beam":
                self.particles.emit_ring(self.x, self.y, (210, 200, 255), count=10, speed=65, size=7, life=0.4)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, (190, 180, 255), count=30, size=4, life=0.3)
            else:
                self.particles.emit_beam(self.x, self.y, target.x, target.y, ab.color, count=26, size=4, life=0.3)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, knockback_x=ndx*220, knockback_y=-240)
            return True

        return False

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
            
            # ── IMPACT PARTICLES ──
            self.particles.emit_impact(self.x, self.y, RED if dmg > 40 else (WHITE if random.random()<0.5 else self.color), count=int(dmg/10)+5)
            for _ in range(3):
                sang = random.uniform(0, math.pi*2)
                self.particles.emit_beam(self.x, self.y, self.x + math.cos(sang)*50, self.y + math.sin(sang)*50, WHITE, count=4)

            self.battle_ref.sounds.play('hit')

        self.hit_flash = 0.3
        self.invincible_timer = 0.15
        
        # ── RE-ENGAGEMENT AI ──
        if dmg > 10:
            self.ai_state = "scramble"
            self.ai_timer = random.uniform(0.6, 1.1) # Time before re-engaging
        
        # ── DYNAMIC KNOCKBACK ENHANCEMENT ──
        if attacker and knockback_x == 0:
            kb_dx = self.x - attacker.x
            if kb_dx == 0: kb_dx = random.choice([-1, 1])
            knockback_x = (kb_dx/abs(kb_dx)) * 380
        
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
                impact = "thud"
            elif self.x > r.right - margin:
                self.body.position = (r.right - margin - 2, self.body.position.y)
                impulse_x = -1200
                impact = "thud"
                
            if self.y < r.top + margin:
                self.body.position = (self.body.position.x, r.top + margin + 2)
                impulse_y = 1200
                if not impact: impact = "thud"
            elif self.y > r.bottom - margin:
                self.body.position = (self.body.position.x, r.bottom - margin - 2)
                impulse_y = -1800 
                impact = "jump"

            if impact:
                self.body.apply_impulse_at_local_point((impulse_x, impulse_y))
                self.particles.emit_ring(self.x, self.y, SILVER, count=12, speed=350, size=6, life=0.5)
                if hasattr(self.battle_ref, 'sounds'): self.battle_ref.sounds.play(impact)
                self.ai_timer = max(self.ai_timer, 0.4)
                self.body.velocity *= 1.3

        # Timers
        self.hit_flash = max(0, self.hit_flash - dt)
        self.invincible_timer = max(0, self.invincible_timer - dt)
        self.stun_timer = max(0, self.stun_timer - dt)
        self.ai_timer  = max(0, self.ai_timer  - dt)
        self.collision_recover_timer = max(0, self.collision_recover_timer - dt)
        self.cast_flash_timer = max(0, self.cast_flash_timer - dt)
        self.cast_ring_timer = max(0, self.cast_ring_timer - dt)
        updated_afterimages = []
        for img in self.afterimages:
            img["life"] -= dt
            img["y"] -= 10 * dt
            if img["life"] > 0:
                updated_afterimages.append(img)
        self.afterimages = updated_afterimages
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
        t_aim = self.ai_target
        t_move = self.ai_target
        
        # Distance to actual enemy for combat logic
        aim_dx, aim_dy = t_aim.x - self.x, t_aim.y - self.y
        aim_dist = max(1, math.hypot(aim_dx, aim_dy))
        
        # ── STRATEGIC CONTENTION: POWER-UP FOCUS ──
        if hasattr(self, 'battle_ref') and getattr(self.battle_ref, 'powerups', None):
            visible_pu = [pu for pu in self.battle_ref.powerups if math.hypot(pu.x-self.x, pu.y-self.y) < 450]
            if visible_pu:
                # We see the shiny! Steer towards it instead of enemy
                t_move = min(visible_pu, key=lambda p: math.hypot(p.x-self.x, p.y-self.y))
        
        dx, dy = t_move.x - self.x, t_move.y - self.y
        dist  = max(1, math.hypot(dx, dy)) # Movement distance
        ndx, ndy = dx/dist, dy/dist
        self.facing = 1 if aim_dx > 0 else -1 # Keep facing enemy for attacks

        low_hp = self.hp < self.max_hp * 0.35  # Only truly low HP triggers retreat
        has_ranged = any(ab.range > 220 for ab in self.abilities)

        # ── ABILITY SELECTION — ALWAYS TRY TO ATTACK ──
        best_ab = None
        ready_abs = [ab for ab in self.abilities if ab.ready()]

        # Priority 1: Heals only when critically low
        heals = [ab for ab in ready_abs if ab.damage == 0]
        if heals and self.hp < self.max_hp * 0.5:
            best_ab = heals[0]

        # Priority 2: Use ANY ready ability in range (ranged preferred)
        if not best_ab:
            # Expand range check: ranged can fire at full range, melee gets a 1.5x leniency buffer
            in_range = []
            for ab in ready_abs:
                effective_range = ab.range if ab.range > 150 else ab.range * 2.0
                if aim_dist <= effective_range:
                    in_range.append(ab)
            if in_range:
                best_ab = max(in_range, key=lambda a: a.damage)

        # Priority 3: If nothing in range but we have ready abilities, pick the highest damage anyway
        # (the ability code will still fire particles/effects and some have no range check)
        if not best_ab and ready_abs:
            best_ab = max(ready_abs, key=lambda a: a.damage)
            # Only use it if we're close enough that it makes sense (within 2x max range)
            max_range = max(ab.range for ab in ready_abs)
            if aim_dist > max_range * 2.5:
                best_ab = None  # Too far away, just move closer

        if self.ai_timer <= 0:
            self.ai_timer = random.uniform(0.15, 0.35)  # Faster decision making
            if best_ab:
                self._use_ability(best_ab, t_aim, projectiles)
                best_ab.use()
                # After using ability, always approach so the next one lands
                if best_ab.range < 200:
                    self.ai_state = "approach"
            else:
                # No ability ready — aggressively close the distance
                self.ai_state = "approach" if dist > 200 else random.choice(["approach", "strafe"])

        # ── DYNAMIC DODGING (reduced frequency, don't interrupt attacks) ──
        dodge_chance = 0.03  # Reduced from 0.08 so AI doesn't constantly dodge instead of attack
        if low_hp:
            dodge_chance = 0.12
        
        # Only dodge if AI timer is not about to fire
        if (self.ai_state == "jump_over" or random.random() < dodge_chance) and dist < 300:
            side = random.choice([1, -1])
            angle_off = random.uniform(math.pi/4, math.pi/3) * side
            dash_vel = pygame.Vector2(ndx, ndy).rotate_rad(angle_off) * self.speed * 3.0
            self.body.apply_impulse_at_local_point((dash_vel.x, dash_vel.y))
            self.ai_timer = max(self.ai_timer, 0.2)  # Short pause only
            if low_hp: self.ai_state = "strafe"

        # ── MOVEMENT ──
        move_vec = pygame.Vector2(0, 0)
        if self.ai_state == "scramble":
            # Tactical retreat: move away and regroup
            move_vec = pygame.Vector2(-ndx, -ndy).rotate_rad(random.uniform(-0.4, 0.4))
            if random.random() < 0.05:
                # Random tactical jump away
                self.body.apply_impulse_at_local_point((0, -450))
        elif self.ai_state == "approach" or not low_hp:
            move_vec = pygame.Vector2(ndx, ndy)
        elif self.ai_state == "strafe":
            move_vec = pygame.Vector2(-ndy, ndx).rotate_rad(random.uniform(-0.2, 0.2))
            if low_hp and has_ranged:
                move_vec += pygame.Vector2(-ndx, -ndy) * 0.6
            else:
                move_vec += pygame.Vector2(ndx, ndy) * 0.7  # Drift toward enemy while strafing

        # ── ANTI-CAMPING STEERING ──
        # Dynamically push away from ALL walls, pillars, and corners
        if hasattr(self, 'battle_ref') and getattr(self.battle_ref, 'walls', None):
            repel_vec = pygame.Vector2(0, 0)
            for w in self.battle_ref.walls:
                if hasattr(w, 'a') and hasattr(w, 'b'): # pymunk.Segment
                    p1 = pygame.Vector2(w.a.x, w.a.y)
                    p2 = pygame.Vector2(w.b.x, w.b.y)
                    line_vec = p2 - p1
                    pt_vec = pygame.Vector2(self.x, self.y) - p1
                    line_len = line_vec.length()
                    if line_len > 0:
                        proj = pt_vec.dot(line_vec) / line_len
                        proj = max(0, min(line_len, proj))
                        closest_pt = p1 + (line_vec / line_len) * proj
                        dist_to_wall = math.hypot(self.x - closest_pt.x, self.y - closest_pt.y)
                        avoid_dist = 180 # Stay well away from edges
                        if dist_to_wall < avoid_dist:
                            push_dir = pygame.Vector2(self.x - closest_pt.x, self.y - closest_pt.y)
                            if push_dir.length() > 0:
                                repel_vec += push_dir.normalize() * ((avoid_dist - dist_to_wall) / avoid_dist)
                
                elif hasattr(w, 'radius'): # pymunk.Circle (Pillars)
                    px = w.body.position.x + getattr(w, 'offset', pygame.Vector2(0,0)).x
                    py = w.body.position.y + getattr(w, 'offset', pygame.Vector2(0,0)).y
                    dist_to_pillar = math.hypot(self.x - px, self.y - py)
                    avoid_dist = w.radius + 140
                    if dist_to_pillar < avoid_dist:
                        push_dir = pygame.Vector2(self.x - px, self.y - py)
                        if push_dir.length() > 0:
                            repel_vec += push_dir.normalize() * ((avoid_dist - dist_to_pillar) / avoid_dist) * 1.5
                            
            if repel_vec.length() > 0:
                # Add strong repulsive force to the movement vector
                move_vec += repel_vec * 1.5

        if move_vec.length() > 0:
            move_vec = move_vec.normalize() * self.speed
            self.body.velocity += (move_vec - self.body.velocity) * 0.30  # Slightly snappier

        # Always re-approach if drifted too far from target
        if dist > 600 and not (low_hp and has_ranged):
            self.ai_state = "approach"


    def _use_ability(self, ab, target, projectiles):
        dx = target.x - self.x
        dy = target.y - self.y
        dist = max(1, math.hypot(dx, dy))
        ndx, ndy = dx/dist, dy/dist
        self._trigger_ability_visual(ab, target, ndx, ndy, dist)

        # ── DASH FORWARD (Attack Lunge) ──
        if ab.range < 170: # Melee lunge
            self.body.velocity = (ndx * 750, ndy * 300)
            self.particles.emit_slash(self.x, self.y, math.atan2(ndy, ndx), ab.color, size=int(self.size)+10)
        elif ab.range > 300: # Muzzle flash for ranged
            self.particles.emit(self.x + ndx*20, self.y + ndy*20, ab.color, count=8, speed=200, spread=0.5, direction=math.atan2(ndy, ndx))

        name = ab.name

        if self._handle_legendary_move(name, ab, target, projectiles, ndx, ndy, dist):
            return

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cloud", self.x + ndx*40, self.y, (90,90,100), 3.4,
                                                 radius=70, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=0.8, interval=0.5)
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
            self.particles.emit_beam(self.x, self.y, self.x+ndx*ab.range, self.y+ndy*ab.range, CRIMSON, count=20, size=6)
            for i in range(5):
                off = (i-2)*10
                self.particles.emit(self.x + ndx*50 + (-ndy*off), self.y + ndy*50 + (ndx*off), CRIMSON, count=5, speed=150)
            if dist < ab.range:
                stolen = target.take_damage(ab.damage, knockback_x=ndx*250, attacker=self)
                self.heal(stolen * 0.3)

        elif name == "Hell Spike":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            # Throws stationary spikes onto the stage that hurt enemies when they step on them
            for _ in range(5):
                dist_throw = random.uniform(40, ab.range)
                angle = math.atan2(ndy, ndx) + random.uniform(-0.7, 0.7)
                px = self.x + math.cos(angle) * dist_throw
                py = self.y + math.sin(angle) * dist_throw
                p = Projectile(px, py, 0, 0,
                              ab.damage // 2, (150,0,50), 10, self.team,
                              CRIMSON, homing=False)
                projectiles.append(p)
                # Visual appearance effect
                self.particles.emit(px, py, CRIMSON, count=15, speed=80, size=5, gravity=False)
                self.particles.emit_ring(px, py, (100, 0, 30), count=8, speed=30, size=6)

        elif name == "Soul Drain":
            self.particles.emit_beam(self.x, self.y, target.x, target.y,
                                    PURPLE, count=20, life=0.5)
            # Make the character glow while draining life
            self.particles.emit_ring(self.x, self.y, PURPLE, count=20, speed=40, size=7, life=0.6)
            self.particles.emit(self.x, self.y, PINK, count=10, speed=15, size=8, life=0.5, gravity=False)
            if dist < ab.range:
                stolen = target.take_damage(ab.damage, attacker=self)
                self.heal(stolen * 0.8)
                target.particles.emit_ring(target.x, target.y, PURPLE, count=10, speed=60, size=4)

        elif name == "Hellfire":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(6):
                px = target.x + random.uniform(-120, 120)
                p = Projectile(px, -30, 0, 500, ab.damage//6,
                              RED, 10, self.team, ORANGE)
                p.gravity_affected = False
                projectiles.append(p)
                # Show landing indicator
                self.particles.emit_ring(px, target.y + random.uniform(-20, 20), ORANGE, count=15, speed=40, size=5)

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("vortex", target.x, target.y, TEAL, 4.5,
                                                 radius=85, owner_team=self.team, damage=ab.damage,
                                                 secondary=CYAN, spin=3.8, interval=0.45)
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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("field", target.x, target.y, BLUE, 4.8,
                                                 radius=140, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=2.5, interval=0.55)

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, PURPLE, 4.2,
                                                 radius=75, owner_team=self.team, damage=dmg,
                                                 secondary=PINK, spin=3.0, interval=0.45)

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cage", target.x, target.y, WHITE, 4.5,
                                                 radius=95, owner_team=self.team, damage=dmg,
                                                 secondary=BLUE, spin=1.6, interval=0.55)

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
            if hasattr(self, 'battle_ref'):
                mx = self.x + ndx*70
                my = self.y + ndy*40
                self.battle_ref.add_field_effect("mine", mx, my, GREEN, 5.0,
                                                 radius=68, owner_team=self.team, damage=ab.damage,
                                                 secondary=LIME, spin=1.2, interval=0.35)
                self.battle_ref.add_field_effect("cloud", mx, my, GREEN, 3.0,
                                                 radius=80, owner_team=self.team, damage=ab.damage,
                                                 secondary=LIME, spin=0.7, interval=0.6)
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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("ritual", target.x, target.y, PURPLE, 4.2,
                                                 radius=90, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=2.0, interval=0.55)
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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, BLACK, 4.4,
                                                 radius=72, owner_team=self.team, damage=ab.damage,
                                                 secondary=BROWN, spin=4.6, interval=0.4)
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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("vortex", target.x, target.y, BLUE, 5.2,
                                                 radius=125, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=4.5, interval=0.4)
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
            if hasattr(self, 'battle_ref'):
                for i in range(2):
                    ang = i * math.pi
                    self.battle_ref.add_field_effect("clone", self.x + math.cos(ang)*65, self.y + math.sin(ang)*30,
                                                     GREEN, 3.2, owner_team=self.team, damage=ab.damage,
                                                     secondary=WHITE, spin=1.5, interval=0.9)

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cage", target.x, target.y, BROWN, 4.0,
                                                 radius=82, owner_team=self.team, damage=ab.damage,
                                                 secondary=GREEN, spin=1.0, interval=0.55)
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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, TEAL, 3.8,
                                                 radius=78, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=2.4, interval=0.4)

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
            self._spawn_quake_zone(self.x, self.y, BROWN, ab.damage, life=1.05, radius=150)
            if dist < ab.range * 1.4:
                target.take_damage(self._ability_damage(ab), ndx*500, -260, attacker=self)
                target.stun_timer = 1.2

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, BROWN, 4.8,
                                                 radius=88, owner_team=self.team, damage=ab.damage,
                                                 secondary=GREEN, spin=3.2, interval=0.4)
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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("mothership", target.x, 90, LIME, 5.2,
                                                 owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=1.1, interval=0.55,
                                                 target_x=target.x)

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
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, BLUE, 4.6,
                                                 radius=110, owner_team=self.team, damage=ab.damage,
                                                 secondary=TEAL, spin=1.9, interval=0.4)
                self.battle_ref.add_field_effect("field", target.x, target.y, TEAL, 3.8,
                                                 radius=105, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=1.3, interval=0.5)
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

        # ── PHANTOM ──
        elif name == "Phase Blink":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit(self.x, self.y, PURPLE, count=20, speed=200, life=0.4, gravity=False)
            self.body.position = (target.x - self.facing*50, target.y + random.uniform(-30,30))
            self.particles.emit(self.x, self.y, (180,100,255), count=20, speed=150, gravity=False)
            if dist < ab.range: target.take_damage(ab.damage, ndx*300, attacker=self)

        elif name == "Ghost Strike":
            self.invincible_timer = 0.5  # Brief phase
            self.particles.emit_beam(self.x, self.y, target.x, target.y, PURPLE, count=20)
            if dist < ab.range: target.take_damage(ab.damage, ndx*400, attacker=self)

        elif name == "Void Step":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(3):
                fx = target.x + random.uniform(-120, 120)
                fy = target.y + random.uniform(-60, 60)
                self.particles.emit_ring(fx, fy, (180,100,255), count=15, speed=120, size=5)
            self.body.position = (target.x + self.facing*40, target.y)
            target.take_damage(ab.damage, ndx*300, attacker=self)
            target.stun_timer = 0.8

        elif name == "Phantom Surge":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for i in range(6):
                px = target.x + random.uniform(-150, 150)
                py = target.y + random.uniform(-80, 80)
                self.particles.emit_ring(px, py, (180,100,255), count=20, speed=200, size=8)
                self.particles.emit(px, py, WHITE, count=10, speed=100)
            target.take_damage(ab.damage, ndx*600, -400, attacker=self)

        # ── TIME-LORD ──
        elif name == "Time Bolt":
            p = Projectile(self.x, self.y, ndx*500, ndy*500, ab.damage, GOLD, 8, self.team, YELLOW)
            projectiles.append(p)

        elif name == "Slow Field":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(target.x, target.y, YELLOW, count=30, speed=80, size=6, life=1.5)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("field", target.x, target.y, YELLOW, 4.0,
                                                 radius=88, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=1.8, interval=0.45)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.stun_timer = 2.0  # "Slow" = stun
                target.body.velocity = (target.body.velocity.x * 0.2, target.body.velocity.y * 0.2)

        elif name == "Rewind":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('heal')
            heal_amt = self.max_hp * 0.35  # Rewind ~35% HP
            self.heal(heal_amt)
            self.particles.emit_ring(self.x, self.y, CYAN, count=40, speed=200, size=8)
            for _ in range(3):
                self.particles.emit_ring(self.x, self.y, GOLD, count=20, speed=100+_*80, size=6)

        elif name == "Timestop":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(target.x, target.y, WHITE, count=50, speed=400, size=10)
            target.stun_timer = 2.5
            target.take_damage(ab.damage, ndx*200, attacker=self)
            if hasattr(self, 'battle_ref'): self.battle_ref.impact_flash = 0.1

        # ── NECROMANCER ──
        elif name == "Cursed Bolt":
            p = Projectile(self.x, self.y, ndx*450, ndy*450, ab.damage, (80,200,80), 7, self.team, LIME, piercing=True)
            projectiles.append(p)

        elif name == "Death Touch":
            self.particles.emit(target.x, target.y, (50,150,50), count=20, speed=200)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.apply_dot(15, 4.0)

        elif name == "Plague Cloud":
            for _ in range(20):
                self.particles.emit(target.x + random.uniform(-80,80), target.y + random.uniform(-40,40),
                                   LIME, count=2, speed=30, size=10, life=2.0, gravity=False)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cloud", target.x, target.y, LIME, 5.0,
                                                 radius=105, owner_team=self.team, damage=ab.damage,
                                                 secondary=GREEN, spin=0.8, interval=0.45)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.apply_dot(20, 5.0)

        elif name == "Army of Dead":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(12):
                angle = random.uniform(0, math.pi*2)
                p = Projectile(self.x, self.y, math.cos(angle)*400, math.sin(angle)*400,
                              ab.damage//12, (80,200,80), 8, self.team, LIME, aoe_radius=25)
                projectiles.append(p)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, (80,200,80), 5.0,
                                                 radius=95, owner_team=self.team, damage=ab.damage,
                                                 secondary=LIME, spin=2.7, interval=0.4)

        # ── MIRROR-MAGE ──
        elif name == "Mirror Shard":
            p = Projectile(self.x, self.y, ndx*500, ndy*500, ab.damage, (200,220,255), 7, self.team, WHITE, piercing=True)
            projectiles.append(p)

        elif name == "Reflect":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.invincible_timer = 2.0
            self.particles.emit_ring(self.x, self.y, WHITE, count=30, speed=150, size=8)
            # Mirror the enemy's velocity back
            if dist < ab.range:
                rx, ry = -target.body.velocity.x, -target.body.velocity.y
                target.body.velocity = (rx, ry)
                target.take_damage(ab.damage, rx*0.3, ry*0.3, attacker=self)

        elif name == "Clone Army":
            for i in range(3):
                off = [(100, -80), (-100, -80), (0, -130)][i]
                self.particles.emit_ring(self.x + off[0], self.y + off[1],
                                        SILVER, count=20, speed=100, size=6)
            if hasattr(self, 'battle_ref'):
                for ox, oy in [(100, -80), (-100, -80), (0, -130)]:
                    self.battle_ref.add_field_effect("clone", self.x + ox, self.y + oy, SILVER, 3.6,
                                                     owner_team=self.team, damage=ab.damage,
                                                     secondary=WHITE, spin=1.2, interval=0.8)
            if dist < ab.range: target.take_damage(ab.damage, ndx*200, attacker=self)
            target.stun_timer = 1.0

        elif name == "Prism Burst":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for i in range(12):
                angle = i * (math.pi*2/12)
                p = Projectile(self.x, self.y, math.cos(angle)*500, math.sin(angle)*500,
                              ab.damage//12, (200,220,255), 6, self.team, WHITE, piercing=True)
                projectiles.append(p)

        # ── BLACK-HOLE ──
        elif name == "Gravity Pull":
            if dist < ab.range:
                pull_x = (self.x - target.x)
                pull_y = (self.y - target.y)
                target.body.velocity = (target.body.velocity.x + pull_x*3, target.body.velocity.y + pull_y*3)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, PURPLE, count=15)
                if hasattr(self, 'battle_ref'):
                    self.battle_ref.add_field_effect("vortex", (self.x + target.x) / 2, (self.y + target.y) / 2,
                                                     PURPLE, 2.8, radius=68, owner_team=self.team,
                                                     damage=ab.damage, secondary=BLACK, spin=3.4, interval=0.35)
                target.take_damage(ab.damage, attacker=self)

        elif name == "Event Horizon":
            self.particles.emit_ring(self.x, self.y, PURPLE, count=40, speed=60, size=10, life=1.0)
            if dist < ab.range:
                pull_x = self.x - target.x; pull_y = self.y - target.y
                target.body.velocity = (pull_x*2, pull_y*2)
                target.take_damage(ab.damage, attacker=self)

        elif name == "Dark Matter":
            p = Projectile(self.x, self.y, ndx*350, ndy*350, ab.damage, (50,0,80), 18, self.team, PURPLE, aoe_radius=100)
            projectiles.append(p)

        elif name == "Singularity":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, BLACK, count=60, speed=600, size=15)
            self.particles.emit_ring(self.x, self.y, PURPLE, count=40, speed=300, size=10)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("vortex", target.x, target.y, BLACK, 4.8,
                                                 radius=118, owner_team=self.team, damage=ab.damage,
                                                 secondary=PURPLE, spin=5.0, interval=0.35)
            for _ in range(3):
                target.take_damage(ab.damage//3, (self.x-target.x)*2, (self.y-target.y)*2, attacker=self)

        # ── ALCHEMIST ──
        elif name == "Acid Flask":
            p = Projectile(self.x, self.y, ndx*450, ndy*450-100, ab.damage, (150,200,50), 9, self.team, LIME)
            projectiles.append(p)
            if dist < ab.range: target.apply_dot(15, 3.0)

        elif name == "Fire Potion":
            p = Projectile(self.x, self.y, ndx*400, ndy*400-150, ab.damage, ORANGE, 10, self.team, RED, aoe_radius=60)
            projectiles.append(p)

        elif name == "Transmute":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(target.x, target.y, GOLD, count=25, speed=200, size=8)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.damage_mult = max(0.3, target.damage_mult - 0.5)
                target.stun_timer = 1.0

        elif name == "Grand Elixir":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(5):
                p = Projectile(self.x+random.uniform(-30,30), self.y,
                              ndx*400+random.uniform(-100,100), ndy*400-random.uniform(0,200),
                              ab.damage//5, PURPLE, 10, self.team, ORANGE, aoe_radius=50)
                projectiles.append(p)

        # ── MAGNETAR ──
        elif name == "Magnetic Pull":
            if dist < ab.range:
                pull_x = (self.x - target.x) * 3
                pull_y = (self.y - target.y) * 3
                target.body.velocity = (pull_x, pull_y)
                self.particles.emit_beam(self.x, self.y, target.x, target.y, BLUE, count=20, size=6)
                target.take_damage(ab.damage, attacker=self)

        elif name == "Repulse Blast":
            self.particles.emit_ring(self.x, self.y, CYAN, count=20, speed=200, size=8)
            if dist < ab.range:
                target.body.velocity = (ndx*1200, ndy*1200)
                target.take_damage(ab.damage, ndx*800, ndy*800, attacker=self)

        elif name == "Iron Storm":
            for _ in range(8):
                angle = math.atan2(ndy,ndx) + random.uniform(-0.4,0.4)
                p = Projectile(self.x, self.y, math.cos(angle)*500, math.sin(angle)*500,
                              ab.damage//8, SILVER, 6, self.team, BLUE)
                projectiles.append(p)

        elif name == "Polarity Flip":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, WHITE, count=50, speed=500, size=12)
            if dist < ab.range:
                target.body.velocity = (-target.body.velocity.x*2, -target.body.velocity.y*2)
                target.take_damage(ab.damage, -ndx*800, -ndy*600, attacker=self)

        # ── TSUNAMI ──
        elif name == "Water Jet":
            p = Projectile(self.x, self.y, ndx*700, ndy*700, ab.damage, BLUE, 8, self.team, CYAN)
            projectiles.append(p)

        elif name == "Riptide":
            self.particles.emit(self.x + ndx*100, self.y, CYAN, count=25, speed=300, direction=math.atan2(ndy,ndx))
            if dist < ab.range: target.take_damage(ab.damage, ndx*600, -200, attacker=self)

        elif name == "Wave Crash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for i in range(5):
                self.particles.emit(self.x + ndx*i*60, self.y, BLUE, count=8, speed=150, size=12)
            if dist < ab.range: target.take_damage(ab.damage, ndx*700, -300, attacker=self)

        elif name == "Mega Tsunami":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, BLUE, count=60, speed=600, size=15)
            for _ in range(8):
                angle = math.atan2(ndy,ndx) + random.uniform(-0.3,0.3)
                p = Projectile(self.x, self.y, math.cos(angle)*600, math.sin(angle)*600,
                              ab.damage//8, BLUE, 12, self.team, CYAN, aoe_radius=40)
                projectiles.append(p)

        # ── BOUNTY-HUNTER ──
        elif name == "Stun Dart":
            p = Projectile(self.x, self.y, ndx*750, ndy*750, ab.damage, BROWN, 5, self.team, GOLD)
            projectiles.append(p)
            if dist < ab.range: target.stun_timer = 0.8

        elif name == "Trip Mine":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            # Plant mine near enemy
            mx = target.x + random.uniform(-60,60)
            my = target.y + random.uniform(-60,60)
            p = Projectile(mx, my, 0, 0, ab.damage, ORANGE, 12, self.team, RED, aoe_radius=80)
            projectiles.append(p)
            self.particles.emit_ring(mx, my, ORANGE, count=15, speed=50, size=6)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("mine", mx, my, ORANGE, 4.4,
                                                 radius=85, owner_team=self.team, damage=ab.damage,
                                                 secondary=RED, spin=1.4, interval=0.3)

        elif name == "Headshot":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, SILVER, count=15, size=4, life=0.2)
            target.take_damage(ab.damage, ndx*400, attacker=self)
            target.stun_timer = 1.0

        elif name == "Obliterate":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for i in range(10):
                p = Projectile(self.x, self.y, ndx*700+random.uniform(-80,80), ndy*700+random.uniform(-80,80)-i*30,
                              ab.damage//10, RED, 6, self.team, ORANGE, homing=True)
                projectiles.append(p)

        # ── CRYSTAL-WITCH ──
        elif name == "Crystal Bolt":
            p = Projectile(self.x, self.y, ndx*500, ndy*500, ab.damage, (180,80,220), 7, self.team, PINK, piercing=True)
            projectiles.append(p)

        elif name == "Hex Curse":
            self.particles.emit_beam(self.x, self.y, target.x, target.y, PINK, count=20, size=4)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.dodge_rate = max(0, target.dodge_rate - 0.2)
                target.stun_timer = 0.6

        elif name == "Crystal Cage":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_trap(target.x, target.y, (180,80,220), size=80, count=20)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cage", target.x, target.y, (180,80,220), 4.6,
                                                 radius=92, owner_team=self.team, damage=ab.damage,
                                                 secondary=WHITE, spin=1.5, interval=0.5)
            if dist < ab.range:
                target.take_damage(ab.damage, attacker=self)
                target.stun_timer = 2.5

        elif name == "Dark Ritual":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.take_damage(self.max_hp * 0.15)  # Self-sacrifice
            self.particles.emit_ring(self.x, self.y, (100,0,150), count=50, speed=400, size=12)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("ritual", self.x, self.y, (100,0,150), 5.0,
                                                 radius=110, owner_team=self.team, damage=ab.damage,
                                                 secondary=PINK, spin=2.8, interval=0.45)
            target.take_damage(ab.damage, ndx*500, -400, attacker=self)
            target.apply_dot(25, 5.0)

        # ── LAVA-TITAN ──
        elif name == "Lava Fist":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            self.particles.emit(self.x + ndx*60, self.y, ORANGE, count=15, speed=200, size=8)
            if dist < ab.range:
                target.take_damage(ab.damage, ndx*400, attacker=self)
                target.apply_dot(10, 2.0)

        elif name == "Magma Hurl":
            p = Projectile(self.x, self.y, ndx*400, ndy*400-150, ab.damage, RED, 14, self.team, ORANGE, aoe_radius=70)
            projectiles.append(p)

        elif name == "Eruption":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, GOLD, count=30, speed=300, size=12)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("field", self.x, self.y, ORANGE, 3.6,
                                                 radius=130, owner_team=self.team, damage=ab.damage,
                                                 secondary=RED, spin=2.0, interval=0.4)
            for _ in range(6):
                px = self.x + random.uniform(-120,120)
                p = Projectile(px, -30, 0, 600, ab.damage//6, ORANGE, 10, self.team, RED)
                p.gravity_affected = False
                projectiles.append(p)

        elif name == "Caldera":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(15):
                px = target.x + random.uniform(-200,200)
                p = Projectile(px, -50, 0, 700, ab.damage//15, (220,80,20), 12, self.team, ORANGE, aoe_radius=50)
                p.gravity_affected = False
                projectiles.append(p)

        # ── PSIONIC ──
        elif name == "Mind Bolt":
            p = Projectile(self.x, self.y, ndx*550, ndy*550, ab.damage, PINK, 7, self.team, (180,100,220))
            projectiles.append(p)

        elif name == "Telekinesis":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, (180,100,220), count=20, size=5)
            if dist < ab.range:
                r = self.battle_ref.arena_rect if hasattr(self,'battle_ref') else None
                if r:
                    # Fling toward opposite wall
                    cx, cy = r.centerx, r.centery
                    fling_x = (target.x - cx) * 8
                    fling_y = (target.y - cy) * 8
                    target.body.velocity = (fling_x, fling_y)
                target.take_damage(ab.damage, ndx*200, attacker=self)

        elif name == "Mind Crush":
            self.particles.emit_ring(target.x, target.y, PURPLE, count=30, speed=200, size=8)
            if dist < ab.range:
                target.take_damage(ab.damage, 0, -300, attacker=self)
                target.stun_timer = 1.5

        elif name == "Psionic Storm":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(10):
                angle = random.uniform(0, math.pi*2)
                p = Projectile(target.x, target.y, math.cos(angle)*400, math.sin(angle)*400,
                              ab.damage//10, (180,100,220), 7, self.team, PINK, homing=True)
                projectiles.append(p)

        # ── WEREWOLF ──
        elif name == "Rend":
            for i in range(3):
                off = (i-1)*12
                self.particles.emit(self.x+ndx*50+(-ndy*off), self.y+ndy*50+(ndx*off), BROWN, count=4, speed=150)
            if dist < ab.range: target.take_damage(ab.damage, ndx*200, attacker=self)

        elif name == "Pounce":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            self.body.velocity = (ndx*900, -500)
            self.particles.emit(self.x, self.y, (140,110,80), count=15, speed=200)
            if dist < 150: target.take_damage(ab.damage, ndx*500, attacker=self)

        elif name == "Howl":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, WHITE, count=35, speed=250, size=8)
            if dist < ab.range:
                target.take_damage(ab.damage, ndx*300, attacker=self)
                target.stun_timer = 1.2
                self.speed = min(self.speed * 1.2, 600)  # Howl buffs own speed

        elif name == "Full Moon Rage":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, SILVER, count=50, speed=400, size=10)
            for _ in range(5):
                target.take_damage(ab.damage//5, ndx*200, attacker=self)
                self.particles.emit(target.x, target.y, BROWN, count=8, speed=200)

        # ── STORMBORN ──
        elif name == "Spark Shot":
            p = Projectile(self.x, self.y, ndx*700, ndy*700, ab.damage, YELLOW, 6, self.team, CYAN)
            projectiles.append(p)

        elif name == "Thunder Dash":
            self.body.velocity = (ndx*1100, ndy*400)
            self.particles.emit(self.x, self.y, YELLOW, count=15, speed=200)
            if dist < 150: target.take_damage(ab.damage, ndx*600, attacker=self)

        elif name == "Ball Lightning":
            p = Projectile(self.x, self.y, ndx*300, ndy*300, ab.damage, WHITE, 12, self.team, YELLOW, piercing=True, aoe_radius=50)
            projectiles.append(p)

        elif name == "Supercell":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for _ in range(8):
                px = target.x + random.uniform(-150,150)
                self.particles.emit_beam(px, -200, px, target.y, (100,180,255), count=8, size=6)
            target.take_damage(ab.damage, 0, 300, attacker=self)
            target.stun_timer = 1.0

        # ── SAMURAI ──
        elif name == "Iai Strike":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            self.particles.emit_beam(self.x, self.y, self.x+ndx*ab.range, self.y+ndy*ab.range, SILVER, count=15, size=5, life=0.15)
            if dist < ab.range: target.take_damage(ab.damage, ndx*300, attacker=self)

        elif name == "Parry":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            self.invincible_timer = 0.8
            self.particles.emit_ring(self.x, self.y, GOLD, count=20, speed=100, size=6)
            if dist < ab.range:
                target.take_damage(ab.damage, -ndx*400, attacker=self)  # Counter-strike

        elif name == "Blade Storm":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            for i in range(8):
                angle = i * (math.pi*2/8)
                self.particles.emit(self.x + math.cos(angle)*60, self.y + math.sin(angle)*60,
                                   (220,180,100), count=5, speed=150, size=6)
            if dist < ab.range:
                target.take_damage(ab.damage, ndx*400, -300, attacker=self)

        elif name == "Seppuku Edge":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.take_damage(self.max_hp * 0.1)  # Honor sacrifice
            self.particles.emit_ring(self.x, self.y, CRIMSON, count=40, speed=300, size=10)
            self.particles.emit_beam(self.x, self.y, target.x, target.y, SILVER, count=30, size=8)
            target.take_damage(ab.damage, ndx*800, -500, attacker=self)

        # ── GUNSMITH ──
        elif name == "Quick Draw":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self.particles.emit_beam(self.x, self.y, self.x+ndx*300, self.y+ndy*300, GOLD, count=8, size=3, life=0.08)
            p = Projectile(self.x, self.y, ndx*900, ndy*900, ab.damage, (180,130,60), 5, self.team, GOLD)
            projectiles.append(p)

        elif name == "Deploy Turret":
            if hasattr(self, 'battle_ref'):
                self.battle_ref.sounds.play('shoot')
                # Plant a stationary turret projectile that fires for 3 seconds (simulated via rapid burst)
                tx = self.x + ndx*80
                ty = self.y + ndy*80
                self.particles.emit_ring(tx, ty, SILVER, count=20, speed=60, size=6)
                self.particles.emit(tx, ty, (180,130,60), count=15, speed=30, size=8, gravity=False)
                self.battle_ref.add_field_effect("turret", tx, ty, SILVER, 5.5,
                                                 owner_team=self.team, damage=ab.damage,
                                                 secondary=GOLD, spin=1.3, interval=0.55,
                                                 angle=math.atan2(ndy, ndx))
                # Turret fires a burst of bullets in enemy direction
                for i in range(8):
                    spread = random.uniform(-0.15, 0.15)
                    angle = math.atan2(ndy, ndx) + spread
                    p = Projectile(tx, ty, math.cos(angle)*750, math.sin(angle)*750,
                                  ab.damage//8, SILVER, 5, self.team, GOLD)
                    projectiles.append(p)

        elif name == "Shotgun Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self.particles.emit_ring(self.x + ndx*30, self.y + ndy*30, ORANGE, count=20, speed=250, size=5)
            for i in range(7):
                spread = (i - 3) * 0.15
                angle = math.atan2(ndy, ndx) + spread
                p = Projectile(self.x, self.y, math.cos(angle)*600, math.sin(angle)*600,
                              ab.damage//7, ORANGE, 6, self.team, GOLD)
                projectiles.append(p)

        elif name == "Gatling Storm":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            for i in range(20):
                spread = random.uniform(-0.25, 0.25)
                angle = math.atan2(ndy, ndx) + spread
                px = self.x + random.uniform(-20, 20)
                py = self.y + random.uniform(-20, 20)
                p = Projectile(px, py, math.cos(angle)*800, math.sin(angle)*800,
                              ab.damage//20, RED, 5, self.team, ORANGE)
                projectiles.append(p)
            self.particles.emit_ring(self.x, self.y, ORANGE, count=30, speed=150, size=5)

        # ── ARCHITECT ──
        elif name == "Stone Throw":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            p = Projectile(self.x, self.y, ndx*500, ndy*500-80, ab.damage, (120,100,80), 12, self.team, BROWN)
            projectiles.append(p)

        elif name == "Build Wall":
            if hasattr(self, 'battle_ref'):
                self.battle_ref.sounds.play('thud')
                br = self.battle_ref
                # Place a wall segment between self and enemy
                wx = (self.x + target.x) / 2
                wy = (self.y + target.y) / 2
                # Wall perpendicular to the line between fighters
                perp_x, perp_y = -ndy, ndx
                w_len = 70
                static = br.space.static_body
                wall = pymunk.Segment(static,
                    (wx - perp_x*w_len, wy - perp_y*w_len),
                    (wx + perp_x*w_len, wy + perp_y*w_len), 8)
                wall.elasticity = 0.6; wall.friction = 0.5
                wall.collision_type = 0
                br.space.add(wall)
                br.temp_walls.append((wall, 8.0))  # (wall, lifetime seconds)
                br.add_field_effect("wall", wx, wy, (120,100,80), 8.0,
                                    owner_team=self.team, secondary=SILVER,
                                    angle=math.atan2(perp_y, perp_x), length=w_len, shape=wall)
                # Visual effect
                for i in range(5):
                    self.particles.emit(wx + perp_x*i*25, wy + perp_y*i*25,
                                       (120,100,80), count=8, speed=60, size=8, gravity=False)
                    self.particles.emit(wx - perp_x*i*25, wy - perp_y*i*25,
                                       (120,100,80), count=8, speed=60, size=8, gravity=False)
                if dist < ab.range: target.take_damage(ab.damage, ndx*100, attacker=self)

        elif name == "Fortify":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.invincible_timer = 4.0
            self.particles.emit_ring(self.x, self.y, BLUE, count=30, speed=80, size=10)
            self.particles.emit_ring(self.x, self.y, SILVER, count=20, speed=40, size=14)
            self.trait_label_txt = "FORTIFIED!"
            self.trait_label_timer = 2.0

        elif name == "Wall Collapse":
            if hasattr(self, 'battle_ref'):
                self.battle_ref.sounds.play('special')
                br = self.battle_ref
                # Destroy all temp walls and deal damage for each
                if hasattr(br, 'temp_walls') and br.temp_walls:
                    for w, _ in br.temp_walls:
                        if w in br.space.shapes: br.space.remove(w)
                        # Slam wall into enemy as shrapnel
                        self.particles.emit_ring(target.x, target.y, BROWN, count=25, speed=300, size=8)
                    num_walls = len(br.temp_walls)
                    br.temp_walls = []
                    target.take_damage(ab.damage + num_walls*15, ndx*500, attacker=self)
                else:
                    # Even without walls do the base damage
                    self.particles.emit_ring(self.x, self.y, BROWN, count=30, speed=300, size=8)
                    target.take_damage(ab.damage, ndx*400, attacker=self)

        # ── CLONE-MASTER ──
        elif name == "Shadow Punch":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            self.particles.emit(self.x + ndx*50, self.y + ndy*50, TEAL, count=15, speed=200)
            if dist < ab.range: target.take_damage(ab.damage, ndx*350, attacker=self)

        elif name == "Spawn Clone":
            if hasattr(self, 'battle_ref'):
                self.battle_ref.sounds.play('special')
                br = self.battle_ref
                # Create a clone projectile swarm that behaves like a fighter
                # We simulate a clone with a fast burst of homing projectiles
                cx = self.x + random.uniform(-80, 80)
                cy = self.y + random.uniform(-40, 40)
                self.particles.emit_ring(cx, cy, TEAL, count=25, speed=100, size=7)
                self.particles.emit_ring(cx, cy, CYAN, count=15, speed=40, size=10)
                br.add_field_effect("clone", cx, cy, TEAL, 4.0,
                                    owner_team=self.team, damage=ab.damage,
                                    secondary=CYAN, spin=1.8, interval=0.7)
                # Clone fires a burst at the target
                for _ in range(4):
                    spread = random.uniform(-0.2, 0.2)
                    angle = math.atan2(target.y-cy, target.x-cx) + spread
                    p = Projectile(cx, cy, math.cos(angle)*450, math.sin(angle)*450,
                                  ab.damage//4, (80,220,200), 7, self.team, TEAL, homing=True)
                    br.projectiles.append(p)

        elif name == "Twin Strike":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            # Self strikes
            if dist < ab.range:
                target.take_damage(ab.damage//2, ndx*300, attacker=self)
            # Clone ghost strikes from a flanking angle
            clone_x = self.x - ndy*80
            clone_y = self.y + ndx*80
            self.particles.emit(clone_x, clone_y, TEAL, count=20, speed=150, size=6)
            self.particles.emit_beam(clone_x, clone_y, target.x, target.y, CYAN, count=10, size=4, life=0.2)
            target.take_damage(ab.damage//2, -ndy*300, attacker=self)

        elif name == "Clone Army":
            if hasattr(self, 'battle_ref'):
                self.battle_ref.sounds.play('special')
                br = self.battle_ref
                self.particles.emit_ring(self.x, self.y, TEAL, count=60, speed=300, size=8)
                # Spawn 4 clones at different positions, all attacking
                offsets = [(-120,-60),(120,-60),(-60,80),(60,80)]
                for off in offsets:
                    cx = self.x + off[0]; cy = self.y + off[1]
                    self.particles.emit_ring(cx, cy, CYAN, count=20, speed=80, size=6)
                    br.add_field_effect("clone", cx, cy, TEAL, 4.2,
                                        owner_team=self.team, damage=ab.damage,
                                        secondary=WHITE, spin=1.4, interval=0.75)
                    # Each clone fires homing burst
                    angle = math.atan2(target.y-cy, target.x-cx)
                    for _ in range(3):
                        spread = random.uniform(-0.2, 0.2)
                        p = Projectile(cx, cy,
                                      math.cos(angle+spread)*500,
                                      math.sin(angle+spread)*500,
                                      ab.damage//12, TEAL, 7, self.team, CYAN, homing=True)
                        br.projectiles.append(p)

        # ── POKEMON MOVES ──
        elif name == "Solar Beam":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_ring(self.x, self.y, YELLOW, count=28, speed=110, size=7, life=0.7)
            self.particles.emit_beam(self.x, self.y, target.x, target.y, GREEN, count=35, size=5, life=0.35)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("field", self.x, self.y, YELLOW, 1.4,
                                                 radius=85, owner_team=self.team, damage=ab.damage * 0.5,
                                                 secondary=GREEN, spin=1.2, interval=0.5)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*650, -220)

        elif name == "Sludge Bomb":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            p = self._spawn_ability_projectile(projectiles, ab, ndx*360, ndy*360-120, PURPLE, 10, trail=PINK, aoe_radius=85, target=target)
            p.gravity_affected = True
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cloud", target.x, target.y, PURPLE, 3.8,
                                                 radius=90, owner_team=self.team, damage=ab.damage,
                                                 secondary=PINK, spin=0.9, interval=0.5)

        elif name == "Energy Ball":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self._spawn_ability_projectile(projectiles, ab, ndx*520, ndy*520, GREEN, 8, trail=LIME, target=target)

        elif name == "Flamethrower":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            for i in range(10):
                fx = self.x + ndx * (40 + i * 24) + random.uniform(-8, 8)
                fy = self.y + ndy * (40 + i * 24) + random.uniform(-8, 8)
                self.particles.emit(fx, fy, ORANGE, count=2, speed=45, size=6, life=0.5, gravity=False)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*280, -100)
                target.apply_dot(18, 2.2)

        elif name == "Fire Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self._spawn_ability_projectile(projectiles, ab, ndx*430, ndy*430, ORANGE, 12, trail=RED, aoe_radius=95, target=target)

        elif name == "Air Slash":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            for offset in (-0.12, 0.12):
                ang = math.atan2(ndy, ndx) + offset
                p = Projectile(self.x, self.y, math.cos(ang)*560, math.sin(ang)*560, self._ability_damage(ab, scale=0.5, target=target), WHITE, 6, self.team, CYAN, piercing=True, owner=self)
                projectiles.append(p)

        elif name == "Dragon Claw":
            self.particles.emit_slash(target.x, target.y, math.atan2(ndy, ndx), CYAN, size=50, count=10)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*420, -260)

        elif name == "Hydro Pump":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, CYAN, count=28, size=5, life=0.28)
            p = self._spawn_ability_projectile(projectiles, ab, ndx*620, ndy*620, CYAN, 10, trail=BLUE, aoe_radius=40, target=target)
            p.gravity_affected = False

        elif name == "Surf":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("field", target.x, target.y, BLUE, 3.6,
                                                 radius=120, owner_team=self.team, damage=ab.damage,
                                                 secondary=CYAN, spin=1.1, interval=0.45)
            for i in range(5):
                self.particles.emit(self.x + ndx*i*55, self.y + math.sin(i * 0.8) * 6, BLUE, count=8, speed=140, size=10)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*700, -220)

        elif name == "Ice Beam":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, WHITE, count=24, size=4, life=0.25)
            p = Projectile(self.x, self.y, ndx*580, ndy*580, self._ability_damage(ab, target=target), WHITE, 7, self.team, CYAN, piercing=True, owner=self)
            projectiles.append(p)
            if dist < ab.range:
                target.stun_timer = max(target.stun_timer, 0.45)

        elif name == "Dark Pulse":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self._spawn_ability_projectile(projectiles, ab, ndx*450, ndy*450, PURPLE, 10, trail=BLACK, aoe_radius=55, target=target)

        elif name == "Giga Drain":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('heal')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, GREEN, count=18, size=4, life=0.35)
            if dist < ab.range:
                stolen = self._apply_pokemon_hit(target, ab, ndx*160, scale=1.0)
                self.heal(stolen * 0.45)

        elif name == "Body Slam":
            self.body.velocity = (ndx*900, -180)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*620, -220)

        elif name == "Focus Blast":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self._spawn_ability_projectile(projectiles, ab, ndx*360, ndy*360, GOLD, 14, trail=ORANGE, homing=True, aoe_radius=100, target=target)

        elif name == "Waterfall":
            self.particles.emit_ring(self.x, self.y, CYAN, count=18, speed=140, size=6)
            self.body.velocity = (ndx*420, -720)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*420, -520)

        elif name == "Ice Punch":
            self.particles.emit(target.x, target.y, WHITE, count=12, speed=180)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*280, -180)
                target.stun_timer = max(target.stun_timer, 0.6)

        elif name == "Crunch":
            self.particles.emit_beam(target.x-20, target.y-18, target.x+18, target.y+18, PURPLE, count=10, life=0.15)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*320)

        elif name == "Leaf Blade":
            self.particles.emit_slash(self.x, self.y, math.atan2(ndy, ndx), GREEN, size=52, count=12)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*360, -180)

        elif name == "Dragon Pulse":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self._spawn_ability_projectile(projectiles, ab, ndx*470, ndy*470, CYAN, 9, trail=PURPLE, aoe_radius=45, target=target)

        elif name == "Flare Blitz":
            self.body.velocity = (ndx*1100, ndy*160)
            self.particles.emit_ring(self.x, self.y, ORANGE, count=22, speed=170, size=7)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*720, -260)
                self.take_damage(ab.damage * 0.12)

        elif name == "Blaze Kick":
            self.body.velocity = (ndx*720, -260)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*460, -320)
                target.apply_dot(10, 1.5)

        elif name == "High Jump Kick":
            self.body.velocity = (ndx*780, -620)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*760, -500)
            else:
                self.take_damage(ab.damage * 0.08)

        elif name == "Brave Bird":
            self.body.velocity = (ndx*980, ndy*260 - 120)
            if dist < ab.range * 1.2:
                self._apply_pokemon_hit(target, ab, ndx*680, -260)
                self.take_damage(ab.damage * 0.1)

        elif name == "Wood Hammer":
            self.particles.emit_ring(self.x, self.y, GREEN, count=20, speed=150, size=8)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*650, -260)
                self.take_damage(ab.damage * 0.08)

        elif name == "Stone Edge":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('thud')
            for i in range(5):
                px = target.x + (i-2) * 26
                self.particles.emit(px, target.y + 30, SILVER, count=8, speed=180, size=8)
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("cage", target.x, target.y + 10, SILVER, 2.2,
                                                 radius=70, owner_team=self.team, damage=ab.damage * 0.7,
                                                 secondary=BROWN, spin=0.9, interval=0.5)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, 0, -460)

        elif name == "Close Combat":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('slash')
            for _ in range(4):
                if dist < ab.range:
                    self._apply_pokemon_hit(target, ab, ndx*180, scale=0.25)
            self.body.velocity = (self.body.velocity.x + ndx*120, self.body.velocity.y)

        elif name == "Mach Punch":
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*220)
                target.stun_timer = max(target.stun_timer, 0.2)

        elif name == "Flash Cannon":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, SILVER, count=24, size=4, life=0.22)
            self._spawn_ability_projectile(projectiles, ab, ndx*540, ndy*540, SILVER, 8, trail=WHITE, target=target)

        elif name == "Leaf Storm":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            if hasattr(self, 'battle_ref'):
                self.battle_ref.add_field_effect("swarm", target.x, target.y, GREEN, 4.6,
                                                 radius=110, owner_team=self.team, damage=ab.damage,
                                                 secondary=LIME, spin=4.2, interval=0.35)
            for _ in range(12):
                ang = random.uniform(0, math.pi*2)
                p = Projectile(target.x, target.y, math.cos(ang)*360, math.sin(ang)*360, self._ability_damage(ab, scale=1/12, target=target), GREEN, 5, self.team, LIME, owner=self)
                projectiles.append(p)

        elif name == "Heat Crash":
            self.body.velocity = (ndx*820, -120)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*700, -180)
                target.apply_dot(12, 1.6)

        elif name == "Hammer Arm":
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*620, -260)
                target.stun_timer = max(target.stun_timer, 0.45)

        elif name == "Wild Charge":
            self.body.velocity = (ndx*960, ndy*120)
            self.particles.emit_ring(self.x, self.y, YELLOW, count=16, speed=160, size=6)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*620, -220)
                self.take_damage(ab.damage * 0.1)

        elif name == "Megahorn":
            self.body.velocity = (ndx*900, -120)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, ndx*700, -240)

        elif name == "Drain Punch":
            if dist < ab.range:
                stolen = self._apply_pokemon_hit(target, ab, ndx*280)
                self.heal(stolen * 0.5)

        elif name == "Psychic":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('special')
            self.particles.emit_beam(self.x, self.y, target.x, target.y, PINK, count=18, size=4, life=0.3)
            if dist < ab.range:
                self._apply_pokemon_hit(target, ab, 0, -260)
                target.stun_timer = max(target.stun_timer, 0.55)

        elif name == "Shadow Ball":
            if hasattr(self, 'battle_ref'): self.battle_ref.sounds.play('shoot')
            self._spawn_ability_projectile(projectiles, ab, ndx*420, ndy*420, PURPLE, 11, trail=BLACK, homing=True, aoe_radius=55, target=target)

        # ── RECOIL / BACK-DASH (Tactical Retreat) ──
        # Move back after hit / ability use
        recoil_force = 450 if ab.range < 170 else 180
        self.body.velocity = (
            self.body.velocity.x - ndx * recoil_force,
            self.body.velocity.y - ndy * recoil_force
        )
        # Visual dash trail for retreat
        self.particles.emit(self.x, self.y, WHITE, count=5, speed=60, size=3, life=0.5, gravity=False)
        self.particles.emit_ring(self.x, self.y, ab.color, count=10, speed=40, size=2)




    def draw(self, screen, font_small):
        if not self.alive:
            return
        x, y = int(self.x), int(self.y)
        s = self.size

        for img in self.afterimages:
            alpha = max(0.0, img["life"] / img["max_life"])
            ghost = pygame.Surface((int(img["size"] * 4), int(img["size"] * 4)), pygame.SRCALPHA)
            color = (*img["color"], int(80 * alpha))
            rect = (
                int(img["size"]),
                int(img["size"] * 1.2),
                int(img["size"] * 2),
                int(img["size"] * 1.45),
            )
            pygame.draw.ellipse(ghost, color, rect)
            screen.blit(ghost, (img["x"] - img["size"] * 2, img["y"] - img["size"] * 2))

        if self.cast_ring_timer > 0:
            alpha = self.cast_ring_timer / 0.6
            aura_radius = int(s * (1.8 + (1 - alpha) * 1.4))
            aura = pygame.Surface((aura_radius * 4, aura_radius * 4), pygame.SRCALPHA)
            center = aura_radius * 2
            pygame.draw.circle(aura, (*self.cast_color, int(55 * alpha)), (center, center), aura_radius, max(2, int(4 * alpha)))
            pygame.draw.circle(aura, (*self.cast_accent, int(35 * alpha)), (center, center), max(8, aura_radius - 10), 2)
            screen.blit(aura, (x - center, y - center))

        self._draw_ambient_fx(screen, x, y, s)

        # Flash white on hit
        draw_color = WHITE if self.hit_flash > 0 else self.color
        body_draw  = WHITE if self.hit_flash > 0 else self.body_color
        if self.cast_flash_timer > 0:
            cast_blend = min(1.0, self.cast_flash_timer / 0.35)
            draw_color = self._mix_color(draw_color, self.cast_color, 0.35 * cast_blend)
            body_draw = self._mix_color(body_draw, self.cast_accent, 0.45 * cast_blend)

        # ── ANIMATIC EFFECTS ──
        # Squash & Stretch based on velocity
        v_mag = math.hypot(self.vx, self.vy)
        stretch = min(1.35, 1.0 + v_mag / 1400.0)
        squash = 1.0 / stretch
        
        # Hit Shake
        hx, hy = 0, 0
        if self.hit_flash > 0:
            hx, hy = random.randint(-4, 4), random.randint(-4, 4)

        # Shadow
        shadow_surf = pygame.Surface((s*4, s*4), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0,0,0,40), (s*2 - int(s*stretch), s*2 - int(s*squash) + 4, int(s*2*stretch), int(s*2*squash)))
        screen.blit(shadow_surf, (x - s*2 + hx, y - s*2 + hy))

        # Body (main circle or sprite)
        rect = (x - int(s*stretch) + hx, y - int(s*squash) + hy, int(s*2*stretch), int(s*2*squash))
        if self.sprite is not None:
            sprite_w = max(28, int(s * 3.0 * stretch))
            sprite_h = max(28, int(s * 3.0 * squash))
            sprite = pygame.transform.smoothscale(self.sprite, (sprite_w, sprite_h))
            screen.blit(sprite, (x - sprite_w//2 + hx, y - sprite_h//2 + hy))
            if self.hit_flash > 0:
                pygame.draw.ellipse(screen, WHITE, rect, 3)
        else:
            pygame.draw.ellipse(screen, body_draw, rect)
            pygame.draw.ellipse(screen, draw_color, rect, 2)
            self._draw_pokemon_details(screen, x, y, s, body_draw, draw_color)

        if self.cast_flash_timer > 0:
            pulse_w = max(2, int(5 * (self.cast_flash_timer / 0.35)))
            pygame.draw.ellipse(screen, self.cast_color, (rect[0] - 3, rect[1] - 3, rect[2] + 6, rect[3] + 6), pulse_w)

        # Eyes
        eye_x = x + self.facing * (s*0.4) + hx
        eye_y = y - s*0.2 + hy
        pygame.draw.circle(screen, WHITE, (int(eye_x), int(eye_y)), s//5)
        pygame.draw.circle(screen, BLACK, (int(eye_x + self.facing*1), int(eye_y)), s//8)

        # ── DRAW WEAPON ──
        w_color = (180, 180, 180) # Default steel
        attack_phase = 0.0
        if self.cast_flash_timer > 0:
            attack_phase = min(1.0, self.cast_flash_timer / 0.35)
        swing = math.sin(attack_phase * math.pi)
        thrust = attack_phase * (2.0 - attack_phase)
        weapon_glow = self.cast_color if self.cast_flash_timer > 0 else self.color
        if self.weapon_type == "sword":
            sword_len = s * (1.5 + thrust * 0.25)
            lift = swing * s * 0.8
            start = (x + self.facing * (s - 2), y + s//2 - lift * 0.2)
            end = (x + self.facing * (s + sword_len), y - s//2 - lift)
            pygame.draw.line(screen, w_color, start, end, 4)
            pygame.draw.line(screen, (100, 100, 100), start, (x + self.facing * (s + 5), y + s//2 + 5), 6) # hilt
            if self.cast_flash_timer > 0:
                pygame.draw.line(screen, weapon_glow, start, end, 2)
        elif self.weapon_type == "staff":
            staff_len = s * 2.0
            sway = math.sin(pygame.time.get_ticks()*0.012 + self.ambient_phase) * 3 + swing * 6
            start = (x + self.facing * s + sway, y + s)
            end = (x + self.facing * s - sway, y - s - thrust * 6)
            pygame.draw.line(screen, (100, 70, 30), start, end, 3)
            pygame.draw.circle(screen, self.color, end, 5) # Gem
            if self.cast_flash_timer > 0:
                pygame.draw.circle(screen, weapon_glow, end, 7, 2)
        elif self.weapon_type == "katana":
            sword_len = s * (1.8 + thrust * 0.2)
            slash_rise = swing * s * 0.65
            start = (x + self.facing * s, y + s//4 - slash_rise * 0.15)
            end = (x + self.facing * (s + sword_len), y - s//4 - slash_rise)
            pygame.draw.line(screen, (220, 220, 230), start, end, 2)
            if self.cast_flash_timer > 0:
                pygame.draw.line(screen, weapon_glow, start, end, 1)
        elif self.weapon_type == "blaster":
            b_w, b_h = s, s//2
            recoil = thrust * 8
            bx = x + self.facing * (s - recoil) - (b_w if self.facing == -1 else 0)
            by = y - b_h//2 + math.sin(pygame.time.get_ticks()*0.03 + self.ambient_phase) * 1.5
            pygame.draw.rect(screen, (80, 80, 90), (bx, by, b_w, b_h), border_radius=2)
            pygame.draw.rect(screen, CYAN, (bx + (b_w-4 if self.facing == 1 else 0), by + 2, 4, b_h-4)) # Energy glow
            if self.cast_flash_timer > 0:
                muzzle_x = bx + (b_w if self.facing == 1 else 0)
                pygame.draw.circle(screen, weapon_glow, (int(muzzle_x), int(by + b_h//2)), 5, 2)
        elif self.weapon_type == "bow":
            pull = thrust * 10
            arc_rect = (x + self.facing * (s - pull*0.2) - s, y - s - swing * 4, s*2, s*2)
            start_angle = -math.pi/2 if self.facing == 1 else math.pi/2
            pygame.draw.arc(screen, (120, 80, 40), arc_rect, start_angle, start_angle + math.pi, 2)
            string_x = x - self.facing * pull * 0.7
            pygame.draw.line(screen, weapon_glow if self.cast_flash_timer > 0 else WHITE,
                             (int(string_x), int(y - s)), (int(string_x), int(y + s)), 1)
        elif self.weapon_type == "trident":
            staff_len = s * 1.8
            jab = thrust * 12
            start = (x + self.facing * (s - jab*0.2), y + s)
            end = (x + self.facing * (s + jab), y - s - swing * 4)
            pygame.draw.line(screen, (150, 150, 160), start, end, 3)
            # Prongs
            pygame.draw.line(screen, (150, 150, 160), end, (end[0]-5, end[1]-8), 2)
            pygame.draw.line(screen, (150, 150, 160), end, (end[0]+5, end[1]-8), 2)
            pygame.draw.line(screen, (150, 150, 160), end, (end[0], end[1]-12), 2)
            if self.cast_flash_timer > 0:
                pygame.draw.circle(screen, weapon_glow, (int(end[0]), int(end[1]-4)), 6, 2)
        elif self.weapon_type == "claws":
            for i in range(3):
                off = (i-1)*5
                reach = 10 + thrust * 8
                rise = swing * 6
                pygame.draw.line(screen, WHITE, (x + self.facing*s, y + off), (x + self.facing*(s+reach), y + off - 5 - rise), 2)
        elif self.weapon_type == "hammer":
            staff_len = s * 1.5
            smash = swing * 10
            start = (x + self.facing * s, y + s)
            end = (x + self.facing * (s + thrust*5), y - s + smash)
            pygame.draw.line(screen, (120, 90, 50), start, end, 5) # Handle
            # Hammer head
            pygame.draw.rect(screen, (100, 100, 110), (end[0]-10, end[1]-5, 20, 15))
            if self.cast_flash_timer > 0:
                pygame.draw.rect(screen, weapon_glow, (end[0]-12, end[1]-7, 24, 19), 2)
        elif self.weapon_type == "chain":
            start = (x + self.facing * s, y - swing * 3)
            for i in range(5):
                cx_ = start[0] + self.facing * i * (6 + thrust * 2)
                cy_ = start[1] + math.sin(pygame.time.get_ticks()*0.01 + i + attack_phase*4)*5
                pygame.draw.circle(screen, (150, 150, 160), (int(cx_), int(cy_)), 3, 1)
            ball_x = start[0] + self.facing*(30 + thrust * 10)
            ball_y = start[1] - swing * 4
            pygame.draw.circle(screen, RED, (int(ball_x), int(ball_y)), 5) # Weighted end
            if self.cast_flash_timer > 0:
                pygame.draw.circle(screen, weapon_glow, (int(ball_x), int(ball_y)), 8, 2)
        
        # ── DRAW SHIELD ──
        if self.has_shield:
            sh_w, sh_h = s//2, s * 1.4
            shx = x + self.facing * (s - 2) - (sh_w if self.facing == -1 else 0)
            shy = y - sh_h//2
            pygame.draw.rect(screen, (150, 160, 170), (shx, shy, sh_w, sh_h), border_radius=4)
            pygame.draw.rect(screen, SILVER, (shx+2, shy+2, sh_w-4, sh_h-4), border_radius=2)

        if self.cast_ring_timer > 0:
            tip_angle = pygame.time.get_ticks() * 0.01
            for i in range(3):
                ang = tip_angle + i * (math.pi * 2 / 3)
                orb_x = x + math.cos(ang) * (s + 10)
                orb_y = y + math.sin(ang) * (s + 10)
                pygame.draw.circle(screen, self.cast_accent, (int(orb_x), int(orb_y)), 3)

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
        self.orig_arena_size = 440
        self.powerups: List[PowerUp] = []
        self.pu_spawn_timer = 10.0 # First one at 10s
        self.TIME_LIMIT = 105.0  # 1 minute 45 seconds
        self.time_up = False     # True when battle ended by timer
        self.time_up_winner_team = -1
        self.time_up_judgment = []  # List of strings explaining the judgment
        self.field_effects: List[BattlefieldEffect] = []
        self.temp_walls = []
        self.active_clones = []

        # ── ARENA GENERATION ──
        self.arena_size = 440
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
            rad = 240
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

        # Fighter-to-Fighter collision (Push/Bump logic)
        def fighter_collide(arbiter, space, data):
            s1, s2 = arbiter.shapes
            f1 = getattr(s1, 'fighter', None)
            f2 = getattr(s2, 'fighter', None)
            if f1 and f2:
                if f1.stun_timer > 0 or f2.stun_timer > 0:
                    return True
                if f1.collision_recover_timer > 0 or f2.collision_recover_timer > 0:
                    return True
                # Add a tactical 'bounce' between fighters
                dx, dy = f1.x - f2.x, f1.y - f2.y
                dist = math.hypot(dx, dy) or 1
                ndx, ndy = dx/dist, dy/dist
                # Bump force proportional to impact but with a base minimum
                force = 260 + min(arbiter.total_impulse.length * 0.12, 480)
                f1.body.velocity = (f1.body.velocity.x + ndx*force, f1.body.velocity.y + ndy*force*0.7 - 80)
                f2.body.velocity = (f2.body.velocity.x - ndx*force, f2.body.velocity.y - ndy*force*0.7 - 80)
                f1.collision_recover_timer = 0.38
                f2.collision_recover_timer = 0.38
                f1.ai_state = "scramble"
                f2.ai_state = "scramble"
                f1.ai_timer = max(f1.ai_timer, 0.22)
                f2.ai_timer = max(f2.ai_timer, 0.22)
                # Visual sparks on impact
                f1.particles.emit(f1.x, f1.y, WHITE, count=4, speed=60)
                f2.particles.emit(f2.x, f2.y, WHITE, count=4, speed=60)
                f1.particles.emit_ring((f1.x + f2.x) * 0.5, (f1.y + f2.y) * 0.5, SILVER, count=8, speed=120, size=4, life=0.25)
            if arbiter.total_impulse.length > 500:
                self.sounds.play('thud')
            return True
        self.space.on_collision(1, 1, post_solve=fighter_collide) # Use Fighter collision type (1)
        
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

        # 1v1 HP Boost (70% more health)
        if len(team_a) == 1 and len(team_b) == 1 and not is_br:
            for f in self.fighters:
                f.max_hp = int(f.max_hp * 1.7)
                f.hp = f.max_hp

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

    def add_field_effect(self, effect_type, x, y, color, life, **kwargs):
        eff = BattlefieldEffect(effect_type, x, y, color, life, **kwargs)
        self.field_effects.append(eff)
        return eff

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
                # Update existing physics walls positions (recreate since .a/.b are read-only)
                if len(self.walls) >= 4:
                    static = self.space.static_body
                    # Remove only first 4 walls (main arena)
                    for w in self.walls[:4]:
                        if w in self.space.shapes: self.space.remove(w)
                    
                    self.walls[0] = pymunk.Segment(static, (r.left, r.top), (r.right, r.top), 10)
                    self.walls[1] = pymunk.Segment(static, (r.right, r.top), (r.right, r.bottom), 10)
                    self.walls[2] = pymunk.Segment(static, (r.right, r.bottom), (r.left, r.bottom), 10)
                    self.walls[3] = pymunk.Segment(static, (r.left, r.bottom), (r.left, r.top), 10)
                    
                    for w in self.walls[:4]:
                        w.elasticity = 0.95; w.friction = 0.1
                        self.space.add(w)
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

        # ── ARCHITECT TEMP WALL LIFETIME ──
        if self.temp_walls:
            surviving = []
            for w, lifetime in self.temp_walls:
                remaining = lifetime - dt
                if remaining <= 0:
                    if w in self.space.shapes:
                        self.space.remove(w)
                    mx = (w.a.x + w.b.x) / 2
                    my = (w.a.y + w.b.y) / 2
                    self.particles.emit(mx, my, (120, 100, 80), count=12, speed=80, size=6)
                else:
                    surviving.append((w, remaining))
            self.temp_walls = surviving

        # ── CLONE MASTER ACTIVE CLONE CLEANUP ──
        if self.active_clones:
            t_now = pygame.time.get_ticks() / 1000.0
            self.active_clones = [(cx, cy, col, born, lt) for cx, cy, col, born, lt in self.active_clones
                                  if t_now - born < lt]

        # ── POWER-UP SPAWNING ──
        if self.elapsed > 2.0: # Only spawn after intro
            self.pu_spawn_timer -= dt
            if self.pu_spawn_timer <= 0:
                self.pu_spawn_timer = 15.0
                ptype = random.choice(["Shield", "Rage", "Speed"])
                px = WIDTH//2 + random.uniform(-180, 180)
                py = HEIGHT//2 + random.uniform(-180, 180)
                if self.arena_type != "OCTAGON":
                    r = self.arena_rect
                    px = max(r.left+60, min(r.right-60, px))
                    py = max(r.top+60, min(r.bottom-60, py))
                self.powerups.append(PowerUp(px, py, ptype))
                self.particles.emit_ring(px, py, GOLD, count=25, speed=200, size=6)

        # Update powerups
        new_pu = []
        for pu in self.powerups:
            if pu.update(dt):
                hit_f = None
                for cand in self.fighters: # Use self.fighters to allow picking up before checking if alive logic strips it out
                    if cand.alive and math.hypot(cand.x - pu.x, cand.y - pu.y) < cand.size + pu.size:
                        hit_f = cand
                        break
                if hit_f:
                    self.sounds.play('special')
                    hit_f.particles.emit_ring(hit_f.x, hit_f.y, pu.color, count=30, speed=250, size=8)
                    if pu.type == "Shield":
                        hit_f.trait_label_txt = "ENERGY SHIELD!"
                        hit_f.trait_label_timer = 1.5
                        hit_f.invincible_timer = 4.0
                    elif pu.type == "Rage":
                        hit_f.trait_label_txt = "POWER RAGE!"
                        hit_f.trait_label_timer = 1.5
                        hit_f.hidden_trait = "RAGE"
                        hit_f.trait_timer = 6.0
                    elif pu.type == "Speed":
                        hit_f.trait_label_txt = "MAX SPEED!"
                        hit_f.trait_label_timer = 1.5
                        hit_f.speed *= 1.3
                else:
                    new_pu.append(pu)
        self.powerups = new_pu

        alive_fighters = [f for f in self.fighters if f.alive]

        updated_effects = []
        for effect in self.field_effects:
            if effect.update(dt, self, alive_fighters, self.projectiles):
                updated_effects.append(effect)
        self.field_effects = updated_effects

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
                        self.particles.emit_impact(proj.x, proj.y, WHITE, count=10) # Added sparkle
                    else:
                        dx_ = f.x - proj.x
                        dy_ = f.y - proj.y
                        d_  = max(1, math.hypot(dx_, dy_))
                        f.take_damage(proj.damage,
                                     knockback_x=dx_/d_*450,
                                     knockback_y=-280,
                                     attacker=proj.owner)
                        # Specific hit sparks
                        self.particles.emit_impact(proj.x, proj.y, proj.color, count=12)
                    if not proj.piercing:
                        proj.alive = False
                    self.particles.emit(proj.x, proj.y, WHITE, count=15, speed=250, size=5)
                    break

        self.projectiles = [p for p in self.projectiles if p.alive]

        # Win check
        alive_fighters = [f for f in self.fighters if f.alive]

        # ── TIME LIMIT CHECK (1m 45s) ──
        if not self.over and self.elapsed >= self.TIME_LIMIT:
            self._resolve_time_up(alive_fighters)
            return

        if self.is_br:
            if len(alive_fighters) <= 1:
                self.over = True
                self.shake = 0.0
                self.winner_team = alive_fighters[0].team if alive_fighters else -1
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)
        else:
            # Team Battle
            alive_a = [f for f in alive_fighters if f.team == 0]
            alive_b = [f for f in alive_fighters if f.team == 1]
            
            # Check for double-KO (Draw)
            if not alive_a and not alive_b:
                self.over = True
                self.shake = 0.0
                self.winner_team = -1 # DRAW
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, SILVER, count=60, speed=300, size=8, life=2.0)
            elif not alive_a:
                self.over = True
                self.shake = 0.0
                self.winner_team = 1 # Team Red Wins
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)
            elif not alive_b:
                self.over = True
                self.shake = 0.0
                self.winner_team = 0 # Team Blue Wins
                self.over_timer = 3.0
                self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)

    def _resolve_time_up(self, alive_fighters):
        """Judge winner when time limit is reached — multi-criteria scoring."""
        self.over = True
        self.time_up = True
        self.shake = 0.0
        self.over_timer = 3.0
        self.particles.emit(WIDTH//2, HEIGHT//2, GOLD, count=60, speed=300, size=8, life=2.0)

        if self.is_br:
            # BR: Fighter with highest score wins
            def br_score(f):
                hp_pct = f.hp / f.max_hp if f.alive else 0
                return f.kills * 300 + f.damage_dealt * 0.5 + hp_pct * 200
            winner = max(self.fighters, key=br_score)
            self.winner_team = winner.team
            self.time_up_judgment = [
                f"⏱️ TIME'S UP! Winner by JUDGMENT",
                f"🏆 {winner.name} wins the decision!",
                f"  Kills: {winner.kills}  |  Damage: {int(winner.damage_dealt)}  |  HP: {int(winner.hp)}/{winner.max_hp}",
            ]
        else:
            # Team Battle: Score each team on 4 criteria
            fighters_a = [f for f in self.fighters if f.team == 0]
            fighters_b = [f for f in self.fighters if f.team == 1]

            # Criterion 1: Surviving fighters
            alive_a = sum(1 for f in fighters_a if f.alive)
            alive_b = sum(1 for f in fighters_b if f.alive)
            score_a, score_b = 0, 0
            judgment = ["⏱️ TIME'S UP!  —  JUDGES' DECISION", ""]

            if alive_a > alive_b:
                score_a += 3; judgment.append(f"✅ Survivors: Blue {alive_a} vs Red {alive_b}  → +3 Blue")
            elif alive_b > alive_a:
                score_b += 3; judgment.append(f"✅ Survivors: Blue {alive_a} vs Red {alive_b}  → +3 Red")
            else:
                judgment.append(f"🔘 Survivors tied:  {alive_a} vs {alive_b}")

            # Criterion 2: Total remaining HP %
            hp_pct_a = sum(f.hp / f.max_hp for f in fighters_a if f.alive)
            hp_pct_b = sum(f.hp / f.max_hp for f in fighters_b if f.alive)
            if hp_pct_a > hp_pct_b + 0.05:
                score_a += 2; judgment.append(f"✅ HP Pool: Blue {hp_pct_a*100:.0f}% vs Red {hp_pct_b*100:.0f}%  → +2 Blue")
            elif hp_pct_b > hp_pct_a + 0.05:
                score_b += 2; judgment.append(f"✅ HP Pool: Blue {hp_pct_a*100:.0f}% vs Red {hp_pct_b*100:.0f}%  → +2 Red")
            else:
                judgment.append(f"🔘 HP Pool tied:  {hp_pct_a*100:.0f}% vs {hp_pct_b*100:.0f}%")

            # Criterion 3: Total damage dealt
            dmg_a = sum(f.damage_dealt for f in fighters_a)
            dmg_b = sum(f.damage_dealt for f in fighters_b)
            if dmg_a > dmg_b * 1.1:
                score_a += 1; judgment.append(f"✅ Damage: Blue {int(dmg_a)} vs Red {int(dmg_b)}  → +1 Blue")
            elif dmg_b > dmg_a * 1.1:
                score_b += 1; judgment.append(f"✅ Damage: Blue {int(dmg_a)} vs Red {int(dmg_b)}  → +1 Red")
            else:
                judgment.append(f"🔘 Damage tied:  {int(dmg_a)} vs {int(dmg_b)}")

            # Criterion 4: Total kills
            kills_a = sum(f.kills for f in fighters_a)
            kills_b = sum(f.kills for f in fighters_b)
            if kills_a > kills_b:
                score_a += 2; judgment.append(f"✅ Kills: Blue {kills_a} vs Red {kills_b}  → +2 Blue")
            elif kills_b > kills_a:
                score_b += 2; judgment.append(f"✅ Kills: Blue {kills_a} vs Red {kills_b}  → +2 Red")
            else:
                judgment.append(f"🔘 Kills tied:  {kills_a} vs {kills_b}")

            judgment.append("")
            if score_a > score_b:
                self.winner_team = 0
                judgment.append(f"🏆 TEAM BLUE wins the decision!  ({score_a} – {score_b} pts)")
            elif score_b > score_a:
                self.winner_team = 1
                judgment.append(f"🏆 TEAM RED wins the decision!  ({score_b} – {score_a} pts)")
            else:
                # Absolute tiebreaker: most HP remaining (raw)
                if hp_pct_a >= hp_pct_b:
                    self.winner_team = 0
                    judgment.append(f"🏆 TEAM BLUE wins by TIEBREAKER  (HP edge)!")
                else:
                    self.winner_team = 1
                    judgment.append(f"🏆 TEAM RED wins by TIEBREAKER  (HP edge)!")

            self.time_up_judgment = judgment

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

        for effect in self.field_effects:
            effect.draw(canvas, self)
            
        # ── 1V1 VS HEADER ──
        if len(self.fighters) == 2 and not self.is_br:
            f1, f2 = self.fighters[0], self.fighters[1]
            # Use 'font' (28pt) instead of 'font_small' (18pt) for bigger names
            # Draw names in their respective colors with a bold effect
            n1_surf = font.render(f1.name.upper(), True, f1.color)
            vs_surf = font.render(" VS ", True, SILVER)
            n2_surf = font.render(f2.name.upper(), True, f2.color)
            
            total_w = n1_surf.get_width() + vs_surf.get_width() + n2_surf.get_width()
            so = self.shake_off()
            if self.arena_type == "OCTAGON":
                tx, ty = WIDTH//2 - total_w//2, HEIGHT//2 - 350
            else:
                tx, ty = self.arena_rect.centerx - total_w//2, self.arena_rect.top - 38
            
            # Simple Bold effect (draw twice with 1px offset)
            for ox, oy in [(0,0), (1,0)]:
                canvas.blit(n1_surf, (tx + so[0] + ox, ty + so[1] + oy))
                canvas.blit(vs_surf, (tx + n1_surf.get_width() + so[0] + ox, ty + so[1] + oy))
                canvas.blit(n2_surf, (tx + n1_surf.get_width() + vs_surf.get_width() + so[0] + ox, ty + so[1] + oy))

        # Draw World Objects
        for pu in getattr(self, 'powerups', []): pu.draw(canvas, font_small)
        for proj in self.projectiles: proj.draw(canvas)
        self.particles.draw(canvas)
        for f in self.fighters: f.draw(canvas, font_small)
        for p in self.popups: p.draw(canvas, font_small, font_big)

        # ── Draw Architect Temp Walls ──
        so = self.shake_off()
        for w, lifetime in getattr(self, 'temp_walls', []):
            p1 = (int(w.a.x + so[0]), int(w.a.y + so[1]))
            p2 = (int(w.b.x + so[0]), int(w.b.y + so[1]))
            age_frac = max(0.0, (8.0 - lifetime) / 8.0)
            # Stone colour: blue-grey fading to orange-red as timer expires
            wall_c = (int(100 + age_frac*120), int(130 - age_frac*80), int(180 - age_frac*160))
            pygame.draw.line(canvas, wall_c, p1, p2, 20)          # thick stone body
            pygame.draw.line(canvas, (210, 200, 170), p1, p2, 6)  # bright mortar line
            # Crumble flicker when nearly dead
            if lifetime < 2.0 and int(pygame.time.get_ticks() * 0.005) % 2 == 0:
                mx, my = (p1[0]+p2[0])//2, (p1[1]+p2[1])//2
                pygame.draw.line(canvas, (50, 30, 10), (mx-8, my-6), (mx+8, my+6), 2)

        # ── Draw Clone Master Active Clones ──
        t_now = pygame.time.get_ticks() / 1000.0
        for clone in getattr(self, 'active_clones', []):
            cx_c, cy_c, col, born, lt = clone
            age = t_now - born
            if age > lt:
                continue
            alpha_frac = 1.0 - (age / lt)
            r_c = max(4, int(alpha_frac * 18))
            pulse = 0.7 + 0.3 * math.sin(t_now * 8 + cx_c * 0.01)
            draw_col = tuple(min(255, int(c * pulse)) for c in col)
            # Ghost body circle
            pygame.draw.circle(canvas, draw_col,
                               (int(cx_c + so[0]), int(cy_c + so[1])), r_c)
            pygame.draw.circle(canvas, WHITE,
                               (int(cx_c + so[0]), int(cy_c + so[1])), r_c, 1)
            # X eye marks
            fx, fy = int(cx_c + so[0]), int(cy_c + so[1])
            pygame.draw.line(canvas, WHITE, (fx-4, fy-3), (fx+4, fy+3), 1)
            pygame.draw.line(canvas, WHITE, (fx+4, fy-3), (fx-4, fy+3), 1)

        # Draw HUD (Inside shaking canvas for high-action feel)
        self._draw_hud(canvas, font, font_small)

        # 3. Final Screenshake & Blit to Screen
        off_x, off_y = (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)) if self.shake > 0 else (0,0)
        screen.blit(canvas, (off_x, off_y))

        # Draw Sudden Death Warning
        if self.sd_active:
            sd_txt = font_big.render("SUDDEN DEATH!!", True, RED)
            screen.blit(sd_txt, (WIDTH//2 - sd_txt.get_width()//2, 70))  # Moved up from 150 to 70
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

        # ── TIME LIMIT COUNTDOWN WARNING ──
        remaining = max(0, self.TIME_LIMIT - self.elapsed)
        if remaining <= 20 and not self.over:
            pulse = int(pygame.time.get_ticks() * 0.005) % 2 == 0
            warn_c = RED if remaining <= 10 else ORANGE
            warn_txt = font_big.render(f"⏱ {int(remaining)}s", True, warn_c if pulse else WHITE)
            screen.blit(warn_txt, (WIDTH//2 - warn_txt.get_width()//2, 55))
            if remaining <= 10:
                flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                flash.fill((*RED, 25))
                screen.blit(flash, (0, 0))

        # Win screen (Always on top, no shake for readability)
        if self.over:
            if self.time_up and self.time_up_judgment:
                # ── JUDGMENT SCREEN ──
                color = BLUE if self.winner_team == 0 else (RED if self.winner_team == 1 else GOLD)
                panel_h = 60 + len(self.time_up_judgment) * 28 + 80
                panel = pygame.Rect(WIDTH//2 - 240, 120, 480, panel_h)
                bg = pygame.Surface((480, panel_h), pygame.SRCALPHA)
                bg.fill((8, 8, 20, 230))
                screen.blit(bg, (panel.x, panel.y))
                pygame.draw.rect(screen, color, panel, 3, border_radius=14)
                y_j = panel.y + 18
                for i, line in enumerate(self.time_up_judgment):
                    line_c = color if (i == 0 or i == len(self.time_up_judgment)-1) else WHITE
                    if "✅" in line: line_c = (100, 255, 120)
                    if "🔘" in line: line_c = (160, 160, 160)
                    if "🏆" in line: line_c = GOLD
                    s = font.render(line, True, line_c)
                    screen.blit(s, (WIDTH//2 - s.get_width()//2, y_j))
                    y_j += 28
                ret_txt = font.render("PRESS [SPACE] TO RETURN TO MENU", True, WHITE if int(self.timer*2)%2==0 else SILVER)
                screen.blit(ret_txt, (WIDTH//2 - ret_txt.get_width()//2, panel.bottom + 20))
                return  # skip normal win screen

            if self.winner_team == -1:
                msg = "🏆 DRAW! 🏆"
                color = SILVER
            elif self.is_br:
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
            # Prioritize winning team for MVP
            winner_pool = [f for f in self.fighters if f.team == self.winner_team] if self.winner_team != -1 else self.fighters
            # If winning team was decided but everyone died (rare), fallback to all
            if not winner_pool: winner_pool = self.fighters
            
            mvp = max(winner_pool, key=lambda f: f.kills * 200 + f.damage_dealt)
            
            # Winner Banner (Higher Y to avoid SD overlap)
            win_surf = font_big.render(msg, True, color)
            screen.blit(win_surf, (WIDTH//2 - win_surf.get_width()//2, 120))  # Moved from 160 to 120

            # MVP Spotlight
            mvp_txt = font.render(f"🏅 MATCH MVP: {mvp.name}", True, GOLD)
            screen.blit(mvp_txt, (WIDTH//2 - mvp_txt.get_width()//2, 200)) # Moved from 240 to 200
            
            # Stats Display
            stats_box = pygame.Rect(WIDTH//2 - 230, 250, 460, 220) # Moved from 290 to 250
            pygame.draw.rect(screen, (20, 20, 40, 220), stats_box, border_radius=15)
            pygame.draw.rect(screen, color, stats_box, 3, border_radius=15)
            
            # Record Holders (Overall best, but MVP is guaranteed winner)
            best_damage = max(self.fighters, key=lambda f: f.damage_dealt)
            best_traits = max(self.fighters, key=lambda f: f.traits_activated_count)
            
            y_off = 275
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
        # Show remaining time instead of elapsed when under 30s left
        remaining = max(0, self.TIME_LIMIT - self.elapsed)
        if remaining <= 30:
            mins = int(remaining) // 60
            secs = int(remaining) % 60
        else:
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
        if self.is_br:
            mid = (len(self.fighters) + 1) // 2
            list_a = self.fighters[:mid]
            list_b = self.fighters[mid:]
        else:
            list_a = [f for f in self.fighters if f.team == 0]
            list_b = [f for f in self.fighters if f.team == 1]

        def draw_team_panel(fighters, side, color):
            panel_w, panel_h = 240, 50
            if side == "left":
                px = 15
            else:
                px = WIDTH - panel_w - 15
            
            # Start below the arena
            start_y = (HEIGHT + self.arena_size) // 2 + 10
            
            for i, f in enumerate(fighters):
                py = start_y + i * (panel_h + 4)

                # Panel bg
                surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                surf.fill((0, 0, 0, 160))
                screen.blit(surf, (px, py))
                pygame.draw.rect(screen, color, (px, py, panel_w, panel_h), 1)
                
                # Name
                n_surf = font_small.render(f.name, True, color)
                screen.blit(n_surf, (px+6, py+3))
                
                # HP bar
                hp_frac = f.hp / f.max_hp
                hp_c = (int(255*(1-hp_frac)), int(255*hp_frac), 40)
                pygame.draw.rect(screen, (40,40,40), (px+6, py+18, panel_w-12, 12))
                pygame.draw.rect(screen, hp_c, (px+6, py+18, int((panel_w-12)*hp_frac), 12))
                hp_txt = font_small.render(f"{int(f.hp)}/{f.max_hp}", True, WHITE)
                screen.blit(hp_txt, (px + panel_w//2 - hp_txt.get_width()//2, py+17))
                
                # Ability dots (Simple)
                for j, ab in enumerate(f.abilities):
                    adx = px + 6 + j*58
                    ady = py + 34
                    ac = ab.color if ab.ready() else (50,50,60)
                    pygame.draw.rect(screen, ac, (adx, ady, 52, 5))
                    if not ab.ready():
                        frac = 1 - (ab.timer / ab.cooldown)
                        pygame.draw.rect(screen, ab.color, (adx, ady, int(52*frac), 5))

        # Position panels: Left for A, Right for B
        draw_team_panel(list_a, "left", BLUE if not self.is_br else (100, 180, 255))
        draw_team_panel(list_b, "right", RED if not self.is_br else (255, 150, 100))

        # ── 1v1 ABILITY FLASHCARDS ──
        is_1v1 = len(list_a) == 1 and len(list_b) == 1 and not self.is_br
        if is_1v1:
            def draw_flashcard(fighter, x, color, y_start):
                card_w, card_h = 240, 105
                # Place directly below the team panels
                y = y_start + 60
                bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 180))
                screen.blit(bg, (x, y))
                pygame.draw.rect(screen, color, (x, y, card_w, card_h), 2, border_radius=12)
                
                for j, ab in enumerate(fighter.abilities):
                    # Ability Name : Damage
                    name_s = font_small.render(ab.name, True, color)
                    dmg_s = font_small.render(f"{int(ab.damage)} DMG", True, WHITE)
                    # Vertical spacing
                    yy = y + 10 + j*22
                    screen.blit(name_s, (x + 10, yy))
                    screen.blit(dmg_s, (x + card_w - dmg_s.get_width() - 10, yy))

            # Find the starting Y of health bars
            sy = (HEIGHT + self.arena_size) // 2 + 10
            draw_flashcard(list_a[0], 15, BLUE, sy)
            draw_flashcard(list_b[0], WIDTH - 255, RED, sy)

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

        self.char_tabs = ["Original", "Pokemon", "Legendary"]
        self.char_tab_idx = 0
        self.chars = list(ORIGINAL_CHARACTER_NAMES)
        self.selected_a: List[str] = []
        self.selected_b: List[str] = []
        self.selecting_team = 0   # 0 = team A, 1 = team B
        self.needed_a = 1
        self.needed_b = 1
        self.hover_char = None

        self.particles = ParticleSystem()
        self.bg_timer = 0.0
        self.scroll_y = 0.0
        self.max_scroll = 500.0

    def _refresh_char_list(self):
        if self.char_tab_idx == 0:
            self.chars = list(ORIGINAL_CHARACTER_NAMES)
        elif self.char_tab_idx == 1:
            self.chars = list(STARTER_POKEMON_NAMES)
        else:
            self.chars = list(LEGENDARY_CHARACTER_NAMES)
        self.scroll_y = 0.0

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
            if event.type == pygame.MOUSEWHEEL:
                self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 30))
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # Left arrow
                if WIDTH//2 - 220 < mx < WIDTH//2 - 160 and HEIGHT//2 - 80 < my < HEIGHT//2:
                    self.mode_idx = (self.mode_idx - 1) % len(self.modes)
                # Right arrow
                elif WIDTH//2 + 160 < mx < WIDTH//2 + 220 and HEIGHT//2 - 80 < my < HEIGHT//2:
                    self.mode_idx = (self.mode_idx + 1) % len(self.modes)
                else:
                    self.needed_a, self.needed_b = self.needed_counts()
                    self.selected_a = []
                    self.selected_b = []
                    self.selecting_team = 0
                    self.state = "char_select"

        elif self.state == "char_select":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "mode_select"
                elif event.key == pygame.K_TAB:
                    self.char_tab_idx = (self.char_tab_idx + 1) % len(self.char_tabs)
                    self._refresh_char_list()
                elif event.key == pygame.K_UP:
                    self.scroll_y = max(0, self.scroll_y - 40)
                elif event.key == pygame.K_DOWN:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 40)
                elif event.key == pygame.K_PAGEUP:
                    self.scroll_y = max(0, self.scroll_y - 300)
                elif event.key == pygame.K_PAGEDOWN:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 300)
                
            if event.type == pygame.MOUSEWHEEL:
                self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 50))
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                tab_y = 104
                tab_w, tab_h = 130, 32
                tab_gap = 12
                tabs_total = len(self.char_tabs) * tab_w + (len(self.char_tabs) - 1) * tab_gap
                tab_start_x = WIDTH//2 - tabs_total//2
                for idx, label in enumerate(self.char_tabs):
                    tx = tab_start_x + idx * (tab_w + tab_gap)
                    if tx <= mx <= tx + tab_w and tab_y <= my <= tab_y + tab_h:
                        self.char_tab_idx = idx
                        self._refresh_char_list()
                        return
                my_adj = my + self.scroll_y
                card_w, card_h = 120, 92
                cols = 4
                start_x = WIDTH//2 - (cols * (card_w+8))//2
                start_y = 140
                for i, name in enumerate(self.chars):
                    col = i % cols
                    row = i // cols
                    cx = start_x + col*(card_w+8)
                    cy = start_y + row*(card_h+8)
                    if cx <= mx <= cx+card_w and cy <= my_adj <= cy+card_h:
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

                # Independent Start button
                footer_y = HEIGHT - 110
                btn_w, btn_h = 180, 45
                bx, by = WIDTH - btn_w - 20, footer_y + 30
                can_start = (self.modes[self.mode_idx] == "Battle Royale" and len(self.selected_a) >= 2) or \
                           (len(self.selected_a) == self.needed_a and len(self.selected_b) == self.needed_b)
                
                if can_start and bx <= mx <= bx+btn_w and by <= my <= by+btn_h:
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

        # Animated character previews (Wrapped)
        chars_preview = list(CHARACTER_DATA.keys())[:12] # Show fewer in wrap
        for i, name in enumerate(chars_preview):
            col = i % 4
            row = i // 4
            x = 80 + col * 125
            y = 340 + row * 85 + int(math.sin(self.bg_timer*1.5 + i*0.5)*10)
            data = CHARACTER_DATA[name]
            pygame.draw.circle(screen, data["color"], (x, y), 20)
            pygame.draw.circle(screen, data["body_color"], (x, y), 20, 3)
            lbl = self.font_small.render(name.split(" ")[1][:8], True, data["color"])
            screen.blit(lbl, (x - lbl.get_width()//2, y + 25))

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
        # 1. Header (Fixed)
        is_br = self.modes[self.mode_idx] == "Battle Royale"
        if is_br:
            title_txt, title_c, needed, selected = "BATTLE ROYALE", GOLD, 8, self.selected_a
            hint_txt = f"Choose 2 to 8 Fighters ({len(selected)}/8)"
        else:
            is_a = self.selecting_team == 0
            title_txt = "SELECT TEAM BLUE" if is_a else "SELECT TEAM RED"
            title_c   = BLUE if is_a else RED
            needed = self.needed_a if is_a else self.needed_b
            selected = self.selected_a if is_a else self.selected_b
            hint_txt = f"Choose {needed} character{'s' if needed>1 else ''}  ({len(selected)}/{needed} selected)"

        title = self.font_big.render(title_txt, True, title_c)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))
        progress = self.font.render(hint_txt, True, WHITE)
        screen.blit(progress, (WIDTH//2 - progress.get_width()//2, 70))

        tab_y = 104
        tab_w, tab_h = 130, 32
        tab_gap = 12
        tabs_total = len(self.char_tabs) * tab_w + (len(self.char_tabs) - 1) * tab_gap
        tab_start_x = WIDTH//2 - tabs_total//2
        for idx, label in enumerate(self.char_tabs):
            tx = tab_start_x + idx * (tab_w + tab_gap)
            active = idx == self.char_tab_idx
            if active and label == "Pokemon":
                fill = (35, 90, 60)
            elif active and label == "Legendary":
                fill = (92, 72, 28)
            elif active:
                fill = (60, 75, 120)
            else:
                fill = (30, 30, 50)
            border = GOLD if active else (90, 90, 120)
            pygame.draw.rect(screen, fill, (tx, tab_y, tab_w, tab_h), border_radius=10)
            pygame.draw.rect(screen, border, (tx, tab_y, tab_w, tab_h), 2, border_radius=10)
            tab_txt = self.font_small.render(label, True, WHITE)
            screen.blit(tab_txt, (tx + tab_w//2 - tab_txt.get_width()//2, tab_y + tab_h//2 - tab_txt.get_height()//2))

        # 2. Scrollable Gallery
        card_w, card_h = 122, 95
        cols = 4
        start_x = WIDTH//2 - (cols * (card_w+8))//2
        start_y = 10
        mx, my = pygame.mouse.get_pos()
        my_adj = my + self.scroll_y - 140 # Gallery starts at y=140

        rows = (len(self.chars) + cols - 1) // cols
        gallery_h = rows * (card_h + 8) + 40
        self.max_scroll = max(0, gallery_h - (HEIGHT - 250))
        
        gallery = pygame.Surface((WIDTH, gallery_h), pygame.SRCALPHA)
        hover_target = None

        for i, name in enumerate(self.chars):
            col = i % cols
            row = i // cols
            cx = start_x + col*(card_w+8)
            cy = start_y + row*(card_h+8)
            data = CHARACTER_DATA[name]

            in_a = name in self.selected_a
            in_b = name in self.selected_b
            hovered = cx <= mx <= cx+card_w and cy <= my_adj <= cy+card_h
            if hovered and 140 <= my <= HEIGHT - 110: 
                hover_target = (cx, cy - self.scroll_y + 140, name, data)

            # Draw Card
            bg_f = (15,45,100,230) if in_a else (120,25,35,230) if in_b else (25,25,50,200)
            if hovered: bg_f = tuple(min(255, c+40) for c in bg_f)
            pygame.draw.rect(gallery, bg_f, (cx, cy, card_w, card_h), border_radius=10)
            pygame.draw.rect(gallery, (GOLD if hovered else WHITE), (cx, cy, card_w, card_h), 1 if not hovered else 2, border_radius=10)

            # Icon & Name
            p = name.split(" ")
            gallery.blit(self.font_big.render(p[0], True, WHITE), (cx+card_w//2-20, cy+10))
            n_s = self.font_small.render(p[1] if len(p)>1 else "", True, WHITE)
            gallery.blit(n_s, (cx+card_w//2-n_s.get_width()//2, cy+62))

            # Selected indicators
            if is_br:
                ct = self.selected_a.count(name)
                if ct > 0: gallery.blit(self.font_small.render(f"x{ct}", True, GOLD), (cx+6, cy+6))
            else:
                ca, cb = self.selected_a.count(name), self.selected_b.count(name)
                if ca>0: gallery.blit(self.font_small.render(f"A{ca if ca>1 else ''}", True, CYAN), (cx+6, cy+6))
                if cb>0: gallery.blit(self.font_small.render(f"B{cb if cb>1 else ''}", True, PINK), (cx+card_w-20, cy+6))

        gallery_rect = pygame.Rect(0, 140, WIDTH, HEIGHT - 250)
        screen.set_clip(gallery_rect)
        screen.blit(gallery, (0, 140 - self.scroll_y))
        screen.set_clip(None)

        # 2.5 Scrollbar Visual
        if self.max_scroll > 0:
            bar_bh = HEIGHT - 250
            bar_h = max(20, (bar_bh / (self.max_scroll + bar_bh)) * bar_bh)
            bar_y = 140 + (self.scroll_y / self.max_scroll) * (bar_bh - bar_h)
            pygame.draw.rect(screen, (50, 50, 70), (WIDTH - 8, 140, 4, bar_bh))
            pygame.draw.rect(screen, GOLD, (WIDTH - 8, bar_y, 4, bar_h))

        # 3. Footer (Fixed)
        footer_y = HEIGHT - 110
        pygame.draw.rect(screen, (10,10,20), (0, footer_y, WIDTH, 110))
        pygame.draw.line(screen, (50,50,70), (0, footer_y), (WIDTH, footer_y), 2)

        # Team Summaries
        if self.modes[self.mode_idx] == "Battle Royale":
            sel_txt = "Selected: " + (", ".join(self.selected_a[:4]) + ("..." if len(self.selected_a)>4 else ""))
            s_surf = self.font_small.render(sel_txt or "No one selected", True, GOLD)
            screen.blit(s_surf, (20, footer_y + 10))
        else:
            a_txt = "Blue: " + (", ".join([s.split(" ")[-1] for s in self.selected_a]) or "---")
            b_txt = "Red:  " + (", ".join([s.split(" ")[-1] for s in self.selected_b]) or "---")
            asurf = self.font_small.render(a_txt, True, BLUE)
            bsurf = self.font_small.render(b_txt, True, RED)
            screen.blit(asurf, (20, footer_y + 8))
            screen.blit(bsurf, (20, footer_y + 26))

        # Start button
        if (self.modes[self.mode_idx] == "Battle Royale" and len(self.selected_a) >= 2) or \
           (len(self.selected_a) == self.needed_a and len(self.selected_b) == self.needed_b):
            btn_w, btn_h = 220, 50
            bx, by = WIDTH - btn_w - 20, footer_y + 30
            pygame.draw.rect(screen, GREEN, (bx, by, btn_w, btn_h), border_radius=12)
            st_t = self.font.render("START BATTLE", True, BLACK)
            screen.blit(st_t, (bx + btn_w//2 - st_t.get_width()//2, by + btn_h//2 - st_t.get_height()//2))

        # Tooltip (Always on Top)
        if hover_target:
            self._draw_tooltip(screen, hover_target[0], hover_target[1], hover_target[3], hover_target[2])

        self.particles.draw(screen)
        screen.blit(self.font_small.render("ESC = Back to Mode Select", True, SILVER), (20, HEIGHT - 22))

    def _draw_tooltip(self, screen, cx, cy, data, name):
        lines = data["description"].split("\n")
        tip_w = 260
        tx = cx + 130 if cx + 130 + tip_w < WIDTH else cx - tip_w - 10
        ty = max(115, min(cy - 20, HEIGHT - 350))
        th = 45 + len(lines)*18 + len(data["abilities"])*22 + 40
        ts = pygame.Surface((tip_w, th), pygame.SRCALPHA); ts.fill((10,10,30,240))
        pygame.draw.rect(ts, GOLD, (0,0,tip_w,th), 2, border_radius=12)
        screen.blit(ts, (tx, ty))
        curr_y = ty + 12
        screen.blit(self.font.render(name, True, data["color"]), (tx+12, curr_y)); curr_y += 30
        for l in lines:
            screen.blit(self.font_small.render(l.strip(), True, SILVER), (tx+12, curr_y)); curr_y += 18
        curr_y += 8
        for ab in data["abilities"]:
            pygame.draw.circle(screen, ab.color, (tx+16, curr_y+8), 4)
            screen.blit(self.font_small.render(f"{ab.name}: {int(ab.damage)} dmg", True, WHITE), (tx+25, curr_y)); curr_y += 22

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
                    if battle: battle.sounds.stop_bgm()
                    battle = None
                if event.key == pygame.K_SPACE and state == "battle":
                    if battle and battle.over:
                        state = "menu"
                        menu.state = "main"
                        if battle: battle.sounds.stop_bgm()
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
                               
                # Start pokemon music for pokemon battles
                is_pokemon_battle = False
                for b_name in menu.selected_a + menu.selected_b:
                    if b_name in STARTER_POKEMON_NAMES or b_name in LEGENDARY_CHARACTER_NAMES:
                        is_pokemon_battle = True
                
                if is_pokemon_battle:
                    battle.sounds.play_bgm("bgm_pokemon")

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
