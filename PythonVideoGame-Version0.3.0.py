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
    safe_depth = max(0.0, depth)

    scale = ENEMY_MIN_SCALE + (ENEMY_MAX_SCALE - ENEMY_MIN_SCALE) * (safe_depth ** 1.6)
    sx = VP_X + (nx - 0.5) * SCREEN_W * safe_depth
    sy = VP_Y + (ny - 0.5) * SCREEN_H * safe_depth
    return sx, sy, scale

def rects_overlap(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])

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
    cache["player"] = arcade.Texture(img)

    # 2. Dalek Saucer (Heavy Ship)
    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 20, 124, 52], fill=C_DALEK_GOLD)
    d.ellipse([24, 6, 104, 34], fill=C_DALEK_DARK, outline=C_DALEK_GOLD, width=2)
    d.ellipse([58, 2, 70, 14], fill=C_RED)
    cache["saucer"] = arcade.Texture(img)

    # 3. Dalek Infantry (Solo Unit)
    img = Image.new("RGBA", (48, 76), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(4, 70), (44, 70), (36, 34), (12, 34)], fill=C_DALEK_DARK)
    d.rectangle([10, 22, 38, 34], fill=C_DALEK_GOLD)
    d.ellipse([14, 4, 34, 22], fill=C_DALEK_GOLD)
    d.line([24, 12, 46, 12], fill=C_DALEK_DARK, width=2)
    d.ellipse([44, 9, 48, 15], fill=C_RED)
    cache["dalek"] = arcade.Texture(img)

    # 4. Cyberman Warship (Heavy Ship)
    img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(48, 6), (88, 26), (88, 70), (48, 90), (8, 70), (8, 26)], fill=C_CYBER_DARK, outline=C_CYBER_SILVER, width=2)
    d.ellipse([34, 34, 62, 62], fill=C_CYBER_GLOW)
    cache["cybership"] = arcade.Texture(img)

    # 5. Cyberman Infantry (Solo Unit)
    img = Image.new("RGBA", (48, 76), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([12, 26, 36, 70], fill=C_CYBER_SILVER, outline=C_CYBER_DARK, width=2)
    d.rectangle([14, 6, 34, 26], fill=C_CYBER_SILVER)
    d.ellipse([18, 12, 22, 16], fill=C_CYBER_GLOW)
    d.ellipse([26, 12, 30, 16], fill=C_CYBER_GLOW)
    cache["cyberunit"] = arcade.Texture(img)

    # 6. Weeping Angel
    img = Image.new("RGBA", (54, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(14, 74), (40, 74), (32, 32), (22, 32)], fill=C_ANGEL_STONE, outline=C_ANGEL_DARK, width=2)
    d.polygon([(22, 32), (2, 12), (12, 52)], fill=C_ANGEL_DARK)
    d.polygon([(32, 32), (52, 12), (42, 52)], fill=C_ANGEL_DARK)
    d.ellipse([19, 12, 35, 32], fill=C_ANGEL_STONE)
    cache["angel"] = arcade.Texture(img)

    # 7. Projectiles
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 15, 15], fill=C_BULLET)
    d.ellipse([4, 4, 12, 12], fill=C_WHITE)
    cache["bullet"] = arcade.Texture(img)

    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 15, 15], fill=(220, 80, 20))
    d.ellipse([4, 4, 12, 12], fill=(255, 200, 80))
    cache["enemy_bullet_red"] = arcade.Texture(img)

    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 15, 15], fill=C_CYBER_GLOW)
    d.ellipse([4, 4, 12, 12], fill=C_WHITE)
    cache["enemy_bullet_cyan"] = arcade.Texture(img)

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
        cache[f"pickup_{kind}"] = arcade.Texture(img)

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
    W, H = 28, 38

    def __init__(self):
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
        
        self.sprite = arcade.SpriteSolidColor(int(self.W), int(self.H), (255, 255, 255))
        self.sprite.alpha = 0

    def update(self):
        self.x = max(self.W//2, min(SCREEN_W - self.W//2, self.x + self.dx))
        self.y = max(self.H//2, min(SCREEN_H - self.H//2, self.y + self.dy))
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

    def draw(self):
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            return
        x, y   = self.x, self.y
        idle   = math.sin(self.wobble) * 0.055 + math.sin(self.wobble * 0.7) * 0.03
        angle  = self.roll + idle + self.spin
        tilt_x = math.sin(self.pitch) * 5
        hw, hh = self.W / 2, self.H / 2
        
        def rot(px, py):
            c, s = math.cos(angle), math.sin(angle)
            return (x + tilt_x + px*c - py*s, y + px*s + py*c)
            
        bl, br, tr, tl = [rot(px, py) for px, py in [(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)]]
        
        # DRAWING SYNTAX:
        arcade.draw_polygon_filled([bl,br,tr,tl], C_TARDIS_BLUE)
        arcade.draw_polygon_outline([bl,br,tr,tl], C_TARDIS_LIGHT, 2)
        
        def rot_rect(cx, cy, w, h):
            hw2, hh2 = w/2, h/2
            return [rot(cx+px, cy+py) for px,py in [(-hw2,-hh2),(hw2,-hh2),(hw2,hh2),(-hw2,hh2)]]
            
        arcade.draw_polygon_filled(rot_rect(-6, 6, 7, 9), C_TARDIS_LIGHT)
        arcade.draw_polygon_filled(rot_rect( 6, 6, 7, 9), C_TARDIS_LIGHT)
        p1 = rot(0, -hh+4);  p2 = rot(0, hh-12)
        arcade.draw_line(p1[0], p1[1], p2[0], p2[1], C_TARDIS_LIGHT, 1)
        lb = rot(0, hh+5);   lt = rot(0, hh+14)
        arcade.draw_line(lb[0], lb[1], lt[0], lt[1], C_TARDIS_LIGHT, 3)
        arcade.draw_circle_filled(lt[0], lt[1], 4, (220, 240, 255))

    def rect(self):
        return (self.x - self.W//2, self.y - self.H//2,
                self.x + self.W//2, self.y + self.H//2)


class Bullet:
    def __init__(self, px, py, texture):
        self.nx    = px / SCREEN_W
        self.ny    = py / SCREEN_H
        self.depth = 1.0
        self.alive = True
        self.sprite = arcade.Sprite(texture)

    def update(self):
        self.depth -= BULLET_DEPTH_SPEED
        self.nx += (0.5 - self.nx) * BULLET_DEPTH_SPEED * 1.5
        self.ny += (VP_Y / SCREEN_H - self.ny) * BULLET_DEPTH_SPEED * 1.5
        if self.depth <= 0.0:
            self.alive = False

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = (float(scale), float(scale))


class EnemyBullet:
    def __init__(self, sx, py, target_x, target_y, speed, texture):
        self.alive  = True
        self.sprite = arcade.Sprite(texture)
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
        self.sprite    = arcade.Sprite(texture)
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
        if self.depth < 0.35 or self.sprite.scale[0] < 0.25: return None
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
        self.sprite.scale    = (float(scale), float(scale))
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
        self.sprite    = arcade.Sprite(texture)
        self.shoot_cd  = random.uniform(0.5, 2.0)

    def maybe_shoot(self, target_x, target_y, tex_bullet):
        if self.depth < 0.28 or self.sprite.scale[0] < 0.20: return None
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
        self.sprite.scale    = (float(scale), float(scale))
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
        self.sprite    = arcade.Sprite(texture)
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
        if self.depth < 0.25 or self.sprite.scale[0] < 0.18: return None
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
        self.sprite.scale    = (float(scale), float(scale))
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
        self.sprite    = arcade.Sprite(texture)
        self.shoot_cd  = random.uniform(0.6, 2.2)

    def maybe_shoot(self, target_x, target_y, tex_bullet):
        if self.depth < 0.25 or self.sprite.scale[0] < 0.18: return None
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
        self.sprite.scale    = (float(scale), float(scale))
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
        self.sprite    = arcade.Sprite(texture)

    def is_watched(self, pnx, pny, darkness_level=0.0):
        if darkness_level >= 1.0: return False
        same_quad    = (int(pnx>0.5), int(pny>0.5)) == (int(self.nx>0.5), int(self.ny>0.5))
        angel_closer = math.hypot(self.nx-0.5, self.ny-0.5) < math.hypot(pnx-0.5, pny-0.5)
        return same_quad or angel_closer

    def update(self, pnx=0.5, pny=0.5, darkness_level=0.0, is_blinking=False):
        self.frozen = self.is_watched(pnx, pny, darkness_level)
        if self.frozen:
            sx, sy, scale = project(self.nx, self.ny, self.depth)
            self.sprite.center_x = sx; self.sprite.center_y = sy; self.sprite.scale = (scale, scale)
            self.sprite.alpha = min(255, int(255 * (self.depth / 0.12)))
            return

        steer_mult = 3.0 if is_blinking else 1.0
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += (pnx - self.nx) * 0.004 * steer_mult
            self.ny += (pny - self.ny) * 0.004 * steer_mult
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True; self.depth = PATROL_DEPTH
                self.patrol_cd = random.uniform(1.0, 2.5)
        else:
            self.nx += (self.target_nx - self.nx) * PATROL_STEER * 2.2 * steer_mult
            self.ny += (self.target_ny - self.ny) * PATROL_STEER * 2.2 * steer_mult
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self.target_nx = max(0.05, min(0.95, pnx + random.uniform(-0.15, 0.15)))
                self.target_ny = max(0.05, min(0.95, pny + random.uniform(-0.12, 0.12)))
                self.patrol_cd = random.uniform(1.0, 2.5)

        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sprite.center_x = sx
        self.sprite.center_y = sy
        self.sprite.scale    = (float(scale), float(scale))
        self.sprite.alpha    = min(255, int(255 * (self.depth / 0.12)))


class Pickup:
    def __init__(self, sx, sy, kind, texture):
        self.kind  = kind
        self.alive = True
        self.age   = 0
        self.vx    = random.uniform(-1.2, 1.2)
        self.vy    = random.uniform(-1.2, 1.2)
        self.sprite = arcade.Sprite(texture)
        self.sprite.center_x = sx
        self.sprite.center_y = sy

    def update(self, player_x, player_y):
        self.age += 1
        if self.age > 30:
            dx = player_x - self.sprite.center_x
            dy = player_y - self.sprite.center_y
            dist = math.hypot(dx, dy) or 1
            speed = 1.2 + min(3.0, self.age * 0.01)
            self.vx += (dx/dist) * 0.18
            self.vy += (dy/dist) * 0.18
            spd = math.hypot(self.vx, self.vy)
            if spd > speed:
                self.vx = self.vx/spd*speed; self.vy = self.vy/spd*speed
        
        self.sprite.center_x += self.vx
        self.sprite.center_y += self.vy
        if self.age > 420: self.alive = False


# ─────────────────────────────────────────────────────────────────────────────
#  Visual Particles (Manual Render remains optimal for short-term bursts)
# ─────────────────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, colour):
        self.x = x;  self.y = y
        angle = random.uniform(0, 2*math.pi);  speed = random.uniform(1.5, 5)
        self.vx = math.cos(angle)*speed;  self.vy = math.sin(angle)*speed
        self.life = random.randint(15,35);  self.maxlife = self.life
        self.colour = colour;  self.size = random.uniform(2,5);  self.alive = True

    def update(self):
        self.x += self.vx;  self.y += self.vy;  self.vy -= 0.08
        self.life -= 1;  self.size = max(0.5, self.size - 0.1)
        if self.life <= 0: self.alive = False

    def draw(self):
        a = int(255 * (self.life / self.maxlife));  r,g,b = self.colour
        arcade.draw_circle_filled(self.x, self.y, self.size, (r,g,b,a))

def explode(x, y, colours, n=25):
    return [Particle(x, y, random.choice(colours)) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
#  Main System Simulation Loop
# ─────────────────────────────────────────────────────────────────────────────
class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, resizable=False)
        self.state = "title"
        self.textures = bake_procedural_textures()
        self._init_scene()

    def _init_scene(self):
        self.stars           = [Star() for _ in range(160)]
        self.vortex          = [VortexRing() for _ in range(30)]
        self.player          = Player()
        self.bullets         = []
        self.enemies         = []        
        self.daleks          = []        
        self.cybermen        = []        
        self.cyberman_units  = []        
        self.angels          = []
        self.pickups         = []
        self.enemy_bullets   = []
        self.particles       = []
        self.score           = 0
        self.lives           = 3
        self.wave            = 1
        self.spawn_timer     = 0.0
        self.cyber_timer     = 5.0
        self.angel_timer     = 10.0
        self.stat_pierce     = 0
        self.stat_fire       = 0
        self.wave_kills      = 0
        self.wave_target     = 8
        self.angel_survival_elapsed = 0.0 
        self.angel_survival_target  = 30.0 
        self.shoot_cd        = 0.0
        self.flash_msg       = ""
        self.flash_timer     = 0.0
        self._flash_colour   = C_TEXT_GOLD
        self.keys_held       = set()
        self.condition_red   = False
        self.cond_timer      = 0.0
        self.elapsed         = 0.0
        self.darkness_level  = 0.0
        self.is_blinking     = False
        self.blink_timer     = 0.0
        self.last_blink_time = 0.0
        self.blink_duration  = 0.2
        self.blink_cooldown  = 2.0
        self._last_faction   = ""

    def on_key_press(self, key, mod):
        self.keys_held.add(key)
        if self.state == "title" and key in (arcade.key.SPACE, arcade.key.ENTER):
            self.state = "playing"
        if self.state == "game_over" and key == arcade.key.R:
            self._init_scene();  self.state = "playing"

    def on_key_release(self, key, mod):
        self.keys_held.discard(key)

    def on_update(self, dt):
        self.elapsed += dt
        for s in self.stars:   s.update()
        for v in self.vortex:  v.update()
        if self.state != "playing": return

        faction = faction_for_wave(self.wave)
        if faction != self._last_faction:
            self._last_faction = faction
            label, col = {
                "daleks_infantry":   ("DALEK SQUADRON",     C_DALEK_GOLD),
                "daleks_ships":      ("DALEK FLEET",        C_DALEK_GOLD),
                "cybermen_infantry": ("CYBERMAN SECTOR",    C_CYBER_GLOW),
                "cybermen_ships":    ("CYBERMAN INVASION",  C_CYBER_GLOW),
                "angels":            ("ANGEL INCURSION",    C_ANGEL_GLOW),
                "mixed":             ("ALL FORCES",         C_RED),
            }.get(faction, ("", C_WHITE))
            self.flash(f"EPISODE {self.wave}  —  {label}", 3.0, col)

        # Player Engine
        dx = dy = 0
        if arcade.key.LEFT  in self.keys_held or arcade.key.A in self.keys_held: dx -= PLAYER_SPEED
        if arcade.key.RIGHT in self.keys_held or arcade.key.D in self.keys_held: dx += PLAYER_SPEED
        if arcade.key.UP    in self.keys_held or arcade.key.W in self.keys_held: dy += PLAYER_SPEED
        if arcade.key.DOWN  in self.keys_held or arcade.key.S in self.keys_held: dy -= PLAYER_SPEED
        self.player.dx, self.player.dy = dx, dy
        self.player.update()

        # Quantum Sight Controls (Blink Meter)
        if faction in ("angels", "mixed"):
            if self.is_blinking:
                self.blink_timer += dt
                if self.blink_timer >= self.blink_duration:
                    self.is_blinking = False;  self.blink_timer = 0.0
            else:
                self.darkness_level = min(1.0, self.darkness_level + dt * 0.08)
            if arcade.key.B in self.keys_held and self.elapsed - self.last_blink_time >= self.blink_cooldown:
                self.is_blinking = True;  self.blink_timer = 0.0
                self.last_blink_time = self.elapsed
                self.darkness_level = max(0.0, self.darkness_level - 0.35)
        else:
            self.darkness_level = max(0.0, self.darkness_level - dt * 0.5)

        # Weapons Fire
        self.shoot_cd -= dt
        if arcade.key.SPACE in self.keys_held and self.shoot_cd <= 0:
            self.bullets.append(Bullet(self.player.x, self.player.y, self.textures["bullet"]))
            self.shoot_cd = max(0.06, 0.18 - self.stat_fire * 0.02)

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        # ── Spawning Matrix ───────────────────────────────────────────────────
        self.spawn_timer -= dt
        if faction == "daleks_infantry":
            if self.spawn_timer <= 0 and len(self.daleks) < MAX_ENEMIES:
                self.daleks.append(Dalek(self.wave, self.textures["dalek"]))
                self.spawn_timer = max(0.6, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave-1)))
        elif faction in ("daleks_ships", "mixed"):
            if self.spawn_timer <= 0 and len(self.enemies) < MAX_ENEMIES:
                self.enemies.append(Enemy(self.wave, self.textures["saucer"], self.textures["dalek"]))
                self.spawn_timer = max(0.5, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave-1)))
            for e in self.enemies:
                d = e.maybe_deploy()
                if d and len(self.daleks) < MAX_ENEMIES: self.daleks.append(d)

        self.cyber_timer -= dt
        if faction == "cybermen_infantry":
            if self.cyber_timer <= 0 and len(self.cyberman_units) < MAX_ENEMIES:
                self.cyberman_units.append(CybermanUnit(self.wave, self.textures["cyberunit"]))
                self.cyber_timer = max(0.6, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave-1)))
        elif faction in ("cybermen_ships", "mixed"):
            if self.cyber_timer <= 0 and len(self.cybermen) < MAX_ENEMIES:
                self.cybermen.append(Cyberman(self.wave, self.textures["cybership"], self.textures["cyberunit"]))
                self.cyber_timer = max(1.2, 5.0 - (self.wave-4)*0.3 if self.wave > 4 else 5.0)
            for cy in self.cybermen:
                cu = cy.maybe_deploy()
                if cu and len(self.cyberman_units) < MAX_ENEMIES: self.cyberman_units.append(cu)

        self.angel_timer -= dt
        if faction in ("angels", "mixed"):
            max_angels = 4 if faction == "angels" else 2
            if self.angel_timer <= 0 and len(self.angels) < max_angels:
                self.angels.append(WeepingAngel(self.wave, self.textures["angel"]))
                self.angel_timer = max(4.0, 12.0 - (self.wave-7)*1.5 if self.wave > 7 else 12.0)

        if faction in ("cybermen_infantry", "cybermen_ships"):
            self.enemies = []; self.daleks = []
        elif faction == "angels":
            self.enemies = []; self.daleks = []; self.cybermen = []; self.cyberman_units = []

        pnx, pny = self.player.x / SCREEN_W, self.player.y / SCREEN_H

        for e in self.enemies: e.update(pnx, pny)
        self.enemies = [e for e in self.enemies if e.alive]
        for d in self.daleks: d.update(pnx, pny)
        self.daleks = [d for d in self.daleks if d.alive]
        for cy in self.cybermen: cy.update(pnx, pny)
        self.cybermen = [cy for cy in self.cybermen if cy.alive]
        
        dalek_targets = [d for d in self.daleks if d.alive and d.patrolling]
        for cu in self.cyberman_units: cu.update(pnx, pny, dalek_targets)
        self.cyberman_units = [cu for cu in self.cyberman_units if cu.alive]
        for ang in self.angels: ang.update(pnx, pny, self.darkness_level, self.is_blinking)
        self.angels = [ang for ang in self.angels if ang.alive]

        # ── AI Combat Subroutines ─────────────────────────────────────────────
        for e in self.enemies:
            shot = e.maybe_shoot(self.player.x, self.player.y, self.textures["enemy_bullet_red"])
            if shot: self.enemy_bullets.append(shot)
        for d in self.daleks:
            cyber_targets = [cu for cu in self.cyberman_units if cu.alive] + [cy for cy in self.cybermen if cy.alive]
            if cyber_targets and random.random() < 0.15:
                t = random.choice(cyber_targets)
                shot = d.maybe_shoot(t.sprite.center_x, t.sprite.center_y, self.textures["enemy_bullet_red"])
            else:
                shot = d.maybe_shoot(self.player.x, self.player.y, self.textures["enemy_bullet_red"])
            if shot: self.enemy_bullets.append(shot)
        for cy in self.cybermen:
            shot = cy.maybe_shoot(self.player.x, self.player.y, self.textures["enemy_bullet_cyan"])
            if shot: self.enemy_bullets.append(shot)
        for cu in self.cyberman_units:
            dalek_targets2 = [d for d in self.daleks if d.alive] + [e for e in self.enemies if e.alive]
            if dalek_targets2 and random.random() < 0.12:
                t = random.choice(dalek_targets2)
                shot = cu.maybe_shoot(t.sprite.center_x, t.sprite.center_y, self.textures["enemy_bullet_cyan"])
            else:
                shot = cu.maybe_shoot(self.player.x, self.player.y, self.textures["enemy_bullet_cyan"])
            if shot: self.enemy_bullets.append(shot)

        for eb in self.enemy_bullets: eb.update()
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

        # ── Hardware Accelerated Collision Detection ──────────────────────────
        def try_hit(bullet, entity, points, particle_cols, drop=None, chance=0.0):
            if not (bullet.alive and entity.alive and arcade.check_for_collision(bullet.sprite, entity.sprite)):
                return False
            if random.random() >= self.stat_pierce * 0.10: bullet.alive = False
            entity.alive = False
            self.score += points * self.wave
            self.wave_kills += 1
            self.particles += explode(entity.sprite.center_x, entity.sprite.center_y, particle_cols)
            if drop and random.random() < chance:
                self.pickups.append(Pickup(entity.sprite.center_x, entity.sprite.center_y, drop, self.textures[f"pickup_{drop}"]))
            return True

        for b in self.bullets:
            for e in self.enemies:
                if try_hit(b, e, 100, [C_DALEK_GOLD, C_DALEK_DARK, C_WHITE], "life", 0.09): break
            for d in self.daleks:
                if try_hit(b, d, 150, [C_DALEK_GOLD, C_RED, C_WHITE], "pierce", 0.11): break
            for cy in self.cybermen:
                if try_hit(b, cy, 200, [C_CYBER_SILVER, C_CYBER_GLOW, C_WHITE], "fire", 0.15): break
            for cu in self.cyberman_units:
                if try_hit(b, cu, 180, [C_CYBER_SILVER, C_CYBER_DARK, C_WHITE], "fire", 0.12): break
            for ang in self.angels:
                if b.alive and ang.alive and arcade.check_for_collision(b.sprite, ang.sprite):
                    b.alive = False
                    self.score += 50 * self.wave
                    self.particles += explode(ang.sprite.center_x, ang.sprite.center_y, [C_ANGEL_STONE, C_WHITE], n=12)
                    break

        # Infighting logic
        for eb in self.enemy_bullets:
            if eb.sprite.texture == self.textures["enemy_bullet_cyan"]: # Cyber laser
                for d in self.daleks:
                    if eb.alive and d.alive and arcade.check_for_collision(eb.sprite, d.sprite):
                        eb.alive = False; d.alive = False
                        self.particles += explode(d.sprite.center_x, d.sprite.center_y, [C_DALEK_GOLD, C_RED])
                        break
            else: # Dalek laser
                for cu in self.cyberman_units:
                    if eb.alive and cu.alive and arcade.check_for_collision(eb.sprite, cu.sprite):
                        eb.alive = False; cu.alive = False
                        self.particles += explode(cu.sprite.center_x, cu.sprite.center_y, [C_CYBER_SILVER, C_CYBER_GLOW])
                        break

        # ── Threat Response / Damage Registers ────────────────────────────────
        def register_damage(attacker=None):
            if attacker: attacker.alive = False
            self.particles += explode(self.player.x, self.player.y, [C_TARDIS_BLUE, C_TARDIS_LIGHT, C_WHITE], n=40)
            self.lives -= 1
            if self.lives <= 0:
                self.state = "game_over"
            else:
                self.player.invuln = 75
                self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)

        if self.player.invuln == 0:
            hit_registered = False
            for group in [self.enemies, self.daleks, self.cybermen, self.cyberman_units]:
                if hit_registered: break
                for obj in group:
                    if arcade.check_for_collision(self.player.sprite, obj.sprite):
                        register_damage(obj); hit_registered = True; break
            if not hit_registered:
                for eb in self.enemy_bullets:
                    if arcade.check_for_collision(self.player.sprite, eb.sprite):
                        eb.alive = False; register_damage(); break

        # Angel Displacement Core
        if self.player.invuln == 0:
            for ang in self.angels:
                if not ang.frozen and arcade.check_for_collision(self.player.sprite, ang.sprite):
                    ang.alive = False
                    self.particles += explode(self.player.x, self.player.y, [C_ANGEL_STONE, C_WHITE], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 75
                        self.wave = random.randint(1, 200)
                        self.wave_kills = 0; self.wave_target = 8 + self.wave * 2
                        self.angel_survival_elapsed = 0.0
                        self.enemies = []; self.daleks = []; self.cybermen = []; self.cyberman_units = []; self.angels = []
                        self._last_faction = ""
                        self.flash(f"TIME VORTEX JUMP! EPISODE {self.wave}", 3.0, C_ANGEL_GLOW)
                    break

        # Item Collection Metrics
        for pk in self.pickups:
            pk.update(self.player.x, self.player.y)
            if arcade.check_for_collision(self.player.sprite, pk.sprite):
                pk.alive = False
                if pk.kind == "life":
                    self.lives += 1; self.flash("+1 REGENERATION", 1.5, C_DROP_LIFE)
                elif pk.kind == "pierce":
                    self.stat_pierce += 1; self.flash(f"PIERCE UPGRADED  x{self.stat_pierce}", 1.5, C_DROP_PIERCE)
                elif pk.kind == "fire":
                    self.stat_fire += 1; self.flash(f"FIRE RATE UPGRADED  +{self.stat_fire}", 1.5, C_DROP_FIRE)
        self.pickups = [pk for pk in self.pickups if pk.alive]

        # Chronometer Progression Evaluation
        advance = False
        if faction == "angels":
            self.angel_survival_elapsed += dt
            if self.angel_survival_elapsed >= self.angel_survival_target:
                advance = True; self.angel_survival_elapsed = 0.0
        else:
            if self.wave_kills >= self.wave_target: advance = True

        if advance:
            self.wave += 1
            self.wave_kills = 0; self.wave_target = 8 + self.wave * 2
            self.condition_red = True; self.cond_timer = 6.0

        if self.condition_red:
            self.cond_timer -= dt
            if self.cond_timer <= 0: self.condition_red = False

        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.alive]
        if self.flash_timer > 0: self.flash_timer -= dt

    # ── Render Pipeline ───────────────────────────────────────────────────────
    def on_draw(self):
        self.clear((8, 4, 30))
        for v in self.vortex: v.draw()
        for s in self.stars:  s.draw()

        if self.state == "title":
            self._draw_title(); return

        for p in self.particles: p.draw()

        # ── 3D Batched Pseudo Depth Sorting ───────────────────────────────────
        # Gather all 3D workspace entities dynamically
        render_queue = []
        render_queue.extend(self.enemies)
        render_queue.extend(self.daleks)
        render_queue.extend(self.cybermen)
        render_queue.extend(self.cyberman_units)
        render_queue.extend(self.angels)
        render_queue.extend(self.bullets)
        render_queue.extend(self.enemy_bullets)
        render_queue.extend(self.pickups)

        # Sort elements by pseudo-3D perspective depth layer
        render_queue.sort(key=lambda item: getattr(item, 'depth', 1.0))

        # Push elements sequentially into a clean hardware batch draw array
        batch_draw_list = arcade.SpriteList()
        for obj in render_queue:
            batch_draw_list.append(obj.sprite)
        
        batch_draw_list.draw()

        # Draw the main cockpit avatar over the workspace layer
        if not (self.player.invuln > 0 and (self.player.invuln // 4) % 2 == 0):
            self.player.draw()

        if self.darkness_level > 0:
            draw_overlay(int(self.darkness_level * 210))

        # ── HUD Display System ────────────────────────────────────────────────
        faction = faction_for_wave(self.wave)
        clean_name = {"daleks_infantry": "DALEKS", "daleks_ships": "DALEK FLEET", "cybermen_infantry": "CYBERMEN",
                      "cybermen_ships": "CYBER INVASION", "angels": "WEEPING ANGELS", "mixed": "MIXED ERA"}.get(faction, "VORTEX")

        arcade.draw_text(f"SCORE  {self.score:06d}", 14, SCREEN_H-28, C_TEXT_GOLD, 16, font_name="Courier New", bold=True)
        arcade.draw_text(f"EP {self.wave}  [{clean_name}]", SCREEN_W//2, SCREEN_H-28, C_TEXT_BLUE, 14, anchor_x="center", font_name="Courier New", bold=True)
        
        if faction == "angels":
            rem = max(0.0, self.angel_survival_target - self.angel_survival_elapsed)
            arcade.draw_text(f"TIME REMAINING: {rem:.1f}s", SCREEN_W//2, SCREEN_H-52, C_ANGEL_GLOW, 13, anchor_x="center", font_name="Courier New", bold=True)

        for i in range(min(self.lives, 13)):
            draw_rect_filled(SCREEN_W - 20 - i*22, SCREEN_H-20, 14, 18, C_TARDIS_BLUE)
            draw_rect_outline(SCREEN_W - 20 - i*22, SCREEN_H-20, 14, 18, C_TARDIS_LIGHT, 1)

        if self.stat_pierce > 0: arcade.draw_text(f"PIERCE x{self.stat_pierce}", 14, 14, C_DROP_PIERCE, 13, font_name="Courier New", bold=True)
        if self.stat_fire > 0: arcade.draw_text(f"FIRE +{self.stat_fire}", 14, 30, C_DROP_FIRE, 13, font_name="Courier New", bold=True)
        
        if faction in ("angels", "mixed") and self.darkness_level > 0:
            bar_w = 120; filled = int(bar_w * (1.0 - self.darkness_level))
            draw_rect_filled(SCREEN_W//2, 18, bar_w, 10, (40,40,40))
            if filled > 0: draw_rect_filled(SCREEN_W//2 - (bar_w-filled)//2, 18, filled, 10, C_ANGEL_GLOW)
            arcade.draw_text("BLINK [B]", SCREEN_W//2, 30, C_ANGEL_GLOW, 11, anchor_x="center", font_name="Courier New")

        if self.flash_timer > 0:
            arcade.draw_text(self.flash_msg, SCREEN_W//2, SCREEN_H//2+30, self._flash_colour, 24, anchor_x="center", anchor_y="center", font_name="Courier New", bold=True)
        if self.condition_red:
            arcade.draw_text("!! CONDITION RED !!", SCREEN_W//2, SCREEN_H//2-20, C_RED, 20, anchor_x="center", font_name="Courier New", bold=True)
        if self.state == "game_over":
            self._draw_game_over()

    def _draw_title(self):
        draw_overlay(170)
        draw_rect_filled(SCREEN_W//2, SCREEN_H//2+220, 56, 76, C_TARDIS_BLUE)
        draw_rect_outline(SCREEN_W//2, SCREEN_H//2+220, 56, 76, C_TARDIS_LIGHT, 3)
        arcade.draw_text("TARDIS  VOID", SCREEN_W//2, SCREEN_H//2+130, C_TARDIS_LIGHT, 52, anchor_x="center", font_name="Courier New", bold=True)
        arcade.draw_text("A  D O C T O R  W H O  S P A C E  S H O O T E R", SCREEN_W//2, SCREEN_H//2+80, C_TEXT_GOLD, 14, anchor_x="center", font_name="Courier New")
        controls = [
            ("ARROW KEYS / WASD  —  Move",         0),
            ("SPACE              —  Fire",          28),
            ("B                  —  Blink (EP 7)",  56),
            ("Daleks (EP 1-3)  •  Cybermen (EP 4-6)  •  Angels (EP 7)  •  All (EP 8+)", 84),
        ]
        for text, offset in controls:
            arcade.draw_text(text, SCREEN_W//2, SCREEN_H//2-10-offset, C_TEXT_BLUE, 13, anchor_x="center", font_name="Courier New")
        if int(self.elapsed*2) % 2 == 0:
            arcade.draw_text("PRESS  SPACE  TO  BEGIN", SCREEN_W//2, SCREEN_H//2-150, C_TEXT_GOLD, 20, anchor_x="center", font_name="Courier New", bold=True)

    def _draw_game_over(self):
        draw_overlay(200)
        arcade.draw_text("EXTERMINATED", SCREEN_W//2, SCREEN_H//2+80, C_RED, 54, anchor_x="center", font_name="Courier New", bold=True)
        arcade.draw_text(f"FINAL SCORE:  {self.score:06d}", SCREEN_W//2, SCREEN_H//2+10, C_TEXT_GOLD, 24, anchor_x="center", font_name="Courier New")
        arcade.draw_text(f"REACHED EPISODE:  {self.wave}", SCREEN_W//2, SCREEN_H//2-30, C_TEXT_BLUE, 18, anchor_x="center", font_name="Courier New")
        if int(self.elapsed*2) % 2 == 0:
            arcade.draw_text("PRESS  R  TO  REGENERATE", SCREEN_W//2, SCREEN_H//2-110, C_TEXT_GOLD, 18, anchor_x="center", font_name="Courier New", bold=True)

    def flash(self, msg, duration, colour):
        self.flash_msg = msg;  self.flash_timer = duration;  self._flash_colour = colour

def main():
    GameWindow()
    arcade.run()

if __name__ == "__main__":
    main()