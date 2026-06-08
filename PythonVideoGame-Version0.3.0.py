"""
TARDIS VOID — A Doctor Who Space Shooter
 
Controls:
    Arrow keys / WASD  — Move the TARDIS
    Space              — Fire
    B                  — Blink (During Angel Waves)
    R                  — Restart (on Game Over screen)
 
Requirements:
    pip install arcade pillow
"""
 
import arcade
import random
import math
from PIL import Image, ImageDraw
 
# ── Window ───────────────────────────────────────────────────────────────────
SCREEN_W = 900
SCREEN_H = 700
TITLE    = "TARDIS VOID"
 
# ── Gameplay constants ────────────────────────────────────────────────────────
PLAYER_SPEED         = 5
BULLET_SPEED         = 10
ENEMY_BASE_SPEED     = 1.2
ENEMY_SPAWN_INTERVAL = 1.8
MAX_ENEMIES          = 12
 
# ── Pseudo-3D projection ─────────────────────────────────────────────────────
VP_X = SCREEN_W / 2
VP_Y = SCREEN_H / 2
ENEMY_DEPTH_SPEED  = 0.004
ENEMY_MIN_SCALE    = 0.04
ENEMY_MAX_SCALE    = 1.0
PATROL_DEPTH       = 0.82
PATROL_STEER       = 0.025
BULLET_DEPTH_SPEED = 0.06
 
# ── Colours ───────────────────────────────────────────────────────────────────
C_VORTEX_BLUE  = (20,  80, 200)
C_VORTEX_ORG   = (200, 90,  10)
C_TARDIS_BLUE  = (30, 120, 220)
C_TARDIS_LIGHT = (180, 220, 255)
C_DALEK_GOLD   = (210, 170,  30)
C_DALEK_DARK   = (120,  80,   5)
C_BULLET       = (100, 220, 255)
C_STAR_DIM     = (80,   80, 120)
C_STAR_BRIGHT  = (200, 200, 255)
C_WHITE        = (255, 255, 255)
C_RED          = (230,  40,  40)
C_TEXT_GOLD    = (220, 190,  60)
C_TEXT_BLUE    = (120, 180, 255)
C_DROP_LIFE    = (220,  60,  80)
C_DROP_PIERCE  = (255, 200,  40)
C_DROP_FIRE    = ( 60, 220, 140)
C_ANGEL_STONE  = (140, 135, 128)
C_ANGEL_DARK   = ( 80,  76,  70)
C_ANGEL_GLOW   = (200, 190, 170)
C_CYBER_SILVER = (160, 175, 190)
C_CYBER_DARK   = ( 50,  60,  70)
C_CYBER_GLOW   = ( 80, 200, 220)

# ── Level schedule ────────────────────────────────────────────────────────────
LEVEL_SCHEDULE = [
    (1,  1,  "daleks_infantry"),   
    (2,  3,  "daleks_ships"),      
    (4,  4,  "cybermen_infantry"), 
    (5,  6,  "cybermen_ships"),    
    (7,  7,  "angels"),            
    (8,  999,"mixed"),             
]

def faction_for_wave(wave):
    for start, end, faction in LEVEL_SCHEDULE:
        if start <= wave <= end:
            return faction
    return "mixed"

def project(nx, ny, depth):
    scale = ENEMY_MIN_SCALE + (ENEMY_MAX_SCALE - ENEMY_MIN_SCALE) * (depth ** 1.6)
    sx = VP_X + (nx - 0.5) * SCREEN_W * depth
    sy = VP_Y + (ny - 0.5) * SCREEN_H * depth
    return sx, sy, scale

def draw_rect_filled(cx, cy, w, h, colour):
    arcade.draw_lrbt_rectangle_filled(cx - w/2, cx + w/2, cy - h/2, cy + h/2, colour)

def draw_rect_outline(cx, cy, w, h, colour, border=2):
    arcade.draw_lrbt_rectangle_outline(cx - w/2, cx + w/2, cy - h/2, cy + h/2, colour, border)

def draw_overlay(alpha):
    arcade.draw_lrbt_rectangle_filled(0, SCREEN_W, 0, SCREEN_H, (0, 0, 10, alpha))


# ─────────────────────────────────────────────────────────────────────────────
#  Procedural Texture Bakery (Option A)
# ─────────────────────────────────────────────────────────────────────────────
def bake_procedural_textures():
    cache = {}

    # 1. TARDIS (Player)
    img = Image.new("RGBA", (64, 86), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([12, 12, 52, 80], fill=C_TARDIS_BLUE, outline=C_TARDIS_LIGHT, width=2)
    d.rectangle([18, 22, 30, 36], fill=C_TARDIS_LIGHT)
    d.rectangle([34, 22, 46, 36], fill=C_TARDIS_LIGHT)
    d.ellipse([28, 2, 36, 10], fill=(220, 240, 255))
    cache["player"] = arcade.Texture("player", img)

    # 2. Dalek Saucer (Heavy Ship)
    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 20, 124, 52], fill=C_DALEK_GOLD)
    d.ellipse([24, 6, 104, 34], fill=C_DALEK_DARK, outline=C_DALEK_GOLD, width=2)
    d.ellipse([58, 2, 70, 14], fill=C_RED)
    cache["saucer"] = arcade.Texture("saucer", img)

    # 3. Dalek Infantry (Solo Unit)
    img = Image.new("RGBA", (48, 76), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(4, 70), (44, 70), (36, 34), (12, 34)], fill=C_DALEK_DARK)
    d.rectangle([10, 22, 38, 34], fill=C_DALEK_GOLD)
    d.ellipse([14, 4, 34, 22], fill=C_DALEK_GOLD)
    d.line([24, 12, 46, 12], fill=C_DALEK_DARK, width=2)
    d.ellipse([44, 9, 48, 15], fill=C_RED)
    cache["dalek"] = arcade.Texture("dalek", img)

    # 4. Cyberman Warship (Heavy Ship)
    img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(48, 6), (88, 26), (88, 70), (48, 90), (8, 70), (8, 26)], fill=C_CYBER_DARK, outline=C_CYBER_SILVER, width=2)
    d.ellipse([34, 34, 62, 62], fill=C_CYBER_GLOW)
    cache["cybership"] = arcade.Texture("cybership", img)

    # 5. Cyberman Infantry (Solo Unit)
    img = Image.new("RGBA", (48, 76), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([12, 26, 36, 70], fill=C_CYBER_SILVER, outline=C_CYBER_DARK, width=2)
    d.rectangle([14, 6, 34, 26], fill=C_CYBER_SILVER)
    d.ellipse([18, 12, 22, 16], fill=C_CYBER_GLOW)
    d.ellipse([26, 12, 30, 16], fill=C_CYBER_GLOW)
    cache["cyberunit"] = arcade.Texture("cyberunit", img)

    # 6. Weeping Angel
    img = Image.new("RGBA", (54, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(14, 74), (40, 74), (32, 32), (22, 32)], fill=C_ANGEL_STONE, outline=C_ANGEL_DARK, width=2)
    d.polygon([(22, 32), (2, 12), (12, 52)], fill=C_ANGEL_DARK)
    d.polygon([(32, 32), (52, 12), (42, 52)], fill=C_ANGEL_DARK)
    d.ellipse([19, 12, 35, 32], fill=C_ANGEL_STONE)
    cache["angel"] = arcade.Texture("angel", img)

    # 7. Projectiles
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 15, 15], fill=C_BULLET)
    d.ellipse([4, 4, 12, 12], fill=C_WHITE)
    cache["bullet"] = arcade.Texture("bullet", img)

    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 15, 15], fill=(220, 80, 20))
    d.ellipse([4, 4, 12, 12], fill=(255, 200, 80))
    cache["enemy_bullet_red"] = arcade.Texture("enemy_bullet_red", img)

    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 15, 15], fill=C_CYBER_GLOW)
    d.ellipse([4, 4, 12, 12], fill=C_WHITE)
    cache["enemy_bullet_cyan"] = arcade.Texture("enemy_bullet_cyan", img)

    # 8. Modifiers / Pickups
    for kind, col in [("life", C_DROP_LIFE), ("pierce", C_DROP_PIERCE), ("fire", C_DROP_FIRE)]:
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([2, 2, 30, 30], fill=col, outline=C_WHITE, width=2)
        if kind == "life":
            d.rectangle([14, 8, 18, 24], fill=C_WHITE)
            d.rectangle([8, 14, 24, 18], fill=C_WHITE)
        elif kind == "pierce":
            d.polygon([(16, 6), (24, 24), (8, 24)], fill=C_WHITE)
        elif kind == "fire":
            d.ellipse([10, 10, 22, 22], fill=C_WHITE)
        cache[f"pickup_{kind}"] = arcade.Texture(f"pickup_{kind}", img)

    return cache


# ─────────────────────────────────────────────────────────────────────────────
#  Starfield & Ambient Environment
# ─────────────────────────────────────────────────────────────────────────────
class Star:
    def __init__(self):
        self.reset(random.uniform(0, SCREEN_H))

    def reset(self, y=None):
        self.x      = random.uniform(0, SCREEN_W)
        self.y      = y if y is not None else SCREEN_H + 2
        layer       = random.randint(0, 2)
        self.speed  = [0.4, 0.9, 1.8][layer]
        self.size   = [1.0, 1.5, 2.5][layer]
        self.colour = [C_STAR_DIM, C_STAR_DIM, C_STAR_BRIGHT][layer]

    def update(self):
        self.y -= self.speed
        if self.y < -2: self.reset()

    def draw(self):
        arcade.draw_circle_filled(self.x, self.y, self.size, self.colour)

class VortexRing:
    def __init__(self):
        self.reset()

    def reset(self):
        self.radius = random.uniform(5, 30)
        self.grow   = random.uniform(2.5, 5.5)
        self.alpha  = random.randint(25, 65)
        self.colour = random.choice([C_VORTEX_BLUE, C_VORTEX_ORG])

    def update(self):
        self.radius += self.grow
        self.alpha  -= 1
        if self.alpha <= 0 or self.radius > math.hypot(SCREEN_W, SCREEN_H):
            self.reset()

    def draw(self):
        r, g, b = self.colour
        arcade.draw_circle_outline(VP_X, VP_Y, self.radius, (r, g, b, max(0, self.alpha)), 1)


# ─────────────────────────────────────────────────────────────────────────────
#  Game Entities (Driven by Sprites)
# ─────────────────────────────────────────────────────────────────────────────
class Player:
    def __init__(self, texture):
        self.x         = SCREEN_W / 2
        self.y         = 80
        self.dx        = 0
        self.dy        = 0
        self.invuln    = 0
        self.roll      = 0.0
        self.pitch     = 0.0
        self.wobble    = 0.0
        self.spin      = 0.0
        self.spin_vel  = 0.0
        self.sprite    = arcade.Sprite(texture=texture)

    def update(self):
        self.x = max(20, min(SCREEN_W - 20, self.x + self.dx))
        self.y = max(25, min(SCREEN_H - 25, self.y + self.dy))
        if self.invuln > 0:
            self.invuln -= 1
        
        target_roll  = math.radians(-self.dx * 2.2)
        self.roll   += (target_roll - self.roll) * 0.12
        target_pitch = math.radians(self.dy * 1.4)
        self.pitch  += (target_pitch - self.pitch) * 0.10
        
        if math.hypot(self.dx, self.dy) > PLAYER_SPEED * 1.3:
            self.spin_vel += 0.008
        self.spin_vel *= 0.97
        self.spin     += self.spin_vel
        self.wobble   += 0.04

        self.sprite.center_x = self.x
        self.sprite.center_y = self.y
        self.sprite.angle    = math.degrees(self.roll + math.sin(self.wobble)*0.055 + self.spin)


class Bullet:
    def __init__(self, px, py, texture):
        self.nx    = px / SCREEN_W
        self.ny    = py / SCREEN_H
        self.depth = 1.0
        self.alive = True
        self.sprite = arcade.Sprite(texture=texture)

    def update(self):
        self.depth -= BULLET_DEPTH_SPEED
        self.nx += (0.5 - self.nx) * BULLET_DEPTH_SPEED * 1.5
        self.ny += (VP_Y / SCREEN_H - self.ny) * BULLET_DEPTH_SPEED * 1.5
        if self.depth <= 0.0:
            self.alive = False

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = scale


class EnemyBullet:
    def __init__(self, sx, py, target_x, target_y, speed, texture):
        self.alive  = True
        self.sprite = arcade.Sprite(texture=texture)
        self.sprite.center_x = sx
        self.sprite.center_y = py
        
        dx = target_x - sx
        dy = target_y - py
        dist = math.hypot(dx, dy) or 1
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed

    def update(self):
        self.sprite.center_x += self.vx
        self.sprite.center_y += self.vy
        if (self.sprite.center_x < -20 or self.sprite.center_x > SCREEN_W + 20 or 
            self.sprite.center_y < -20 or self.sprite.center_y > SCREEN_H + 20):
            self.alive = False


class Enemy:
    def __init__(self, wave, texture, child_texture):
        self.nx    = random.uniform(0.3, 0.7)
        self.ny    = random.uniform(0.4, 0.6)
        self.dnx   = random.uniform(-0.0008, 0.0008)
        self.dny   = random.uniform(-0.0004, 0.0002)
        self.depth = 0.0
        wave_mult  = 1 + (wave - 1) * 0.12
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.8, 1.3) * wave_mult
        self.alive = True
        self.wave  = wave
        self.patrolling = False
        self.target_nx = self.nx
        self.target_ny = self.ny
        self.patrol_cd = 0.0
        self.deploy_cd = random.uniform(4.0, 8.0)
        self.deployed  = 0
        self.sprite    = arcade.Sprite(texture=texture)
        self.child_tex = child_texture
        self.shoot_cd  = random.uniform(1.5, 3.5)

    def maybe_deploy(self):
        if self.depth < 0.30 or self.deployed >= 2: return None
        self.deploy_cd -= 1/60
        if self.deploy_cd <= 0:
            self.deploy_cd = random.uniform(5.0, 9.0)
            self.deployed += 1
            return Dalek(self.wave, self.child_tex, self.nx, self.ny, self.depth)
        return None

    def maybe_shoot(self, target_x, target_y, tex_bullet):
        if self.depth < 0.35 or self.sprite.scale < 0.25: return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.5, 2.8 - (self.wave-1) * 0.15)
            self.shoot_cd = random.uniform(base_cd*0.7, base_cd) * (1.0 - self.depth*0.45)
            speed = (3.5 + self.depth*3.0) + (self.wave-1)*0.4
            return EnemyBullet(self.sprite.center_x, self.sprite.center_y, target_x, target_y, speed, tex_bullet)
        return None

    def update(self, pnx=0.5, pny=0.5):
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*2)
            self.ny += self.dny * (1 + self.depth*2)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True; self.depth = PATROL_DEPTH
                self.patrol_cd = random.uniform(2.5, 5.0)
        else:
            self.nx += (self.target_nx - self.nx) * PATROL_STEER
            self.ny += (self.target_ny - self.ny) * PATROL_STEER
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self.target_nx = max(0.05, min(0.95, pnx + random.uniform(-0.2, 0.2)))
                self.target_ny = max(0.05, min(0.95, pny + random.uniform(-0.15, 0.15)))
                self.patrol_cd = random.uniform(2.5, 5.0)

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = scale
        self.sprite.alpha    = min(255, int(255 * (self.depth / 0.15)))


class Dalek:
    def __init__(self, wave, texture, spawn_nx=None, spawn_ny=None, spawn_depth=None):
        self.nx    = spawn_nx if spawn_nx is not None else random.uniform(0.2, 0.8)
        self.ny    = spawn_ny if spawn_ny is not None else random.uniform(0.3, 0.7)
        self.dnx   = random.uniform(-0.0014, 0.0014)
        self.dny   = random.uniform(-0.0006, 0.0004)
        self.depth = spawn_depth if spawn_depth is not None else 0.0
        wave_mult  = 1 + (wave-1) * 0.10
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.7, 1.1) * wave_mult
        self.alive = True
        self.wave  = wave
        self.patrolling = False
        self.target_nx = self.nx
        self.target_ny = self.ny
        self.patrol_cd = 0.0
        self.sprite    = arcade.Sprite(texture=texture)
        self.shoot_cd  = random.uniform(0.5, 2.0)

    def maybe_shoot(self, target_x, target_y, tex_bullet):
        if self.depth < 0.28 or self.sprite.scale < 0.20: return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.3, 1.8 - (self.wave-1)*0.10)
            self.shoot_cd = random.uniform(base_cd*0.6, base_cd) * (1.0 - self.depth*0.4)
            speed = (4.5 + self.depth*3.5) + (self.wave-1)*0.45
            return EnemyBullet(self.sprite.center_x, self.sprite.center_y, target_x, target_y, speed, tex_bullet)
        return None

    def update(self, pnx=0.5, pny=0.5):
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*2)
            self.ny += self.dny * (1 + self.depth*2)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True; self.depth = PATROL_DEPTH
                self.patrol_cd = random.uniform(1.5, 3.5)
        else:
            self.nx += (self.target_nx - self.nx) * PATROL_STEER * 1.4
            self.ny += (self.target_ny - self.ny) * PATROL_STEER * 1.4
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self.target_nx = max(0.05, min(0.95, pnx + random.uniform(-0.2, 0.2)))
                self.target_ny = max(0.05, min(0.95, pny + random.uniform(-0.15, 0.15)))
                self.patrol_cd = random.uniform(1.5, 3.5)

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = scale
        self.sprite.alpha    = min(255, int(255 * (self.depth / 0.12)))


class Cyberman:
    def __init__(self, wave, texture, child_texture):
        self.nx    = random.uniform(0.44, 0.56)
        self.ny    = random.uniform(0.44, 0.56)
        self.dnx   = random.uniform(-0.0006, 0.0006)
        self.dny   = random.uniform(-0.0003, 0.0003)
        self.depth = 0.0
        wave_mult  = 1 + (wave-1) * 0.09
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.6, 0.95) * wave_mult
        self.alive = True
        self.wave  = wave
        self.patrolling = False
        self.target_nx = self.nx
        self.target_ny = self.ny
        self.patrol_cd = 0.0
        self.deploy_cd = random.uniform(2.0, 4.0)
        self.deployed  = 0
        self.sprite    = arcade.Sprite(texture=texture)
        self.child_tex = child_texture
        self.shoot_cd  = random.uniform(1.0, 3.0)

    def maybe_deploy(self):
        if self.depth < 0.25 or self.deployed >= 3: return None
        self.deploy_cd -= 1/60
        if self.deploy_cd <= 0:
            self.deploy_cd = random.uniform(2.5, 5.0)
            self.deployed += 1
            return CybermanUnit(self.wave, self.child_tex, self.nx, self.ny, self.depth)
        return None

    def maybe_shoot(self, target_x, target_y, tex_bullet):
        if self.depth < 0.25 or self.sprite.scale < 0.18: return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.6, 3.2 - (self.wave-1)*0.14)
            self.shoot_cd = random.uniform(base_cd*0.7, base_cd) * (1.0 - self.depth*0.35)
            speed = (5.5 + self.depth*4.0) + (self.wave-1)*0.5
            return EnemyBullet(self.sprite.center_x, self.sprite.center_y, target_x, target_y, speed, tex_bullet)
        return None

    def update(self, pnx=0.5, pny=0.5):
        self.sprite.angle += 1.2
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*1.5)
            self.ny += self.dny * (1 + self.depth*1.5)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True; self.depth = PATROL_DEPTH
                self.patrol_cd = random.uniform(3.0, 6.0)
        else:
            self.nx += (self.target_nx - self.nx) * PATROL_STEER * 0.7
            self.ny += (self.target_ny - self.ny) * PATROL_STEER * 0.7
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self.target_nx = max(0.05, min(0.95, pnx + random.uniform(-0.25, 0.25)))
                self.target_ny = max(0.05, min(0.95, pny + random.uniform(-0.2, 0.2)))
                self.patrol_cd = random.uniform(3.0, 6.0)

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = scale
        self.sprite.alpha    = min(255, int(255 * (self.depth / 0.12)))


class CybermanUnit:
    def __init__(self, wave, texture, spawn_nx=None, spawn_ny=None, spawn_depth=None):
        self.nx    = spawn_nx if spawn_nx is not None else random.uniform(0.2, 0.8)
        self.ny    = spawn_ny if spawn_ny is not None else random.uniform(0.3, 0.7)
        self.dnx   = random.uniform(-0.0012, 0.0012)
        self.dny   = random.uniform(-0.0005, 0.0003)
        self.depth = spawn_depth if spawn_depth is not None else 0.0
        wave_mult  = 1 + (wave-1) * 0.08
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.8, 1.2) * wave_mult
        self.alive = True
        self.wave  = wave
        self.patrolling = False
        self.target_nx = self.nx
        self.target_ny = self.ny
        self.patrol_cd = 0.0
        self.sprite    = arcade.Sprite(texture=texture)
        self.shoot_cd  = random.uniform(0.6, 2.2)

    def maybe_shoot(self, target_x, target_y, tex_bullet):
        if self.depth < 0.25 or self.sprite.scale < 0.18: return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.6, 2.0 - (self.wave-1)*0.10)
            self.shoot_cd = random.uniform(base_cd*0.8, base_cd) * (1.0 - self.depth*0.3)
            speed = (6.0 + self.depth*4.5) + (self.wave-1)*0.6
            return EnemyBullet(self.sprite.center_x, self.sprite.center_y, target_x, target_y, speed, tex_bullet)
        return None

    def update(self, pnx=0.5, pny=0.5, dalek_targets=None):
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*1.8)
            self.ny += self.dny * (1 + self.depth*1.8)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True; self.depth = PATROL_DEPTH
                self.patrol_cd = random.uniform(2.0, 4.0)
        else:
            self.nx += (self.target_nx - self.nx) * PATROL_STEER * 1.2
            self.ny += (self.target_ny - self.ny) * PATROL_STEER * 1.2
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                if dalek_targets and random.random() < 0.12:
                    t = random.choice(dalek_targets)
                    self.target_nx = t.nx; self.target_ny = t.ny
                else:
                    self.target_nx = max(0.05, min(0.95, pnx + random.uniform(-0.22, 0.22)))
                    self.target_ny = max(0.05, min(0.95, pny + random.uniform(-0.18, 0.18)))
                self.patrol_cd = random.uniform(2.0, 4.0)

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = scale
        self.sprite.alpha    = min(255, int(255 * (self.depth / 0.12)))


class WeepingAngel:
    def __init__(self, wave, texture):
        angle   = random.uniform(0, math.pi*2)
        self.nx = max(0.05, min(0.95, 0.5 + math.cos(angle)*random.uniform(0.28,0.38)))
        self.ny = max(0.05, min(0.95, 0.5 + math.sin(angle)*random.uniform(0.20,0.28)))
        self.depth = random.uniform(0.25, 0.45)
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.5, 0.8)
        self.alive = True
        self.wave  = wave
        self.frozen = False
        self.patrolling = False
        self.target_nx = self.nx
        self.target_ny = self.ny
        self.patrol_cd = 0.0
        self.sprite    = arcade.Sprite(texture=texture)

    def is_watched(self, p