"""
TARDIS VOID — A Doctor Who Space Shooter
 
Controls:
    Arrow keys / WASD  — Move the TARDIS
    Space              — Fire
    B                  — Blink (During Angel Waves)
    R                  — Restart (on Game Over screen)
 
Requirements:
    pip install arcade
"""
 
import arcade
import random
import math
 
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
# Restructured to divide infantry phases from heavy ship fleet groups
LEVEL_SCHEDULE = [
    (1,  1,  "daleks_infantry"),   # Wave 1: Solo Ground Daleks only
    (2,  3,  "daleks_ships"),      # Waves 2-3: Dalek Saucers arrive + deploy units
    (4,  4,  "cybermen_infantry"), # Wave 4: Solo Cyberman infantry units only
    (5,  6,  "cybermen_ships"),    # Waves 5-6: Cyberman Ships arrive + deploy units
    (7,  7,  "angels"),            # Wave 7: Weeping Angels ONLY (Timed survival stage)
    (8,  999,"mixed"),             # Wave 8+: Total chaos free-for-all
]

def faction_for_wave(wave):
    for start, end, faction in LEVEL_SCHEDULE:
        if start <= wave <= end:
            return faction
    return "mixed"

 
# ── Draw helpers ─────────────────────────────────────────────────────────────
def draw_rect_filled(cx, cy, w, h, colour):
    arcade.draw_lrbt_rectangle_filled(cx - w/2, cx + w/2, cy - h/2, cy + h/2, colour)

def draw_rect_outline(cx, cy, w, h, colour, border=2):
    arcade.draw_lrbt_rectangle_outline(cx - w/2, cx + w/2, cy - h/2, cy + h/2, colour, border)

def draw_overlay(alpha):
    arcade.draw_lrbt_rectangle_filled(0, SCREEN_W, 0, SCREEN_H, (0, 0, 10, alpha))

def project(nx, ny, depth):
    scale = ENEMY_MIN_SCALE + (ENEMY_MAX_SCALE - ENEMY_MIN_SCALE) * (depth ** 1.6)
    sx = VP_X + (nx - 0.5) * SCREEN_W * depth
    sy = VP_Y + (ny - 0.5) * SCREEN_H * depth
    return sx, sy, scale

def rects_overlap(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])

 
# ─────────────────────────────────────────────────────────────────────────────
#  Starfield
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
        if self.y < -2:
            self.reset()

    def draw(self):
        arcade.draw_circle_filled(self.x, self.y, self.size, self.colour)


# ─────────────────────────────────────────────────────────────────────────────
#  Vortex rings
# ─────────────────────────────────────────────────────────────────────────────
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
#  Player
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


# ─────────────────────────────────────────────────────────────────────────────
#  Bullet
# ─────────────────────────────────────────────────────────────────────────────
class Bullet:
    BASE_R = 4

    def __init__(self, px, py):
        self.nx    = px / SCREEN_W
        self.ny    = py / SCREEN_H
        self.depth = 1.0
        self.alive = True
        self.sx, self.sy, self.scale = px, py, 1.0

    def update(self):
        self.depth -= BULLET_DEPTH_SPEED
        self.nx += (0.5 - self.nx) * BULLET_DEPTH_SPEED * 1.5
        self.ny += (VP_Y / SCREEN_H - self.ny) * BULLET_DEPTH_SPEED * 1.5
        if self.depth <= 0.0:
            self.alive = False

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
        r = max(1.5, self.BASE_R * scale)
        arcade.draw_circle_filled(sx, sy, r,       C_BULLET)
        arcade.draw_circle_filled(sx, sy, r * 0.5, C_WHITE)

    def rect(self):
        r = max(2, self.BASE_R * self.scale)
        return (self.sx - r, self.sy - r, self.sx + r, self.sy + r)


# ─────────────────────────────────────────────────────────────────────────────
#  Enemy bullet
# ─────────────────────────────────────────────────────────────────────────────
class EnemyBullet:
    BASE_R = 4

    def __init__(self, sx, sy, target_x, target_y, speed=4.5):
        self.sx  = sx
        self.sy  = sy
        dx = target_x - sx;  dy = target_y - sy
        dist = math.hypot(dx, dy) or 1
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed
        self.alive      = True
        self.colour     = (220, 80,  20)
        self.colour_dim = (255, 200, 80)

    def update(self):
        self.sx += self.vx;  self.sy += self.vy
        if self.sx < -20 or self.sx > SCREEN_W+20 or self.sy < -20 or self.sy > SCREEN_H+20:
            self.alive = False

    def draw(self):
        arcade.draw_circle_filled(self.sx, self.sy, self.BASE_R,       self.colour)
        arcade.draw_circle_filled(self.sx, self.sy, self.BASE_R * 0.5, self.colour_dim)

    def rect(self):
        r = self.BASE_R
        return (self.sx - r, self.sy - r, self.sx + r, self.sy + r)


# ─────────────────────────────────────────────────────────────────────────────
#  Enemy — Dalek Saucer
# ─────────────────────────────────────────────────────────────────────────────
class Enemy:
    BASE_W, BASE_H = 44, 20

    def __init__(self, wave=1):
        self.nx    = random.uniform(0.3, 0.7)
        self.ny    = random.uniform(0.4, 0.6)
        self.dnx   = random.uniform(-0.0008, 0.0008)
        self.dny   = random.uniform(-0.0004, 0.0002)
        self.depth = 0.0
        wave_mult  = 1 + (wave - 1) * 0.12
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.8, 1.3) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        base_cd       = max(0.8, 3.5 - (wave-1) * 0.18)
        self.shoot_cd = random.uniform(base_cd * 0.5, base_cd)
        self.wave     = wave
        self.patrolling = False
        self.target_nx = self.nx;  self.target_ny = self.ny;  self.patrol_cd = 0.0
        self.deploy_cd = random.uniform(4.0, 8.0)
        self.deployed  = 0

    def maybe_deploy(self):
        if self.depth < 0.30 or self.deployed >= 2:
            return None
        self.deploy_cd -= 1/60
        if self.deploy_cd <= 0:
            self.deploy_cd = random.uniform(5.0, 9.0)
            self.deployed += 1
            return Dalek(self.wave, spawn_nx=self.nx, spawn_ny=self.ny, spawn_depth=self.depth)
        return None

    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.35 or self.scale < 0.25:
            return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.5, 2.8 - (self.wave-1) * 0.15)
            self.shoot_cd = random.uniform(base_cd*0.7, base_cd) * (1.0 - self.depth*0.45)
            speed = (3.5 + self.depth*3.0) + (self.wave-1)*0.4
            return EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
        return None

    def _new_patrol_target(self, pnx, pny):
        angle  = random.uniform(0, math.pi*2)
        radius = random.uniform(0.12, 0.30)
        self.target_nx = max(0.05, min(0.95, pnx + math.cos(angle)*radius))
        self.target_ny = max(0.05, min(0.95, pny + math.sin(angle)*radius*0.7))
        self.patrol_cd = random.uniform(2.5, 5.0)

    def update(self, pnx=0.5, pny=0.5):
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*2)
            self.ny += self.dny * (1 + self.depth*2)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True;  self.depth = PATROL_DEPTH
                self._new_patrol_target(pnx, pny)
        else:
            self.nx += (self.target_nx - self.nx) * PATROL_STEER
            self.ny += (self.target_ny - self.ny) * PATROL_STEER
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self._new_patrol_target(pnx, pny)

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
        w = self.BASE_W * scale;  h = self.BASE_H * scale
        brightness = min(255, int(255 * (self.depth / 0.15)))
        dome_col = tuple(int(c * brightness/255) for c in C_DALEK_DARK)
        arcade.draw_ellipse_filled(sx, sy + 6*scale, w - 8*scale, 16*scale, dome_col)
        rim_col  = tuple(int(c * brightness/255) for c in C_DALEK_GOLD)
        arcade.draw_ellipse_filled(sx, sy, w, h, rim_col)
        arcade.draw_ellipse_outline(sx, sy + 6*scale, w - 8*scale, 16*scale, rim_col, max(1, int(2*scale)))
        if scale > 0.25:
            dot_col = tuple(int(c * brightness/255) for c in C_DALEK_DARK)
            for i in range(-2, 3):
                arcade.draw_circle_filled(sx + i*9*scale, sy, max(1, 2*scale), dot_col)
        eye_r   = max(1.5, 5*scale)
        eye_col = tuple(int(c * brightness/255) for c in C_RED)
        arcade.draw_circle_filled(sx, sy + 14*scale, eye_r, eye_col)
        if scale > 0.2:
            arcade.draw_circle_filled(sx, sy + 14*scale, eye_r*0.4, (255,100,100))

    def rect(self):
        w = self.BASE_W * self.scale
        h = (self.BASE_H + 20) * self.scale
        return (self.sx - w/2, self.sy - h/2, self.sx + w/2, self.sy + h/2)


# ─────────────────────────────────────────────────────────────────────────────
#  Individual Dalek
# ─────────────────────────────────────────────────────────────────────────────
class Dalek:
    BASE_W, BASE_H = 18, 30

    def __init__(self, wave=1, spawn_nx=None, spawn_ny=None, spawn_depth=None):
        self.nx    = spawn_nx if spawn_nx is not None else random.uniform(0.2, 0.8)
        self.ny    = spawn_ny if spawn_ny is not None else random.uniform(0.3, 0.7)
        self.dnx   = random.uniform(-0.0014, 0.0014)
        self.dny   = random.uniform(-0.0006, 0.0004)
        self.depth = spawn_depth if spawn_depth is not None else 0.0
        wave_mult  = 1 + (wave-1) * 0.10
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.7, 1.1) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        base_cd       = max(0.4, 2.2 - (wave-1)*0.14)
        self.shoot_cd = random.uniform(base_cd*0.4, base_cd)
        self.wave     = wave
        self.gun_angle = random.uniform(0, math.pi*2)
        self.patrolling = False
        self.target_nx = self.nx;  self.target_ny = self.ny;  self.patrol_cd = 0.0

    def _new_patrol_target(self, pnx, pny):
        angle  = random.uniform(0, math.pi*2)
        radius = random.uniform(0.10, 0.25)
        self.target_nx = max(0.05, min(0.95, pnx + math.cos(angle)*radius))
        self.target_ny = max(0.05, min(0.95, pny + math.sin(angle)*radius*0.7))
        self.patrol_cd = random.uniform(1.5, 3.5)

    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.28 or self.scale < 0.20:
            return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.3, 1.8 - (self.wave-1)*0.10)
            self.shoot_cd = random.uniform(base_cd*0.6, base_cd) * (1.0 - self.depth*0.4)
            speed = (4.5 + self.depth*3.5) + (self.wave-1)*0.45
            return EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
        return None

    def update(self, pnx=0.5, pny=0.5):
        self.gun_angle += 0.06
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*2)
            self.ny += self.dny * (1 + self.depth*2)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True;  self.depth = PATROL_DEPTH
                self._new_patrol_target(pnx, pny)
        else:
            steer = PATROL_STEER * 1.4
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self._new_patrol_target(pnx, pny)

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
        brightness = min(255, int(255 * (self.depth / 0.12)))
        def c(col): return tuple(int(x * brightness/255) for x in col)
        w = self.BASE_W * scale;  h = self.BASE_H * scale;  s = scale
        skirt = [(sx-w*0.9, sy-h*0.5),(sx+w*0.9, sy-h*0.5),(sx+w*0.6, sy-h*0.1),(sx-w*0.6, sy-h*0.1)]
        arcade.draw_polygon_filled(skirt, c(C_DALEK_DARK))
        draw_rect_filled(sx, sy+h*0.08, w*1.1, h*0.35, c(C_DALEK_GOLD))
        if scale > 0.18:
            bump_r = max(1.5, 3.0*s)
            for row_y, count in [(sy-h*0.04, 3),(sy+h*0.16, 2)]:
                spacing = w*0.55/max(1,count-1) if count > 1 else 0
                for i in range(count):
                    bx = sx - w*0.275 + i*spacing if count > 1 else sx
                    arcade.draw_circle_filled(bx, row_y, bump_r, c(C_DALEK_DARK))
        draw_rect_filled(sx, sy+h*0.28, w*0.85, h*0.10, c(C_DALEK_DARK))
        arcade.draw_ellipse_filled(sx, sy+h*0.42, w*0.7, h*0.28, c(C_DALEK_GOLD))
        if scale > 0.15:
            arcade.draw_line(sx, sy+h*0.44, sx+w*0.75, sy+h*0.44, c(C_DALEK_DARK), max(1,int(2*s)))
            eye_r = max(1.5, 4*s)
            arcade.draw_circle_filled(sx+w*0.75, sy+h*0.44, eye_r, c(C_RED))
            if scale > 0.25:
                arcade.draw_circle_filled(sx+w*0.75, sy+h*0.44, eye_r*0.4, (255,120,120))
        if scale > 0.15:
            ga = math.sin(self.gun_angle) * 0.18
            gx = sx - w*0.2 + math.cos(ga)*w*0.9
            gy = sy + h*0.20 + math.sin(ga)*w*0.9*0.4
            arcade.draw_line(sx-w*0.2, sy+h*0.20, gx, gy, c(C_DALEK_DARK), max(1,int(2*s)))
            if scale > 0.22:
                arcade.draw_circle_filled(gx, gy, max(1.5, 3*s), c(C_DALEK_GOLD))

    def rect(self):
        w = self.BASE_W * self.scale * 1.8;  h = self.BASE_H * self.scale
        return (self.sx-w/2, self.sy-h/2, self.sx+w/2, self.sy+h/2)


# ─────────────────────────────────────────────────────────────────────────────
#  Cyberman Ship
# ─────────────────────────────────────────────────────────────────────────────
class Cyberman:
    BASE_W, BASE_H = 44, 20

    def __init__(self, wave=1):
        self.nx    = random.uniform(0.44, 0.56)
        self.ny    = random.uniform(0.44, 0.56)
        self.dnx   = random.uniform(-0.0006, 0.0006)
        self.dny   = random.uniform(-0.0003, 0.0003)
        self.depth = 0.0
        wave_mult  = 1 + (wave-1) * 0.09
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.6, 0.95) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        base_cd       = max(0.9, 3.8 - (wave-1)*0.16)
        self.shoot_cd = random.uniform(base_cd*0.6, base_cd)
        self.wave     = wave
        self.rot      = random.uniform(0, math.pi*2)
        self.rot_vel  = random.choice([-1,1]) * random.uniform(0.008, 0.022)
        self.patrolling = False
        self.target_nx = self.nx;  self.target_ny = self.ny;  self.patrol_cd = 0.0
        self.deploy_cd = random.uniform(2.0, 4.0)
        self.deployed  = 0

    def maybe_deploy(self):
        if self.depth < 0.25 or self.deployed >= 3:
            return None
        self.deploy_cd -= 1/60
        if self.deploy_cd <= 0:
            self.deploy_cd = random.uniform(2.5, 5.0)
            self.deployed += 1
            return CybermanUnit(self.wave, spawn_nx=self.nx, spawn_ny=self.ny, spawn_depth=self.depth)
        return None

    def _new_patrol_target(self, pnx, pny):
        angle  = random.uniform(0, math.pi*2)
        radius = random.uniform(0.18, 0.35)
        self.target_nx = max(0.05, min(0.95, pnx + math.cos(angle)*radius))
        self.target_ny = max(0.05, min(0.95, pny + math.sin(angle)*radius*0.7))
        self.patrol_cd = random.uniform(3.0, 6.0)

    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.25 or self.scale < 0.18:
            return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.6, 3.2 - (self.wave-1)*0.14)
            self.shoot_cd = random.uniform(base_cd*0.7, base_cd) * (1.0 - self.depth*0.35)
            speed = (5.5 + self.depth*4.0) + (self.wave-1)*0.5
            b = EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
            b.colour = C_CYBER_GLOW;  b.colour_dim = (40,120,140)
            return b
        return None

    def update(self, pnx=0.5, pny=0.5):
        self.rot += self.rot_vel
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*1.5)
            self.ny += self.dny * (1 + self.depth*1.5)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True;  self.depth = PATROL_DEPTH
                self._new_patrol_target(pnx, pny)
        else:
            steer = PATROL_STEER * 0.7
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self._new_patrol_target(pnx, pny)

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
        brightness = min(255, int(255 * (self.depth / 0.12)))
        def c(col): return tuple(int(x * brightness/255) for x in col)
        r = self.rot;  s = scale
        hw = self.BASE_W * s * 0.5;  hh = self.BASE_H * s * 0.5
        def rv(px, py):
            cr, sr = math.cos(r), math.sin(r)
            return (sx + px*cr - py*sr, sy + px*sr + py*cr)
        hex_pts = [rv(math.cos(math.pi/2 + i*math.pi/3)*hw*1.1,
                      math.sin(math.pi/2 + i*math.pi/3)*hh*1.1) for i in range(6)]
        arcade.draw_polygon_filled(hex_pts, c(C_CYBER_DARK))
        arcade.draw_polygon_outline(hex_pts, c(C_CYBER_SILVER), max(1, int(2*s)))
        diamond = [rv(0,hh*0.55),rv(hw*0.55,0),rv(0,-hh*0.55),rv(-hw*0.55,0)]
        arcade.draw_polygon_filled(diamond, c(C_CYBER_SILVER))
        if scale > 0.12:
            eye_r = max(1.5, 5*s)
            arcade.draw_circle_filled(sx, sy, eye_r, c(C_CYBER_GLOW))
            if scale > 0.22:
                arcade.draw_circle_filled(sx, sy, eye_r*0.45, (200,255,255))
        if scale > 0.20:
            for i in [0,1,3,4]:
                pt = hex_pts[i]
                arcade.draw_line(sx, sy, pt[0], pt[1], c(C_CYBER_SILVER), max(1, int(s*1.5)))

    def rect(self):
        r = self.BASE_W * self.scale * 0.9
        return (self.sx-r, self.sy-r, self.sx+r, self.sy+r)


# ─────────────────────────────────────────────────────────────────────────────
#  Individual CybermanUnit
# ─────────────────────────────────────────────────────────────────────────────
class CybermanUnit:
    BASE_W, BASE_H = 20, 32

    def __init__(self, wave=1, spawn_nx=None, spawn_ny=None, spawn_depth=None):
        self.nx    = spawn_nx if spawn_nx is not None else random.uniform(0.2, 0.8)
        self.ny    = spawn_ny if spawn_ny is not None else random.uniform(0.3, 0.7)
        self.dnx   = random.uniform(-0.0012, 0.0012)
        self.dny   = random.uniform(-0.0005, 0.0003)
        self.depth = spawn_depth if spawn_depth is not None else 0.0
        wave_mult  = 1 + (wave-1) * 0.08
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.8, 1.2) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        base_cd       = max(0.8, 2.5 - (wave-1)*0.12)
        self.shoot_cd = random.uniform(base_cd*0.8, base_cd)
        self.wave     = wave
        self.patrolling = False
        self.target_nx = self.nx;  self.target_ny = self.ny;  self.patrol_cd = 0.0

    def _new_patrol_target(self, pnx, pny, dalek_targets=None):
        if dalek_targets and random.random() < 0.12:
            t = random.choice(dalek_targets)
            self.target_nx = t.nx;  self.target_ny = t.ny
        else:
            angle  = random.uniform(0, math.pi*2)
            radius = random.uniform(0.12, 0.28)
            self.target_nx = max(0.05, min(0.95, pnx + math.cos(angle)*radius))
            self.target_ny = max(0.05, min(0.95, pny + math.sin(angle)*radius*0.7))
        self.patrol_cd = random.uniform(2.0, 4.0)

    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.25 or self.scale < 0.18:
            return None
        self.shoot_cd -= 1/60
        if self.shoot_cd <= 0:
            base_cd = max(0.6, 2.0 - (self.wave-1)*0.10)
            self.shoot_cd = random.uniform(base_cd*0.8, base_cd) * (1.0 - self.depth*0.3)
            speed = (6.0 + self.depth*4.5) + (self.wave-1)*0.6
            b = EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
            b.colour = C_CYBER_GLOW;  b.colour_dim = (30,100,120)
            return b
        return None

    def update(self, pnx=0.5, pny=0.5, dalek_targets=None):
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth*1.8)
            self.ny += self.dny * (1 + self.depth*1.8)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True;  self.depth = PATROL_DEPTH
                self._new_patrol_target(pnx, pny, dalek_targets)
        else:
            steer = PATROL_STEER * 1.2
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self._new_patrol_target(pnx, pny, dalek_targets)

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
        brightness = min(255, int(255 * (self.depth / 0.12)))
        def c(col): return tuple(int(x * brightness/255) for x in col)
        w = self.BASE_W * scale;  h = self.BASE_H * scale;  s = scale
        body = [(sx-w*0.4,sy-h*0.5),(sx+w*0.4,sy-h*0.5),(sx+w*0.3,sy+h*0.2),(sx-w*0.3,sy+h*0.2)]
        arcade.draw_polygon_filled(body, c(C_CYBER_SILVER))
        arcade.draw_polygon_outline(body, c(C_CYBER_DARK), max(1,int(2*s)))
        draw_rect_filled(sx, sy+h*0.05, w*0.6, h*0.25, c(C_CYBER_DARK))
        draw_rect_filled(sx, sy+h*0.35, w*0.5, h*0.20, c(C_CYBER_SILVER))
        if scale > 0.15:
            eye_r = max(1.5, 3*s)
            arcade.draw_circle_filled(sx-w*0.15, sy+h*0.35, eye_r, c(C_CYBER_GLOW))
            arcade.draw_circle_filled(sx+w*0.15, sy+h*0.35, eye_r, c(C_CYBER_GLOW))
        if scale > 0.18:
            ay = sy + h*0.1
            arcade.draw_line(sx-w*0.45, ay, sx-w*0.65, ay-h*0.1, c(C_CYBER_DARK), max(1,int(2*s)))
            arcade.draw_line(sx+w*0.45, ay, sx+w*0.65, ay-h*0.1, c(C_CYBER_DARK), max(1,int(2*s)))

    def rect(self):
        w = self.BASE_W * self.scale * 1.2;  h = self.BASE_H * self.scale
        return (self.sx-w/2, self.sy-h/2, self.sx+w/2, self.sy+h/2)


# ─────────────────────────────────────────────────────────────────────────────
#  Pickup
# ─────────────────────────────────────────────────────────────────────────────
class Pickup:
    R = 9
    COLOURS = {"life": C_DROP_LIFE, "pierce": C_DROP_PIERCE, "fire": C_DROP_FIRE}
    LABELS  = {"life": "+", "pierce": "P", "fire": "F"}

    def __init__(self, sx, sy, kind):
        self.sx    = float(sx);  self.sy = float(sy)
        self.kind  = kind
        self.alive = True
        self.age   = 0
        self.vx    = random.uniform(-1.2, 1.2)
        self.vy    = random.uniform(-1.2, 1.2)

    def update(self, player_x, player_y):
        self.age += 1
        if self.age > 30:
            dx = player_x - self.sx;  dy = player_y - self.sy
            dist = math.hypot(dx, dy) or 1
            speed = 1.2 + min(3.0, self.age * 0.01)
            self.vx += (dx/dist) * 0.18;  self.vy += (dy/dist) * 0.18
            spd = math.hypot(self.vx, self.vy)
            if spd > speed:
                self.vx = self.vx/spd*speed;  self.vy = self.vy/spd*speed
        self.sx += self.vx;  self.sy += self.vy
        if self.age > 420:
            self.alive = False

    def draw(self):
        col   = self.COLOURS[self.kind]
        pulse = 0.7 + 0.3 * math.sin(self.age * 0.18)
        r     = int(self.R * pulse)
        arcade.draw_circle_filled(self.sx, self.sy, r+3, (255,255,255,60))
        arcade.draw_circle_filled(self.sx, self.sy, r, col)
        arcade.draw_text(self.LABELS[self.kind], self.sx, self.sy-5,
                         C_WHITE, 10, anchor_x="center", font_name="Courier New", bold=True)

    def rect(self):
        return (self.sx-self.R, self.sy-self.R, self.sx+self.R, self.sy+self.R)


# ─────────────────────────────────────────────────────────────────────────────
#  Weeping Angel
# ─────────────────────────────────────────────────────────────────────────────
class WeepingAngel:
    BASE_W, BASE_H = 22, 36

    def __init__(self, wave=1):
        angle   = random.uniform(0, math.pi*2)
        self.nx = max(0.05, min(0.95, 0.5 + math.cos(angle)*random.uniform(0.28,0.38)))
        self.ny = max(0.05, min(0.95, 0.5 + math.sin(angle)*random.uniform(0.20,0.28)))
        self.depth = random.uniform(0.25, 0.45)
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.5, 0.8)
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        self.wave   = wave
        self.frozen = False
        self.patrolling = False
        self.target_nx = self.nx;  self.target_ny = self.ny;  self.patrol_cd = 0.0

    def is_watched(self, pnx, pny, darkness_level=0.0):
        if darkness_level >= 1.0:
            return False
        same_quad    = (int(pnx>0.5), int(pny>0.5)) == (int(self.nx>0.5), int(self.ny>0.5))
        angel_closer = math.hypot(self.nx-0.5, self.ny-0.5) < math.hypot(pnx-0.5, pny-0.5)
        return same_quad or angel_closer

    def _new_patrol_target(self, pnx, pny):
        angle  = random.uniform(0, math.pi*2)
        radius = random.uniform(0.08, 0.22)
        self.target_nx = max(0.05, min(0.95, pnx + math.cos(angle)*radius))
        self.target_ny = max(0.05, min(0.95, pny + math.sin(angle)*radius*0.7))
        self.patrol_cd = random.uniform(1.0, 2.5)

    def maybe_shoot(self, target_x, target_y):
        return None

    def update(self, pnx=0.5, pny=0.5, darkness_level=0.0, is_blinking=False):
        self.frozen = self.is_watched(pnx, pny, darkness_level)
        if self.frozen:
            return
        steer_mult = 3.0 if is_blinking else 1.0
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += (pnx - self.nx) * 0.004 * steer_mult
            self.ny += (pny - self.ny) * 0.004 * steer_mult
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True;  self.depth = PATROL_DEPTH
                self._new_patrol_target(pnx, pny)
        else:
            steer = PATROL_STEER * 2.2 * steer_mult
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1/60
            if self.patrol_cd <= 0:
                self._new_patrol_target(pnx, pny)

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
        brightness = min(255, int(255 * (self.depth / 0.12)))
        if not self.frozen:
            brightness = min(255, brightness + random.randint(-15,15))
        def c(col): return tuple(int(x * brightness/255) for x in col)
        w = self.BASE_W * scale;  h = self.BASE_H * scale;  s = scale
        body = [(sx-w*0.55,sy-h*0.5),(sx+w*0.55,sy-h*0.5),(sx+w*0.35,sy+h*0.3),(sx-w*0.35,sy+h*0.3)]
        arcade.draw_polygon_filled(body, c(C_ANGEL_STONE))
        arcade.draw_polygon_outline(body, c(C_ANGEL_DARK), max(1,int(s*1.5)))
        if scale > 0.15:
            lw = [(sx-w*0.35,sy+h*0.2),(sx-w*1.1,sy+h*0.4),(sx-w*0.9,sy-h*0.1),(sx-w*0.3,sy+h*0.0)]
            rw = [(sx+w*0.35,sy+h*0.2),(sx+w*1.1,sy+h*0.4),(sx+w*0.9,sy-h*0.1),(sx+w*0.3,sy+h*0.0)]
            arcade.draw_polygon_filled(lw, c(C_ANGEL_DARK));  arcade.draw_polygon_outline(lw, c(C_ANGEL_STONE), max(1,int(s)))
            arcade.draw_polygon_filled(rw, c(C_ANGEL_DARK));  arcade.draw_polygon_outline(rw, c(C_ANGEL_STONE), max(1,int(s)))
        if scale > 0.10:
            arcade.draw_ellipse_filled(sx, sy+h*0.42, w*0.55, h*0.22, c(C_ANGEL_STONE))
            if self.frozen and scale > 0.25:
                arcade.draw_ellipse_filled(sx-w*0.12, sy+h*0.44, w*0.16, h*0.10, c(C_ANGEL_DARK))
                arcade.draw_ellipse_filled(sx+w*0.12, sy+h*0.44, w*0.16, h*0.10, c(C_ANGEL_DARK))
            elif not self.frozen and scale > 0.22:
                ec = (min(255, brightness+40), 20, 20)
                arcade.draw_circle_filled(sx-w*0.12, sy+h*0.44, max(1.5,3*s), ec)
                arcade.draw_circle_filled(sx+w*0.12, sy+h*0.44, max(1.5,3*s), ec)

    def rect(self):
        w = self.BASE_W * self.scale * 1.1;  h = self.BASE_H * self.scale
        return (self.sx-w/2, self.sy-h/2, self.sx+w/2, self.sy+h/2)


# ─────────────────────────────────────────────────────────────────────────────
#  Particles
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
#  HUD helpers
# ─────────────────────────────────────────────────────────────────────────────
def draw_mini_tardis(cx, cy, scale=1.0):
    w = 28*scale;  h = 38*scale
    draw_rect_filled(cx, cy, w, h, C_TARDIS_BLUE)
    draw_rect_outline(cx, cy, w, h, C_TARDIS_LIGHT, max(1, int(2*scale)))
    draw_rect_filled(cx-6*scale, cy+6*scale, 7*scale, 9*scale, C_TARDIS_LIGHT)
    draw_rect_filled(cx+6*scale, cy+6*scale, 7*scale, 9*scale, C_TARDIS_LIGHT)
    arcade.draw_circle_filled(cx, cy+h/2+8*scale, 4*scale, (220,240,255))

def _faction_banner(faction):
    return {
        "daleks_infantry":   ("DALEK SQUADRON",     C_DALEK_GOLD),
        "daleks_ships":      ("DALEK FLEET",        C_DALEK_GOLD),
        "cybermen_infantry": ("CYBERMAN SECTOR",    C_CYBER_GLOW),
        "cybermen_ships":    ("CYBERMAN INVASION",  C_CYBER_GLOW),
        "angels":            ("ANGEL INCURSION",    C_ANGEL_GLOW),
        "mixed":             ("ALL FORCES",         C_RED),
    }.get(faction, ("", C_WHITE))


# ─────────────────────────────────────────────────────────────────────────────
#  Game Window
# ─────────────────────────────────────────────────────────────────────────────
class GameWindow(arcade.Window):

    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, resizable=False)
        self.state = "title"
        self._init_scene()

    def _init_scene(self):
        self.stars           = [Star() for _ in range(160)]
        self.vortex          = [VortexRing() for _ in range(30)]
        self.player          = Player()
        self.bullets         = []
        self.enemies         = []        # Dalek saucers
        self.daleks          = []        # individual Daleks
        self.cybermen        = []        # Cyberman ships
        self.cyberman_units  = []        # individual Cybermen
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
        self.angel_survival_elapsed = 0.0 # Time tracking for angel round
        self.angel_survival_target  = 30.0 # Total survival time required (seconds)
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

    # ── Input ─────────────────────────────────────────────────────────────────

    def on_key_press(self, key, mod):
        self.keys_held.add(key)
        if self.state == "title" and key in (arcade.key.SPACE, arcade.key.ENTER):
            self.state = "playing"
        if self.state == "game_over" and key == arcade.key.R:
            self._init_scene();  self.state = "playing"

    def on_key_release(self, key, mod):
        self.keys_held.discard(key)

    # ── Update ────────────────────────────────────────────────────────────────

    def on_update(self, dt):
        self.elapsed += dt
        for s in self.stars:   s.update()
        for v in self.vortex:  v.update()
        if self.state != "playing":
            return

        faction = faction_for_wave(self.wave)

        # Show banner when faction changes
        if faction != self._last_faction:
            self._last_faction = faction
            label, col = _faction_banner(faction)
            self.flash(f"EPISODE {self.wave}  —  {label}", 3.0, col)

        # Movement
        dx = dy = 0
        if arcade.key.LEFT  in self.keys_held or arcade.key.A in self.keys_held: dx -= PLAYER_SPEED
        if arcade.key.RIGHT in self.keys_held or arcade.key.D in self.keys_held: dx += PLAYER_SPEED
        if arcade.key.UP    in self.keys_held or arcade.key.W in self.keys_held: dy += PLAYER_SPEED
        if arcade.key.DOWN  in self.keys_held or arcade.key.S in self.keys_held: dy -= PLAYER_SPEED
        self.player.dx, self.player.dy = dx, dy
        self.player.update()

        # Blinking mechanic (angel waves)
        angel_wave = faction in ("angels", "mixed")
        if angel_wave:
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

        # Shoot
        self.shoot_cd -= dt
        if arcade.key.SPACE in self.keys_held and self.shoot_cd <= 0:
            self.bullets.append(Bullet(self.player.x, self.player.y))
            self.shoot_cd = max(0.06, 0.18 - self.stat_fire * 0.02)

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        # ── Spawning — faction-gated ───────────────────────────────────────────

        # Dalek Handling
        self.spawn_timer -= dt
        if faction == "daleks_infantry":
            if self.spawn_timer <= 0 and len(self.daleks) < MAX_ENEMIES:
                self.daleks.append(Dalek(self.wave))
                self.spawn_timer = max(0.6, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave-1)))
        elif faction in ("daleks_ships", "mixed"):
            if self.spawn_timer <= 0 and len(self.enemies) < MAX_ENEMIES:
                self.enemies.append(Enemy(self.wave))
                self.spawn_timer = max(0.5, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave-1)))
            
            # Saucers deploy individual Daleks
            for e in self.enemies:
                d = e.maybe_deploy()
                if d and len(self.daleks) < MAX_ENEMIES:
                    self.daleks.append(d)
        else:
            if self.spawn_timer <= 0:
                self.spawn_timer = 2.0

        # Cyberman Handling
        self.cyber_timer -= dt
        if faction == "cybermen_infantry":
            if self.cyber_timer <= 0 and len(self.cyberman_units) < MAX_ENEMIES:
                self.cyberman_units.append(CybermanUnit(self.wave))
                self.cyber_timer = max(0.6, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave-1)))
        elif faction in ("cybermen_ships", "mixed"):
            if self.cyber_timer <= 0 and len(self.cybermen) < MAX_ENEMIES:
                self.cybermen.append(Cyberman(self.wave))
                self.cyber_timer = max(1.2, 5.0 - (self.wave-4)*0.3 if self.wave > 4 else 5.0)
            
            # Cyber ships deploy individual Cybermen
            for cy in self.cybermen:
                cu = cy.maybe_deploy()
                if cu and len(self.cyberman_units) < MAX_ENEMIES:
                    self.cyberman_units.append(cu)
        else:
            if self.cyber_timer <= 0:
                self.cyber_timer = 2.0

        # Weeping Angels Handling
        self.angel_timer -= dt
        if faction in ("angels", "mixed"):
            max_angels = 4 if faction == "angels" else 2 # More intense challenge for solo level
            if self.angel_timer <= 0 and len(self.angels) < max_angels:
                self.angels.append(WeepingAngel(self.wave))
                self.angel_timer = max(4.0, 12.0 - (self.wave-7)*1.5 if self.wave > 7 else 12.0)
        else:
            if self.angel_timer <= 0:
                self.angel_timer = 5.0

        # Clear active entities outside their structural wave phases
        if faction in ("cybermen_infantry", "cybermen_ships"):
            self.enemies = [];  self.daleks = []
        elif faction == "angels":
            self.enemies = [];  self.daleks = [];  self.cybermen = [];  self.cyberman_units = []

        pnx = self.player.x / SCREEN_W
        pny = self.player.y / SCREEN_H

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

        # ── Shooting ──────────────────────────────────────────────────────────

        for e in self.enemies:
            shot = e.maybe_shoot(self.player.x, self.player.y)
            if shot: self.enemy_bullets.append(shot)

        for d in self.daleks:
            cyber_targets = [cu for cu in self.cyberman_units if cu.alive] + \
                            [cy for cy in self.cybermen if cy.alive]
            if cyber_targets and random.random() < 0.15:
                t = random.choice(cyber_targets)
                shot = d.maybe_shoot(t.sx, t.sy)
            else:
                shot = d.maybe_shoot(self.player.x, self.player.y)
            if shot: self.enemy_bullets.append(shot)

        for cy in self.cybermen:
            shot = cy.maybe_shoot(self.player.x, self.player.y)
            if shot: self.enemy_bullets.append(shot)

        for cu in self.cyberman_units:
            dalek_targets2 = [d for d in self.daleks if d.alive] + \
                             [e for e in self.enemies if e.alive]
            if dalek_targets2 and random.random() < 0.12:
                t = random.choice(dalek_targets2)
                shot = cu.maybe_shoot(t.sx, t.sy)
            else:
                shot = cu.maybe_shoot(self.player.x, self.player.y)
            if shot: self.enemy_bullets.append(shot)

        for eb in self.enemy_bullets: eb.update()
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

        # ── Bullet collisions ─────────────────────────────────────────────────

        def hit(b, target, score_val, colours, drop_kind=None, drop_chance=0.0):
            pierce = random.random() < self.stat_pierce * 0.10
            if not pierce: b.alive = False
            target.alive = False
            self.score += score_val * self.wave
            self.wave_kills += 1
            self.particles += explode(target.sx, target.sy, colours)
            if drop_kind and random.random() < drop_chance:
                self.pickups.append(Pickup(target.sx, target.sy, drop_kind))

        for b in self.bullets[:]:
            for e in self.enemies[:]:
                if b.alive and e.alive and rects_overlap(b.rect(), e.rect()):
                    hit(b, e, 100, [C_DALEK_GOLD,C_DALEK_DARK,(255,200,50),C_WHITE], "life", 0.09)
                    break
        for b in self.bullets[:]:
            for d in self.daleks[:]:
                if b.alive and d.alive and rects_overlap(b.rect(), d.rect()):
                    hit(b, d, 150, [C_DALEK_GOLD,C_RED,(255,160,20),C_WHITE], "pierce", 0.11)
                    break
        for b in self.bullets[:]:
            for cy in self.cybermen[:]:
                if b.alive and cy.alive and rects_overlap(b.rect(), cy.rect()):
                    hit(b, cy, 200, [C_CYBER_SILVER,C_CYBER_GLOW,C_CYBER_DARK,C_WHITE], "fire", 0.15)
                    break
        for b in self.bullets[:]:
            for cu in self.cyberman_units[:]:
                if b.alive and cu.alive and rects_overlap(b.rect(), cu.rect()):
                    hit(b, cu, 180, [C_CYBER_SILVER,C_CYBER_GLOW,C_CYBER_DARK,C_WHITE], "fire", 0.12)
                    break

        for b in self.bullets[:]:
            for ang in self.angels[:]:
                if b.alive and ang.alive and rects_overlap(b.rect(), ang.rect()):
                    b.alive = False
                    self.score += 50 * self.wave
                    self.particles += explode(ang.sx, ang.sy, [C_ANGEL_STONE,C_ANGEL_GLOW,C_WHITE], n=12)
                    break

        for eb in self.enemy_bullets[:]:
            for d in self.daleks[:]:
                if eb.colour == C_CYBER_GLOW and eb.alive and d.alive and rects_overlap(eb.rect(), d.rect()):
                    eb.alive = False;  d.alive = False
                    self.particles += explode(d.sx, d.sy, [C_DALEK_GOLD,C_RED,C_WHITE], n=15)
                    break
            for cu in self.cyberman_units[:]:
                if eb.colour != C_CYBER_GLOW and eb.alive and cu.alive and rects_overlap(eb.rect(), cu.rect()):
                    eb.alive = False;  cu.alive = False
                    self.particles += explode(cu.sx, cu.sy, [C_CYBER_SILVER,C_CYBER_GLOW,C_WHITE], n=15)
                    break

        # ── Player collisions ─────────────────────────────────────────────────

        def hurt_player(killer=None):
            if killer: killer.alive = False
            self.particles += explode(self.player.x, self.player.y,
                                      [C_TARDIS_BLUE,C_TARDIS_LIGHT,C_WHITE], n=40)
            self.lives -= 1
            if self.lives <= 0:
                self.state = "game_over"
            else:
                self.player.invuln = 75
                self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)

        if self.player.invuln == 0:
            pr = self.player.rect()
            hit_done = False
            for group in [self.enemies, self.daleks, self.cybermen, self.cyberman_units]:
                if hit_done: break
                for obj in group[:]:
                    if rects_overlap(pr, obj.rect()):
                        hurt_player(obj);  hit_done = True;  break
            if not hit_done:
                for eb in self.enemy_bullets[:]:
                    if rects_overlap(pr, eb.rect()):
                        eb.alive = False;  hurt_player();  break

        # Angel touch — time vortex jump
        if self.player.invuln == 0:
            pr = self.player.rect()
            for ang in self.angels[:]:
                if not ang.frozen and rects_overlap(pr, ang.rect()):
                    ang.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                                              [C_ANGEL_STONE,C_ANGEL_GLOW,C_WHITE], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 75
                        self.wave = random.randint(1, 200)
                        self.wave_kills  = 0
                        self.wave_target = 8 + self.wave * 2
                        self.angel_survival_elapsed = 0.0
                        self.enemies = [];  self.daleks = []
                        self.cybermen = [];  self.cyberman_units = [];  self.angels = []
                        self._last_faction = ""
                        self.flash(f"TIME VORTEX JUMP! EPISODE {self.wave}", 3.0, C_ANGEL_GLOW)
                    break

        # ── Pickup collection ─────────────────────────────────────────────────

        pr = self.player.rect()
        for pk in self.pickups[:]:
            pk.update(self.player.x, self.player.y)
            if rects_overlap(pr, pk.rect()):
                pk.alive = False
                if pk.kind == "life":
                    self.lives += 1;  self.flash("+1 REGENERATION", 1.5, C_DROP_LIFE)
                elif pk.kind == "pierce":
                    self.stat_pierce += 1
                    self.flash(f"PIERCE UPGRADED  x{self.stat_pierce}", 1.5, C_DROP_PIERCE)
                elif pk.kind == "fire":
                    self.stat_fire += 1
                    self.flash(f"FIRE RATE UPGRADED  +{self.stat_fire}", 1.5, C_DROP_FIRE)
        self.pickups = [pk for pk in self.pickups if pk.alive]

        # ── Wave advance ──────────────────────────────────────────────────────

        # Progress tracking conditional branches split by combat target thresholds vs time loops
        should_advance = False
        if faction == "angels":
            self.angel_survival_elapsed += dt
            if self.angel_survival_elapsed >= self.angel_survival_target:
                should_advance = True
                self.angel_survival_elapsed = 0.0
        else:
            if self.wave_kills >= self.wave_target:
                should_advance = True

        if should_advance:
            old_faction = faction_for_wave(self.wave)
            self.wave       += 1
            self.wave_kills  = 0
            self.wave_target = 8 + self.wave * 2
            self.condition_red = True;  self.cond_timer = 6.0
            new_faction = faction_for_wave(self.wave)
            if new_faction != old_faction:
                label, col = _faction_banner(new_faction)
                self.flash(f"EPISODE {self.wave}  —  {label}", 3.0, col)
                self._last_faction = new_faction
            else:
                self.flash(f"EPISODE {self.wave}  —  CONDITION RED", 2.5, C_RED)

        if self.condition_red:
            self.cond_timer -= dt
            if self.cond_timer <= 0: self.condition_red = False

        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.alive]
        if self.flash_timer > 0: self.flash_timer -= dt

    # ── Draw ──────────────────────────────────────────────────────────────────

    def on_draw(self):
        self.clear((8, 4, 30))
        for v in self.vortex: v.draw()
        for s in self.stars:  s.draw()

        if self.state == "title":
            self._draw_title();  return

        for p in self.particles: p.draw()
        for pk in self.pickups:  pk.draw()
        for b in self.bullets:   b.draw()
        for eb in self.enemy_bullets: eb.draw()
        all_enemies = sorted(self.enemies + self.daleks + self.cybermen +
                             self.cyberman_units + self.angels, key=lambda e: e.depth)
        for e in all_enemies: e.draw()
        self.player.draw()

        # Darkness veil
        if self.darkness_level > 0:
            draw_overlay(int(self.darkness_level * 210))

        # HUD Text Formatting Cleaners
        faction = faction_for_wave(self.wave)
        clean_fac_name = {
            "daleks_infantry": "DALEKS",
            "daleks_ships": "DALEK FLEET",
            "cybermen_infantry": "CYBERMEN",
            "cybermen_ships": "CYBER INVASION",
            "angels": "WEEPING ANGELS",
            "mixed": "MIXED ERA"
        }.get(faction, faction.upper())

        arcade.draw_text(f"SCORE  {self.score:06d}", 14, SCREEN_H-28,
                         C_TEXT_GOLD, 16, font_name="Courier New", bold=True)
        
        arcade.draw_text(f"EP {self.wave}  [{clean_fac_name}]",
                         SCREEN_W//2, SCREEN_H-28, C_TEXT_BLUE, 14,
                         anchor_x="center", font_name="Courier New", bold=True)
        
        # Chronometer display for the Angel timed survival stage
        if faction == "angels":
            time_left = max(0.0, self.angel_survival_target - self.angel_survival_elapsed)
            arcade.draw_text(f"TIME REMAINING: {time_left:.1f}s",
                             SCREEN_W//2, SCREEN_H-52, C_ANGEL_GLOW, 13,
                             anchor_x="center", font_name="Courier New", bold=True)

        for i in range(min(self.lives, 13)):
            lx = SCREEN_W - 20 - i * 22
            draw_rect_filled(lx, SCREEN_H-20, 14, 18, C_TARDIS_BLUE)
            draw_rect_outline(lx, SCREEN_H-20, 14, 18, C_TARDIS_LIGHT, 1)
        if self.stat_pierce > 0:
            arcade.draw_text(f"PIERCE x{self.stat_pierce}", 14, 14,
                             C_DROP_PIERCE, 13, font_name="Courier New", bold=True)
        if self.stat_fire > 0:
            arcade.draw_text(f"FIRE +{self.stat_fire}", 14, 30,
                             C_DROP_FIRE, 13, font_name="Courier New", bold=True)
        
        # Blink meter (angel waves)
        if faction in ("angels", "mixed") and self.darkness_level > 0:
            bar_w = 120;  filled = int(bar_w * (1.0 - self.darkness_level))
            draw_rect_filled(SCREEN_W//2, 18, bar_w, 10, (40,40,40))
            if filled > 0:
                draw_rect_filled(SCREEN_W//2 - (bar_w-filled)//2, 18, filled, 10, C_ANGEL_GLOW)
            arcade.draw_text("BLINK [B]", SCREEN_W//2, 30, C_ANGEL_GLOW, 11,
                             anchor_x="center", font_name="Courier New")

        if self.flash_timer > 0:
            arcade.draw_text(self.flash_msg, SCREEN_W//2, SCREEN_H//2+30,
                             self._flash_colour, 24, anchor_x="center", anchor_y="center",
                             font_name="Courier New", bold=True)
        if self.condition_red:
            arcade.draw_text("!! CONDITION RED !!", SCREEN_W//2, SCREEN_H//2-20,
                             C_RED, 20, anchor_x="center", font_name="Courier New", bold=True)
        if self.state == "game_over":
            self._draw_game_over()

    def _draw_title(self):
        draw_overlay(170)
        draw_mini_tardis(SCREEN_W//2, SCREEN_H//2+220, 2.0)
        arcade.draw_text("TARDIS  VOID", SCREEN_W//2, SCREEN_H//2+130,
                         C_TARDIS_LIGHT, 52, anchor_x="center", font_name="Courier New", bold=True)
        arcade.draw_text("A  D O C T O R  W H O  S P A C E  S H O O T E R",
                         SCREEN_W//2, SCREEN_H//2+80, C_TEXT_GOLD, 14,
                         anchor_x="center", font_name="Courier New")
        controls = [
            ("ARROW KEYS / WASD  —  Move",         0),
            ("SPACE              —  Fire",          28),
            ("B                  —  Blink (EP 7)",  56),
            ("Daleks (EP 1-3)  •  Cybermen (EP 4-6)  •  Angels (EP 7)  •  All (EP 8+)", 84),
        ]
        for text, offset in controls:
            arcade.draw_text(text, SCREEN_W//2, SCREEN_H//2-10-offset,
                             C_TEXT_BLUE, 13, anchor_x="center", font_name="Courier New")
        if int(self.elapsed*2) % 2 == 0:
            arcade.draw_text("PRESS  SPACE  TO  BEGIN", SCREEN_W//2, SCREEN_H//2-150,
                             C_TEXT_GOLD, 20, anchor_x="center", font_name="Courier New", bold=True)

    def _draw_game_over(self):
        draw_overlay(200)
        arcade.draw_text("EXTERMINATED", SCREEN_W//2, SCREEN_H//2+80,
                         C_RED, 54, anchor_x="center", font_name="Courier New", bold=True)
        arcade.draw_text(f"FINAL SCORE:  {self.score:06d}",
                         SCREEN_W//2, SCREEN_H//2+10, C_TEXT_GOLD, 24,
                         anchor_x="center", font_name="Courier New")
        arcade.draw_text(f"REACHED EPISODE:  {self.wave}",
                         SCREEN_W//2, SCREEN_H//2-30, C_TEXT_BLUE, 18,
                         anchor_x="center", font_name="Courier New")
        arcade.draw_text("All regenerations exhausted.",
                         SCREEN_W//2, SCREEN_H//2-65, (160,140,200), 14,
                         anchor_x="center", font_name="Courier New")
        if int(self.elapsed*2) % 2 == 0:
            arcade.draw_text("PRESS  R  TO  REGENERATE", SCREEN_W//2, SCREEN_H//2-110,
                             C_TEXT_GOLD, 18, anchor_x="center", font_name="Courier New", bold=True)

    def flash(self, msg, duration, colour):
        self.flash_msg = msg;  self.flash_timer = duration;  self._flash_colour = colour


def main():
    GameWindow()
    arcade.run()

if __name__ == "__main__":
    main()