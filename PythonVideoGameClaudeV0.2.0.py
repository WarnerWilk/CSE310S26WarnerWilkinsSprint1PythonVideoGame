"""
TARDIS VOID — A Doctor Who Space Shooter
Bare-bones prototype: blocks, dots, and the Time Vortex.

Controls:
    Arrow keys / WASD  — Move the TARDIS
    Space              — Fire
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
VP_X = SCREEN_W / 2          # vanishing point X (centre)
VP_Y = SCREEN_H / 2          # vanishing point Y — matches vortex centre
ENEMY_DEPTH_SPEED = 0.004     # how fast depth grows per frame (~250 frames to arrive)
ENEMY_MIN_SCALE   = 0.04      # size at vanishing point
ENEMY_MAX_SCALE   = 1.0       # size when depth == 1 (at player plane)
BULLET_DEPTH_SPEED = 0.06     # bullets travel "into" the screen fast

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


# ── Draw helpers ─────────────────────────────────────────────────────────────

def draw_rect_filled(cx, cy, w, h, colour):
    arcade.draw_lrbt_rectangle_filled(
        cx - w / 2, cx + w / 2,
        cy - h / 2, cy + h / 2,
        colour
    )

def draw_rect_outline(cx, cy, w, h, colour, border=2):
    arcade.draw_lrbt_rectangle_outline(
        cx - w / 2, cx + w / 2,
        cy - h / 2, cy + h / 2,
        colour, border
    )

def draw_overlay(alpha):
    arcade.draw_lrbt_rectangle_filled(0, SCREEN_W, 0, SCREEN_H, (0, 0, 10, alpha))

def project(nx, ny, depth):
    """
    Map a normalised position (nx, ny in 0..1) and depth (0=far, 1=near)
    to screen coordinates, growing outward from the vanishing point.
    """
    scale = ENEMY_MIN_SCALE + (ENEMY_MAX_SCALE - ENEMY_MIN_SCALE) * (depth ** 1.6)
    # Spread positions out from VP as depth increases
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
        diagonal = math.hypot(SCREEN_W, SCREEN_H)
        if self.alpha <= 0 or self.radius > diagonal:
            self.reset()

    def draw(self):
        r, g, b = self.colour
        arcade.draw_circle_outline(
            VP_X, VP_Y,
            self.radius, (r, g, b, max(0, self.alpha)), 1
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Player
# ─────────────────────────────────────────────────────────────────────────────
class Player:
    W, H = 28, 38

    def __init__(self):
        self.x      = SCREEN_W / 2
        self.y      = 80
        self.dx     = 0
        self.dy     = 0
        self.invuln = 0
        # Cosmetic tumble state
        self.roll        = 0.0    # side-to-side lean (radians), driven by dx
        self.pitch       = 0.0    # forward/back tilt, driven by dy
        self.wobble      = 0.0    # continuous idle wobble phase
        self.spin        = 0.0    # accumulated spin angle — kicks in on sharp moves
        self.spin_vel    = 0.0    # current spin velocity

    def update(self):
        self.x = max(self.W // 2, min(SCREEN_W - self.W // 2, self.x + self.dx))
        self.y = max(self.H // 2, min(SCREEN_H - self.H // 2, self.y + self.dy))
        if self.invuln > 0:
            self.invuln -= 1

        # Roll tracks horizontal input — lean into the turn
        target_roll = math.radians(-self.dx * 2.2)
        self.roll += (target_roll - self.roll) * 0.12

        # Pitch tracks vertical input — nose up/down
        target_pitch = math.radians(self.dy * 1.4)
        self.pitch += (target_pitch - self.pitch) * 0.10

        # Spin — moving diagonally or changing direction rapidly kicks a spin
        input_magnitude = math.hypot(self.dx, self.dy)
        if input_magnitude > PLAYER_SPEED * 1.3:   # diagonal movement
            self.spin_vel += 0.008
        # Spin decays slowly so it feels like real angular momentum
        self.spin_vel *= 0.97
        self.spin     += self.spin_vel

        # Idle wobble — the TARDIS is never perfectly still
        self.wobble += 0.04

    def draw(self):
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            return

        x, y = self.x, self.y

        # Combine all rotation angles for the final transform
        idle   = math.sin(self.wobble) * 0.055 + math.sin(self.wobble * 0.7) * 0.03
        angle  = self.roll + idle + self.spin   # total Z rotation
        tilt_x = math.sin(self.pitch) * 5       # pseudo-X tilt shifts geometry

        # Build the box corners then rotate them around the centre
        hw, hh = self.W / 2, self.H / 2
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        def rot(px, py):
            c, s = math.cos(angle), math.sin(angle)
            return (x + tilt_x + px * c - py * s,
                    y         + px * s + py * c)

        bl, br, tr, tl = [rot(px, py) for px, py in corners]

        # Main box face
        arcade.draw_polygon_filled([bl, br, tr, tl], C_TARDIS_BLUE)
        arcade.draw_polygon_outline([bl, br, tr, tl], C_TARDIS_LIGHT, 2)

        # Windows — rotated with the box
        def rot_rect(cx, cy, w, h):
            """Return 4 rotated corners of a small rectangle."""
            hw2, hh2 = w / 2, h / 2
            pts = [(-hw2, -hh2), (hw2, -hh2), (hw2, hh2), (-hw2, hh2)]
            return [rot(cx + px, cy + py) for px, py in pts]

        arcade.draw_polygon_filled(rot_rect(-6, 6, 7, 9),  C_TARDIS_LIGHT)
        arcade.draw_polygon_filled(rot_rect( 6, 6, 7, 9),  C_TARDIS_LIGHT)

        # Centre panel line
        p1 = rot(0, -hh + 4)
        p2 = rot(0,  hh - 12)
        arcade.draw_line(p1[0], p1[1], p2[0], p2[1], C_TARDIS_LIGHT, 1)

        # Lamp post on top
        lamp_base = rot(0, hh + 5)
        lamp_top  = rot(0, hh + 14)
        arcade.draw_line(lamp_base[0], lamp_base[1],
                         lamp_top[0],  lamp_top[1], C_TARDIS_LIGHT, 3)
        arcade.draw_circle_filled(lamp_top[0], lamp_top[1], 4, (220, 240, 255))

    def rect(self):
        # Collision box stays axis-aligned regardless of visual rotation
        return (self.x - self.W // 2, self.y - self.H // 2,
                self.x + self.W // 2, self.y + self.H // 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Bullet — travels into the screen (depth increases toward vanishing point)
# ─────────────────────────────────────────────────────────────────────────────
class Bullet:
    BASE_R = 4

    def __init__(self, px, py):
        # Start at player position in normalised coords
        self.nx    = px / SCREEN_W
        self.ny    = py / SCREEN_H
        self.depth = 1.0          # starts at player plane
        self.alive = True
        # Cache screen pos for collision
        self.sx, self.sy, self.scale = px, py, 1.0

    def update(self):
        self.depth -= BULLET_DEPTH_SPEED
        # Converge toward vanishing point as depth shrinks
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
#  Enemy bullet — fired from a saucer toward the TARDIS screen position
# ─────────────────────────────────────────────────────────────────────────────
class EnemyBullet:
    BASE_R = 4

    def __init__(self, sx, sy, target_x, target_y, speed=4.5):
        self.sx    = sx
        self.sy    = sy
        # Direction vector toward player screen position
        dx = target_x - sx
        dy = target_y - sy
        dist = math.hypot(dx, dy) or 1
        self.vx    = (dx / dist) * speed
        self.vy    = (dy / dist) * speed
        self.alive = True

    def update(self):
        self.sx += self.vx
        self.sy += self.vy
        if (self.sx < -20 or self.sx > SCREEN_W + 20 or
                self.sy < -20 or self.sy > SCREEN_H + 20):
            self.alive = False

    def draw(self):
        arcade.draw_circle_filled(self.sx, self.sy, self.BASE_R,       (220, 80, 20))
        arcade.draw_circle_filled(self.sx, self.sy, self.BASE_R * 0.5, (255, 200, 80))

    def rect(self):
        r = self.BASE_R
        return (self.sx - r, self.sy - r, self.sx + r, self.sy + r)


# ─────────────────────────────────────────────────────────────────────────────
#  Enemy — Dalek Saucer (pseudo-3D depth)
# ─────────────────────────────────────────────────────────────────────────────
class Enemy:
    # Base dimensions at full scale (depth == 1)
    BASE_W, BASE_H = 44, 20

    def __init__(self, wave=1):
        # Normalised screen position (0..1). Start near centre with small spread.
        self.nx    = random.uniform(0.3, 0.7)
        self.ny    = random.uniform(0.4, 0.6)
        # Drift direction in normalised space
        self.dnx   = random.uniform(-0.0008, 0.0008)
        self.dny   = random.uniform(-0.0004, 0.0002)
        # Depth: 0 = far (vanishing point), 1 = close (player plane)
        self.depth = 0.0
        # Approach speed scales with wave
        wave_mult  = 1 + (wave - 1) * 0.12          # +12% per wave
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.8, 1.3) * wave_mult
        self.alive = True
        # Cache screen coords for collision (set in draw)
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        # Shooting — cooldown shrinks with wave (more aggressive fire rate)
        base_cd    = max(0.8, 3.5 - (wave - 1) * 0.18)
        self.shoot_cd = random.uniform(base_cd * 0.5, base_cd)
        self.wave  = wave   # store for use in maybe_shoot

    def maybe_shoot(self, target_x, target_y):
        """Return an EnemyBullet if ready to fire, else None."""
        # Only shoot when saucer is visible and meaningfully large
        if self.depth < 0.35 or self.scale < 0.25:
            return None
        self.shoot_cd -= 1 / 60   # called once per frame
        if self.shoot_cd <= 0:
            # Cooldown: faster at higher waves AND when closer
            base_cd = max(0.5, 2.8 - (self.wave - 1) * 0.15)
            self.shoot_cd = random.uniform(base_cd * 0.7, base_cd) * (1.0 - self.depth * 0.45)
            # Bullet speed: scales with wave and depth
            speed = (3.5 + self.depth * 3.0) + (self.wave - 1) * 0.4
            return EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
        return None

    def update(self):
        self.depth += self.depth_speed
        # Drift outward as they approach (spread from centre)
        self.nx += self.dnx * (1 + self.depth * 2)
        self.ny += self.dny * (1 + self.depth * 2)
        if self.depth >= 1.0:
            self.alive = False   # passed the player plane

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale

        w = self.BASE_W * scale
        h = self.BASE_H * scale

        # Fade in from nothing at the vanishing point
        brightness = min(255, int(255 * (self.depth / 0.15)))

        # Dome
        dome_col = tuple(int(c * brightness / 255) for c in C_DALEK_DARK)
        arcade.draw_ellipse_filled(sx, sy + 6 * scale, (w - 8 * scale), 16 * scale, dome_col)
        # Rim
        rim_col = tuple(int(c * brightness / 255) for c in C_DALEK_GOLD)
        arcade.draw_ellipse_filled(sx, sy, w, h, rim_col)
        arcade.draw_ellipse_outline(sx, sy + 6 * scale, (w - 8 * scale), 16 * scale, rim_col, max(1, int(2 * scale)))
        # Rim dots (only when big enough to see)
        if scale > 0.25:
            dot_col = tuple(int(c * brightness / 255) for c in C_DALEK_DARK)
            for i in range(-2, 3):
                arcade.draw_circle_filled(sx + i * 9 * scale, sy, max(1, 2 * scale), dot_col)
        # Eye stalk
        eye_r = max(1.5, 5 * scale)
        eye_col = tuple(int(c * brightness / 255) for c in C_RED)
        arcade.draw_circle_filled(sx, sy + 14 * scale, eye_r, eye_col)
        if scale > 0.2:
            arcade.draw_circle_filled(sx, sy + 14 * scale, eye_r * 0.4, (255, 100, 100))

    def rect(self):
        w = self.BASE_W * self.scale
        h = (self.BASE_H + 20) * self.scale   # +20 covers dome + eye
        return (self.sx - w / 2, self.sy - h / 2,
                self.sx + w / 2, self.sy + h / 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Enemy — Individual Dalek (smaller, faster firing)
# ─────────────────────────────────────────────────────────────────────────────
class Dalek:
    # Daleks are narrower and taller than saucers
    BASE_W, BASE_H = 18, 30

    def __init__(self, wave=1):
        self.nx    = random.uniform(0.25, 0.75)
        self.ny    = random.uniform(0.35, 0.65)
        # Daleks weave more erratically than saucers
        self.dnx   = random.uniform(-0.0014, 0.0014)
        self.dny   = random.uniform(-0.0006, 0.0004)
        self.depth = 0.0
        wave_mult  = 1 + (wave - 1) * 0.10
        # Daleks approach slightly slower than saucers — they strafe more
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.7, 1.1) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        # Faster base fire rate than saucers
        base_cd       = max(0.4, 2.2 - (wave - 1) * 0.14)
        self.shoot_cd = random.uniform(base_cd * 0.4, base_cd)
        self.wave     = wave
        # Dalek gun arm angle oscillates for visual flair
        self.gun_angle = random.uniform(0, math.pi * 2)

    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.28 or self.scale < 0.20:
            return None
        self.shoot_cd -= 1 / 60
        if self.shoot_cd <= 0:
            base_cd = max(0.3, 1.8 - (self.wave - 1) * 0.10)
            self.shoot_cd = random.uniform(base_cd * 0.6, base_cd) * (1.0 - self.depth * 0.4)
            speed = (4.5 + self.depth * 3.5) + (self.wave - 1) * 0.45
            return EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
        return None

    def update(self):
        self.depth += self.depth_speed
        self.nx += self.dnx * (1 + self.depth * 2)
        self.ny += self.dny * (1 + self.depth * 2)
        self.gun_angle += 0.06   # slowly rotate gun arm
        if self.depth >= 1.0:
            self.alive = False

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale

        brightness = min(255, int(255 * (self.depth / 0.12)))
        def c(col): return tuple(int(x * brightness / 255) for x in col)

        w  = self.BASE_W * scale
        h  = self.BASE_H * scale
        s  = scale   # shorthand

        # ── Body sections (bottom to top) ──
        # Base skirt — wide truncated pyramid shape
        skirt_pts = [
            sx - w * 0.9, sy - h * 0.5,
            sx + w * 0.9, sy - h * 0.5,
            sx + w * 0.6, sy - h * 0.1,
            sx - w * 0.6, sy - h * 0.1,
        ]
        arcade.draw_polygon_filled(
            [(skirt_pts[i], skirt_pts[i+1]) for i in range(0, 8, 2)],
            c(C_DALEK_DARK)
        )

        # Mid section with sensor bumps
        draw_rect_filled(sx, sy + h * 0.08, w * 1.1, h * 0.35, c(C_DALEK_GOLD))

        # Sensor bumps (the iconic Dalek balls) — only when large enough
        if scale > 0.18:
            bump_r = max(1.5, 3.0 * s)
            rows = [(sy - h * 0.04, 3), (sy + h * 0.16, 2)]
            for row_y, count in rows:
                spacing = w * 0.55 / max(1, count - 1) if count > 1 else 0
                for i in range(count):
                    bx = sx - w * 0.275 + i * spacing if count > 1 else sx
                    arcade.draw_circle_filled(bx, row_y, bump_r, c(C_DALEK_DARK))

        # Collar / shoulder ring
        draw_rect_filled(sx, sy + h * 0.28, w * 0.85, h * 0.10, c(C_DALEK_DARK))

        # Head dome
        arcade.draw_ellipse_filled(sx, sy + h * 0.42, w * 0.7, h * 0.28, c(C_DALEK_GOLD))

        # Eyestalk — horizontal rod with eye at the end
        if scale > 0.15:
            eye_base_x = sx + w * 0.0
            eye_base_y = sy + h * 0.44
            eye_tip_x  = sx + w * 0.75
            eye_tip_y  = sy + h * 0.44
            arcade.draw_line(eye_base_x, eye_base_y, eye_tip_x, eye_tip_y,
                             c(C_DALEK_DARK), max(1, int(2 * s)))
            eye_r = max(1.5, 4 * s)
            arcade.draw_circle_filled(eye_tip_x, eye_tip_y, eye_r, c(C_RED))
            if scale > 0.25:
                arcade.draw_circle_filled(eye_tip_x, eye_tip_y, eye_r * 0.4, (255, 120, 120))

        # Gun arm — angled rod, rotates slightly
        if scale > 0.15:
            gun_len   = w * 0.9
            gun_angle = math.sin(self.gun_angle) * 0.18   # subtle oscillation
            gx = sx - w * 0.2 + math.cos(gun_angle) * gun_len
            gy = sy + h * 0.20 + math.sin(gun_angle) * gun_len * 0.4
            arcade.draw_line(sx - w * 0.2, sy + h * 0.20, gx, gy,
                             c(C_DALEK_DARK), max(1, int(2 * s)))
            # Plunger disc at tip
            if scale > 0.22:
                arcade.draw_circle_filled(gx, gy, max(1.5, 3 * s), c(C_DALEK_GOLD))

    def rect(self):
        w = self.BASE_W * self.scale * 1.8
        h = self.BASE_H * self.scale
        return (self.sx - w / 2, self.sy - h / 2,
                self.sx + w / 2, self.sy + h / 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Particles
# ─────────────────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, colour):
        self.x       = x
        self.y       = y
        angle        = random.uniform(0, 2 * math.pi)
        speed        = random.uniform(1.5, 5)
        self.vx      = math.cos(angle) * speed
        self.vy      = math.sin(angle) * speed
        self.life    = random.randint(15, 35)
        self.maxlife = self.life
        self.colour  = colour
        self.size    = random.uniform(2, 5)
        self.alive   = True

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.vy   -= 0.08
        self.life -= 1
        self.size  = max(0.5, self.size - 0.1)
        if self.life <= 0:
            self.alive = False

    def draw(self):
        a       = int(255 * (self.life / self.maxlife))
        r, g, b = self.colour
        arcade.draw_circle_filled(self.x, self.y, self.size, (r, g, b, a))

def explode(x, y, colours, n=25):
    return [Particle(x, y, random.choice(colours)) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────────────────────────────────────
def draw_hud(score, lives, wave):
    arcade.draw_text(f"SCORE  {score:06d}", 14, SCREEN_H - 28,
                     C_TEXT_GOLD, 16, font_name="Courier New", bold=True)
    arcade.draw_text(f"WAVE {wave}", SCREEN_W // 2, SCREEN_H - 28,
                     C_TEXT_BLUE, 16, anchor_x="center",
                     font_name="Courier New", bold=True)
    for i in range(lives):
        lx = SCREEN_W - 20 - i * 22
        draw_rect_filled(lx, SCREEN_H - 20, 14, 18, C_TARDIS_BLUE)
        draw_rect_outline(lx, SCREEN_H - 20, 14, 18, C_TARDIS_LIGHT, 1)

def draw_mini_tardis(cx, cy, scale=1.0):
    w  = 28 * scale
    h  = 38 * scale
    draw_rect_filled(cx, cy, w, h, C_TARDIS_BLUE)
    draw_rect_outline(cx, cy, w, h, C_TARDIS_LIGHT, max(1, int(2 * scale)))
    draw_rect_filled(cx - 6*scale, cy + 6*scale, 7*scale, 9*scale, C_TARDIS_LIGHT)
    draw_rect_filled(cx + 6*scale, cy + 6*scale, 7*scale, 9*scale, C_TARDIS_LIGHT)
    arcade.draw_circle_filled(cx, cy + h/2 + 8*scale, 4*scale, (220, 240, 255))


# ─────────────────────────────────────────────────────────────────────────────
#  Game window
# ─────────────────────────────────────────────────────────────────────────────
class GameWindow(arcade.Window):

    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, resizable=False)
        self.state = "title"
        self._init_scene()

    def _init_scene(self):
        self.stars         = [Star() for _ in range(160)]
        self.vortex        = [VortexRing() for _ in range(30)]
        self.player        = Player()
        self.bullets       = []
        self.enemies       = []
        self.daleks        = []
        self.enemy_bullets = []
        self.particles     = []
        self.score         = 0
        self.lives         = 3
        self.wave          = 1
        self.spawn_timer   = 0.0
        self.dalek_timer   = 2.5
        self.wave_kills    = 0
        self.wave_target   = 8
        self.shoot_cd      = 0.0
        self.flash_msg     = ""
        self.flash_timer   = 0.0
        self._flash_colour = C_TEXT_GOLD
        self.keys_held     = set()
        self.condition_red = False
        self.cond_timer    = 0.0
        self.elapsed          = 0.0

    def on_key_press(self, key, mod):
        self.keys_held.add(key)
        if self.state == "title" and key in (arcade.key.SPACE, arcade.key.ENTER):
            self.state = "playing"
        if self.state == "game_over" and key == arcade.key.R:
            self._init_scene()
            self.state = "playing"

    def on_key_release(self, key, mod):
        self.keys_held.discard(key)

    def on_update(self, dt):
        self.elapsed += dt
        for s in self.stars:   s.update()
        for v in self.vortex:  v.update()

        if self.state != "playing":
            return

        # Movement
        dx = dy = 0
        if arcade.key.LEFT  in self.keys_held or arcade.key.A in self.keys_held: dx -= PLAYER_SPEED
        if arcade.key.RIGHT in self.keys_held or arcade.key.D in self.keys_held: dx += PLAYER_SPEED
        if arcade.key.UP    in self.keys_held or arcade.key.W in self.keys_held: dy += PLAYER_SPEED
        if arcade.key.DOWN  in self.keys_held or arcade.key.S in self.keys_held: dy -= PLAYER_SPEED
        self.player.dx, self.player.dy = dx, dy
        self.player.update()

        # Shoot
        self.shoot_cd -= dt
        if arcade.key.SPACE in self.keys_held and self.shoot_cd <= 0:
            self.bullets.append(Bullet(self.player.x, self.player.y))
            self.shoot_cd = 0.18

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        # Spawn saucers
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.enemies) < MAX_ENEMIES:
            self.enemies.append(Enemy(self.wave))
            self.spawn_timer = max(0.5, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave - 1)))

        # Spawn individual Daleks from wave 2 onward; more frequent at higher waves
        self.dalek_timer -= dt
        if self.wave >= 2 and self.dalek_timer <= 0 and len(self.daleks) < MAX_ENEMIES:
            self.daleks.append(Dalek(self.wave))
            dalek_interval = max(0.8, 3.5 - (self.wave - 2) * 0.25)
            self.dalek_timer = dalek_interval

        for e in self.enemies: e.update()
        self.enemies = [e for e in self.enemies if e.alive]

        for d in self.daleks: d.update()
        self.daleks = [d for d in self.daleks if d.alive]

        # Enemy shooting (saucers)
        for e in self.enemies:
            shot = e.maybe_shoot(self.player.x, self.player.y)
            if shot:
                self.enemy_bullets.append(shot)

        # Dalek shooting (faster rate)
        for d in self.daleks:
            shot = d.maybe_shoot(self.player.x, self.player.y)
            if shot:
                self.enemy_bullets.append(shot)

        for eb in self.enemy_bullets: eb.update()
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

        # Bullet ↔ enemy (saucers)
        for b in self.bullets[:]:
            for e in self.enemies[:]:
                if b.alive and e.alive and rects_overlap(b.rect(), e.rect()):
                    b.alive = False
                    e.alive = False
                    self.score      += 100 * self.wave
                    self.wave_kills += 1
                    self.particles  += explode(e.sx, e.sy,
                        [C_DALEK_GOLD, C_DALEK_DARK, (255, 200, 50), C_WHITE])
                    break

        # Bullet ↔ dalek
        for b in self.bullets[:]:
            for d in self.daleks[:]:
                if b.alive and d.alive and rects_overlap(b.rect(), d.rect()):
                    b.alive = False
                    d.alive = False
                    self.score      += 150 * self.wave   # worth more than saucers
                    self.wave_kills += 1
                    self.particles  += explode(d.sx, d.sy,
                        [C_DALEK_GOLD, C_RED, (255, 160, 20), C_WHITE])
                    break

        # Enemy ↔ player (collision)
        if self.player.invuln == 0:
            pr = self.player.rect()
            for e in self.enemies[:]:
                if rects_overlap(pr, e.rect()):
                    e.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                        [C_TARDIS_BLUE, C_TARDIS_LIGHT, C_WHITE], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 120
                        self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)
                    break

        # Dalek ↔ player (collision)
        if self.player.invuln == 0:
            pr = self.player.rect()
            for d in self.daleks[:]:
                if rects_overlap(pr, d.rect()):
                    d.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                        [C_TARDIS_BLUE, C_TARDIS_LIGHT, C_RED], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 120
                        self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)
                    break

        # Enemy bullet ↔ player
        if self.player.invuln == 0:
            pr = self.player.rect()
            for eb in self.enemy_bullets[:]:
                if rects_overlap(pr, eb.rect()):
                    eb.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                        [C_TARDIS_BLUE, C_TARDIS_LIGHT, (255, 80, 20)], n=30)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 120
                        self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)
                    break

        # Wave advance
        if self.wave_kills >= self.wave_target:
            self.wave          += 1
            self.wave_kills     = 0
            self.wave_target    = 8 + self.wave * 2
            self.condition_red  = True
            self.cond_timer     = 6.0
            self.flash(f"EPISODE {self.wave}  —  CONDITION RED", 2.5, C_RED)

        if self.condition_red:
            self.cond_timer -= dt
            if self.cond_timer <= 0:
                self.condition_red = False

        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.alive]

        if self.flash_timer > 0:
            self.flash_timer -= dt

    def on_draw(self):
        self.clear((8, 4, 30))
        for v in self.vortex: v.draw()
        for s in self.stars:  s.draw()

        if self.state == "title":
            self._draw_title()
            return

        for p in self.particles: p.draw()
        for b in self.bullets:   b.draw()
        for eb in self.enemy_bullets: eb.draw()
        all_enemies = sorted(self.enemies + self.daleks, key=lambda e: e.depth)
        for e in all_enemies:
            e.draw()
        self.player.draw()
        draw_hud(self.score, self.lives, self.wave)

        if self.flash_timer > 0:
            arcade.draw_text(self.flash_msg, SCREEN_W // 2, SCREEN_H // 2 + 30,
                             self._flash_colour, 24, anchor_x="center", anchor_y="center",
                             font_name="Courier New", bold=True)

        if self.condition_red:
            arcade.draw_text("!! CONDITION RED !!", SCREEN_W // 2, SCREEN_H // 2 - 20,
                             C_RED, 20, anchor_x="center",
                             font_name="Courier New", bold=True)

        if self.state == "game_over":
            self._draw_game_over()

    def _draw_title(self):
        draw_overlay(170)
        draw_mini_tardis(SCREEN_W // 2, SCREEN_H // 2 + 220, 2.0)
        arcade.draw_text("TARDIS  VOID", SCREEN_W // 2, SCREEN_H // 2 + 130,
                         C_TARDIS_LIGHT, 52, anchor_x="center",
                         font_name="Courier New", bold=True)
        arcade.draw_text("A  D O C T O R  W H O  S P A C E  S H O O T E R",
                         SCREEN_W // 2, SCREEN_H // 2 + 80,
                         C_TEXT_GOLD, 14, anchor_x="center", font_name="Courier New")
        controls = [
            "ARROW KEYS / WASD  —  Move",
            "SPACE              —  Fire",
            "Destroy Dalek Saucers to advance!",
            "Don't let them reach you!",
        ]
        for i, line in enumerate(controls):
            arcade.draw_text(line, SCREEN_W // 2, SCREEN_H // 2 - 10 - i * 28,
                             C_TEXT_BLUE, 15, anchor_x="center", font_name="Courier New")
        if int(self.elapsed * 2) % 2 == 0:
            arcade.draw_text("PRESS  SPACE  TO  BEGIN",
                             SCREEN_W // 2, SCREEN_H // 2 - 130,
                             C_TEXT_GOLD, 20, anchor_x="center",
                             font_name="Courier New", bold=True)

    def _draw_game_over(self):
        draw_overlay(200)
        arcade.draw_text("EXTERMINATED", SCREEN_W // 2, SCREEN_H // 2 + 80,
                         C_RED, 54, anchor_x="center",
                         font_name="Courier New", bold=True)
        arcade.draw_text(f"FINAL SCORE:  {self.score:06d}",
                         SCREEN_W // 2, SCREEN_H // 2 + 10,
                         C_TEXT_GOLD, 24, anchor_x="center", font_name="Courier New")
        arcade.draw_text(f"REACHED EPISODE:  {self.wave}",
                         SCREEN_W // 2, SCREEN_H // 2 - 30,
                         C_TEXT_BLUE, 18, anchor_x="center", font_name="Courier New")
        arcade.draw_text("All regenerations exhausted.",
                         SCREEN_W // 2, SCREEN_H // 2 - 65,
                         (160, 140, 200), 14, anchor_x="center", font_name="Courier New")
        if int(self.elapsed * 2) % 2 == 0:
            arcade.draw_text("PRESS  R  TO  REGENERATE",
                             SCREEN_W // 2, SCREEN_H // 2 - 110,
                             C_TEXT_GOLD, 18, anchor_x="center",
                             font_name="Courier New", bold=True)

    def flash(self, msg, duration, colour):
        self.flash_msg     = msg
        self.flash_timer   = duration
        self._flash_colour = colour


def main():
    GameWindow()
    arcade.run()

if __name__ == "__main__":
    main()