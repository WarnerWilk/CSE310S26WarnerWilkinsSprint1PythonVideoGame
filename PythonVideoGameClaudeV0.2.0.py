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
PATROL_DEPTH  = 0.82    # depth at which enemies stop approaching and start patrolling
PATROL_STEER  = 0.025   # lerp speed toward patrol target (normalised space)
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
        dx = target_x - sx
        dy = target_y - sy
        dist = math.hypot(dx, dy) or 1
        self.vx    = (dx / dist) * speed
        self.vy    = (dy / dist) * speed
        self.alive = True
        self.colour     = (220, 80,  20)   # default orange (Dalek)
        self.colour_dim = (255, 200, 80)
 
    def update(self):
        self.sx += self.vx
        self.sy += self.vy
        if (self.sx < -20 or self.sx > SCREEN_W + 20 or
                self.sy < -20 or self.sy > SCREEN_H + 20):
            self.alive = False
 
    def draw(self):
        arcade.draw_circle_filled(self.sx, self.sy, self.BASE_R,       self.colour)
        arcade.draw_circle_filled(self.sx, self.sy, self.BASE_R * 0.5, self.colour_dim)
 
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
        # Patrol state — ships switch to this once close enough
        self.patrolling = False
        self.target_nx  = self.nx
        self.target_ny  = self.ny
        self.patrol_cd  = 0.0
        # Dalek deployment — saucers drop individual Daleks when close enough
        self.deploy_cd = random.uniform(4.0, 8.0)
        self.deployed  = 0    # how many Daleks this saucer has dropped
 
    def maybe_deploy(self):
        """Return a Dalek spawned at this saucer's position, or None."""
        if self.depth < 0.30 or self.deployed >= 2:
            return None
        self.deploy_cd -= 1 / 60
        if self.deploy_cd <= 0:
            self.deploy_cd = random.uniform(5.0, 9.0)
            self.deployed += 1
            return Dalek(self.wave, spawn_nx=self.nx, spawn_ny=self.ny,
                         spawn_depth=self.depth)
        return None
 
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
 
    def _new_patrol_target(self, player_nx, player_ny):
        """Pick a random firing position offset from the player in normalised space."""
        angle  = random.uniform(0, math.pi * 2)
        radius = random.uniform(0.12, 0.30)
        self.target_nx = max(0.05, min(0.95, player_nx + math.cos(angle) * radius))
        self.target_ny = max(0.05, min(0.95, player_ny + math.sin(angle) * radius * 0.7))
        self.patrol_cd = random.uniform(2.5, 5.0)   # how long to stay at this spot
 
    def update(self, player_nx=0.5, player_ny=0.5):
        if not self.patrolling:
            self.depth += self.depth_speed
            # Drift outward as they approach (spread from centre)
            self.nx += self.dnx * (1 + self.depth * 2)
            self.ny += self.dny * (1 + self.depth * 2)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True
                self.depth      = PATROL_DEPTH
                self._new_patrol_target(player_nx, player_ny)
        else:
            # Smoothly steer toward current patrol target
            self.nx += (self.target_nx - self.nx) * PATROL_STEER
            self.ny += (self.target_ny - self.ny) * PATROL_STEER
            # Count down to picking a new position
            self.patrol_cd -= 1 / 60
            if self.patrol_cd <= 0:
                self._new_patrol_target(player_nx, player_ny)
 
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
 
    def __init__(self, wave=1, spawn_nx=None, spawn_ny=None, spawn_depth=None):
        # Spawn at saucer position if provided, otherwise default (unused now)
        self.nx    = spawn_nx if spawn_nx is not None else 0.5
        self.ny    = spawn_ny if spawn_ny is not None else 0.5
        # Daleks weave more erratically than saucers
        self.dnx   = random.uniform(-0.0014, 0.0014)
        self.dny   = random.uniform(-0.0006, 0.0004)
        self.depth = spawn_depth if spawn_depth is not None else 0.0
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
        # Patrol state
        self.patrolling = False
        self.target_nx  = self.nx
        self.target_ny  = self.ny
        self.patrol_cd  = 0.0
 
    def _new_patrol_target(self, player_nx, player_ny):
        angle  = random.uniform(0, math.pi * 2)
        radius = random.uniform(0.10, 0.25)
        self.target_nx = max(0.05, min(0.95, player_nx + math.cos(angle) * radius))
        self.target_ny = max(0.05, min(0.95, player_ny + math.sin(angle) * radius * 0.7))
        self.patrol_cd = random.uniform(1.5, 3.5)   # daleks reposition faster
 
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
 
    def update(self, player_nx=0.5, player_ny=0.5):
        self.gun_angle += 0.06
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth * 2)
            self.ny += self.dny * (1 + self.depth * 2)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True
                self.depth      = PATROL_DEPTH
                self._new_patrol_target(player_nx, player_ny)
        else:
            # Daleks steer slightly faster/jerkier than saucers
            steer = PATROL_STEER * 1.4
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1 / 60
            if self.patrol_cd <= 0:
                self._new_patrol_target(player_nx, player_ny)
 
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
#  Enemy — Individual Cyberman (deployed from Cyber Ships)
# ─────────────────────────────────────────────────────────────────────────────
class CybermanUnit:
    BASE_W, BASE_H = 24, 32

    def __init__(self, wave=1, spawn_nx=None, spawn_ny=None, spawn_depth=None):
        # Spawn at ship position if provided
        self.nx    = spawn_nx if spawn_nx is not None else 0.5
        self.ny    = spawn_ny if spawn_ny is not None else 0.5
        self.dnx   = random.uniform(-0.0012, 0.0012)
        self.dny   = random.uniform(-0.0005, 0.0003)
        self.depth = spawn_depth if spawn_depth is not None else 0.0
        wave_mult  = 1 + (wave - 1) * 0.08
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.8, 1.2) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        # Cybermen fire less frequently than Daleks
        base_cd       = max(0.8, 2.5 - (wave - 1) * 0.12)
        self.shoot_cd = random.uniform(base_cd * 0.8, base_cd)
        self.wave     = wave
        self.patrolling = False
        self.target_nx  = self.nx
        self.target_ny  = self.ny
        self.patrol_cd  = 0.0

    def _new_patrol_target(self, player_nx, player_ny):
        angle  = random.uniform(0, math.pi * 2)
        radius = random.uniform(0.12, 0.28)
        self.target_nx = max(0.05, min(0.95, player_nx + math.cos(angle) * radius))
        self.target_ny = max(0.05, min(0.95, player_ny + math.sin(angle) * radius * 0.7))
        self.patrol_cd = random.uniform(2.0, 4.0)

    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.25 or self.scale < 0.18:
            return None
        self.shoot_cd -= 1 / 60
        if self.shoot_cd <= 0:
            base_cd = max(0.6, 2.0 - (self.wave - 1) * 0.10)
            self.shoot_cd = random.uniform(base_cd * 0.8, base_cd) * (1.0 - self.depth * 0.3)
            speed = (6.0 + self.depth * 4.5) + (self.wave - 1) * 0.6
            bullet = EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
            bullet.colour     = C_CYBER_GLOW
            bullet.colour_dim = (30, 100, 120)
            return bullet
        return None

    def update(self, player_nx=0.5, player_ny=0.5):
        if not self.patrolling:
            self.depth += self.depth_speed
            self.nx += self.dnx * (1 + self.depth * 1.8)
            self.ny += self.dny * (1 + self.depth * 1.8)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True
                self.depth      = PATROL_DEPTH
                self._new_patrol_target(player_nx, player_ny)
        else:
            steer = PATROL_STEER * 1.2
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1 / 60
            if self.patrol_cd <= 0:
                self._new_patrol_target(player_nx, player_ny)

    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale

        brightness = min(255, int(255 * (self.depth / 0.12)))
        def c(col): return tuple(int(x * brightness / 255) for x in col)

        w  = self.BASE_W * scale
        h  = self.BASE_H * scale
        s  = scale

        # Cyberman body — angular, robotic
        body_pts = [
            sx - w * 0.4, sy - h * 0.5,
            sx + w * 0.4, sy - h * 0.5,
            sx + w * 0.3, sy + h * 0.2,
            sx - w * 0.3, sy + h * 0.2,
        ]
        arcade.draw_polygon_filled(body_pts, c(C_CYBER_SILVER))
        arcade.draw_polygon_outline(body_pts, c(C_CYBER_DARK), max(1, int(2*s)))

        # Chest panel
        draw_rect_filled(sx, sy + h * 0.05, w * 0.6, h * 0.25, c(C_CYBER_DARK))

        # Head — rectangular with glowing eyes
        draw_rect_filled(sx, sy + h * 0.35, w * 0.5, h * 0.2, c(C_CYBER_SILVER))
        if scale > 0.15:
            # Eyes
            eye_r = max(1.5, 3 * s)
            arcade.draw_circle_filled(sx - w*0.15, sy + h*0.35, eye_r, c(C_CYBER_GLOW))
            arcade.draw_circle_filled(sx + w*0.15, sy + h*0.35, eye_r, c(C_CYBER_GLOW))
            if scale > 0.25:
                arcade.draw_circle_filled(sx - w*0.15, sy + h*0.35, eye_r * 0.4, (200, 255, 255))
                arcade.draw_circle_filled(sx + w*0.15, sy + h*0.35, eye_r * 0.4, (200, 255, 255))

        # Arms — angular
        if scale > 0.18:
            arm_y = sy + h * 0.1
            arcade.draw_line(sx - w*0.45, arm_y, sx - w*0.65, arm_y - h*0.1,
                             c(C_CYBER_DARK), max(1, int(2*s)))
            arcade.draw_line(sx + w*0.45, arm_y, sx + w*0.65, arm_y - h*0.1,
                             c(C_CYBER_DARK), max(1, int(2*s)))

    def rect(self):
        w = self.BASE_W * self.scale * 1.2
        h = self.BASE_H * self.scale
        return (self.sx - w / 2, self.sy - h / 2,
                self.sx + w / 2, self.sy + h / 2)
 
# ── Powerup / Angel colours ───────────────────────────────────────────────────
C_DROP_LIFE    = (220,  60,  80)   # red heart — extra life
C_DROP_PIERCE  = (255, 200,  40)   # gold — piercing bullet
C_DROP_FIRE    = ( 60, 220, 140)   # green — fire rate
C_ANGEL_STONE  = (140, 135, 128)   # weathered grey
C_ANGEL_DARK   = ( 80,  76,  70)
C_ANGEL_GLOW   = (200, 190, 170)   # pale highlight

# ── Cyberman colours ──────────────────────────────────────────────────────────
C_CYBER_SILVER = (160, 175, 190)
C_CYBER_DARK   = ( 50,  60,  70)
C_CYBER_GLOW   = ( 80, 200, 220)   # cold blue-green glow

class Cyberman:
    # Base dimensions at full scale (depth == 1)
    BASE_W, BASE_H = 44, 20

    def __init__(self, wave=1):
        # Always spawns very close to the vortex centre
        self.nx    = random.uniform(0.44, 0.56)
        self.ny    = random.uniform(0.44, 0.56)
        # Drift outward slowly — they creep toward the player
        self.dnx   = random.uniform(-0.0006, 0.0006)
        self.dny   = random.uniform(-0.0003, 0.0003)
        self.depth = 0.0
        wave_mult  = 1 + (wave - 1) * 0.09
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.6, 0.95) * wave_mult
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        # Cybermen ships fire less frequently
        base_cd       = max(0.9, 3.8 - (wave - 1) * 0.16)
        self.shoot_cd = random.uniform(base_cd * 0.6, base_cd)
        self.wave     = wave
        # Rotation for the geometric ship shape
        self.rot      = random.uniform(0, math.pi * 2)
        self.rot_vel  = random.choice([-1, 1]) * random.uniform(0.008, 0.022)
        # Patrol state
        self.patrolling = False
        self.target_nx  = self.nx
        self.target_ny  = self.ny
        self.patrol_cd  = 0.0
        # Cyberman deployment — ships drop individual Cybermen when close enough
        self.deploy_cd = random.uniform(2.0, 5.0)  # More frequent than Daleks
        self.deployed  = 0

    def maybe_deploy(self):
        """Return a CybermanUnit spawned at this ship's position, or None."""
        if self.depth < 0.25 or self.deployed >= 3:  # Deploy more than Daleks
            return None
        self.deploy_cd -= 1 / 60
        if self.deploy_cd <= 0:
            self.deploy_cd = random.uniform(2.5, 6.0)  # More frequent spawns
            self.deployed += 1
            return CybermanUnit(self.wave, spawn_nx=self.nx, spawn_ny=self.ny,
                                spawn_depth=self.depth)
        return None
    def _new_patrol_target(self, player_nx, player_ny):
        # Cybermen keep more distance — orbit further out
        angle  = random.uniform(0, math.pi * 2)
        radius = random.uniform(0.18, 0.35)
        self.target_nx = max(0.05, min(0.95, player_nx + math.cos(angle) * radius))
        self.target_ny = max(0.05, min(0.95, player_ny + math.sin(angle) * radius * 0.7))
        self.patrol_cd = random.uniform(3.0, 6.0)   # cybermen reposition slowly
 
    def maybe_shoot(self, target_x, target_y):
        if self.depth < 0.25 or self.scale < 0.18:
            return None
        self.shoot_cd -= 1 / 60
        if self.shoot_cd <= 0:
            base_cd = max(0.6, 3.2 - (self.wave - 1) * 0.14)
            self.shoot_cd = random.uniform(base_cd * 0.7, base_cd) * (1.0 - self.depth * 0.35)
            # Cyberman shots are fast and blue-green
            speed = (5.5 + self.depth * 4.0) + (self.wave - 1) * 0.5
            bullet = EnemyBullet(self.sx, self.sy, target_x, target_y, speed)
            bullet.colour     = C_CYBER_GLOW          # override colour
            bullet.colour_dim = (40, 120, 140)
            return bullet
        return None
 
    def update(self, player_nx=0.5, player_ny=0.5):
        self.rot += self.rot_vel
        if not self.patrolling:
            self.depth   += self.depth_speed
            self.nx      += self.dnx * (1 + self.depth * 1.5)
            self.ny      += self.dny * (1 + self.depth * 1.5)
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True
                self.depth      = PATROL_DEPTH
                self._new_patrol_target(player_nx, player_ny)
        else:
            # Cybermen glide smoothly — lowest steer rate of all three
            steer = PATROL_STEER * 0.7
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1 / 60
            if self.patrol_cd <= 0:
                self._new_patrol_target(player_nx, player_ny)
 
    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
 
        brightness = min(255, int(255 * (self.depth / 0.12)))
        def c(col): return tuple(int(x * brightness / 255) for x in col)
 
        r   = self.rot
        s   = scale
        hw  = self.BASE_W * s * 0.5
        hh  = self.BASE_H * s * 0.5
 
        def rv(px, py):
            """Rotate a point around (sx, sy)."""
            cr, sr = math.cos(r), math.sin(r)
            x = sx + px * cr - py * sr
            y = sy + px * sr + py * cr
            return (x, y)
 
        # Outer hexagonal hull
        hex_pts = [rv(math.cos(math.pi/2 + i*math.pi/3) * hw * 1.1,
                      math.sin(math.pi/2 + i*math.pi/3) * hh * 1.1)
                   for i in range(6)]
        arcade.draw_polygon_filled(hex_pts, c(C_CYBER_DARK))
        arcade.draw_polygon_outline(hex_pts, c(C_CYBER_SILVER), max(1, int(2*s)))
 
        # Inner diamond
        diamond = [rv(0, hh*0.55), rv(hw*0.55, 0),
                   rv(0, -hh*0.55), rv(-hw*0.55, 0)]
        arcade.draw_polygon_filled(diamond, c(C_CYBER_SILVER))
 
        # Centre glow eye
        if scale > 0.12:
            eye_r = max(1.5, 5 * s)
            arcade.draw_circle_filled(sx, sy, eye_r, c(C_CYBER_GLOW))
            if scale > 0.22:
                arcade.draw_circle_filled(sx, sy, eye_r * 0.45, (200, 255, 255))
 
        # Four angular struts from centre to hull corners
        if scale > 0.20:
            for i in [0, 1, 3, 4]:
                pt = hex_pts[i]
                arcade.draw_line(sx, sy, pt[0], pt[1],
                                 c(C_CYBER_SILVER), max(1, int(s * 1.5)))
 
    def rect(self):
        r = self.BASE_W * self.scale * 0.9
        return (self.sx - r, self.sy - r, self.sx + r, self.sy + r)
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  Pickup — item dropped by killed enemies, drifts toward player
# ─────────────────────────────────────────────────────────────────────────────
class Pickup:
    R = 9
 
    def __init__(self, sx, sy, kind):
        self.sx    = float(sx)
        self.sy    = float(sy)
        self.kind  = kind   # "life" | "pierce" | "fire"
        self.alive = True
        self.age   = 0
        self.vx    = random.uniform(-1.2, 1.2)
        self.vy    = random.uniform(-1.2, 1.2)
 
    COLOURS = {"life": C_DROP_LIFE, "pierce": C_DROP_PIERCE, "fire": C_DROP_FIRE}
    LABELS  = {"life": "+", "pierce": "P", "fire": "F"}
 
    def update(self, player_x, player_y):
        self.age += 1
        # Gently home toward the player after a short delay
        if self.age > 30:
            dx = player_x - self.sx
            dy = player_y - self.sy
            dist = math.hypot(dx, dy) or 1
            speed = 1.2 + min(3.0, self.age * 0.01)
            self.vx += (dx / dist) * 0.18
            self.vy += (dy / dist) * 0.18
            # Cap speed
            spd = math.hypot(self.vx, self.vy)
            if spd > speed:
                self.vx = self.vx / spd * speed
                self.vy = self.vy / spd * speed
        self.sx += self.vx
        self.sy += self.vy
        if self.age > 420:   # despawn after 7 seconds
            self.alive = False
 
    def draw(self):
        col = self.COLOURS[self.kind]
        pulse = 0.7 + 0.3 * math.sin(self.age * 0.18)
        r = int(self.R * pulse)
        arcade.draw_circle_filled(self.sx, self.sy, r + 3, (255, 255, 255, 60))
        arcade.draw_circle_filled(self.sx, self.sy, r,     col)
        arcade.draw_text(self.LABELS[self.kind], self.sx, self.sy - 5,
                         C_WHITE, 10, anchor_x="center", font_name="Courier New", bold=True)
 
    def rect(self):
        return (self.sx - self.R, self.sy - self.R,
                self.sx + self.R, self.sy + self.R)
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  Weeping Angel — quantum-locked. Only moves when NOT watched.
#  "Watched" = player and angel in same screen quadrant, OR angel is closer
#  to the vortex centre than the player is.
# ─────────────────────────────────────────────────────────────────────────────
class WeepingAngel:
    BASE_W, BASE_H = 22, 36
 
    def __init__(self, wave=1):
        # Spawn near the edge of the vortex (mid-depth)
        angle      = random.uniform(0, math.pi * 2)
        self.nx    = 0.5 + math.cos(angle) * random.uniform(0.28, 0.38)
        self.ny    = 0.5 + math.sin(angle) * random.uniform(0.20, 0.28)
        self.nx    = max(0.05, min(0.95, self.nx))
        self.ny    = max(0.05, min(0.95, self.ny))
        self.depth = random.uniform(0.25, 0.45)   # start mid-field
        self.depth_speed = ENEMY_DEPTH_SPEED * random.uniform(0.5, 0.8)
        self.alive = True
        self.sx, self.sy, self.scale = VP_X, VP_Y, ENEMY_MIN_SCALE
        self.wave  = wave
        self.frozen     = False   # True when quantum-locked (player watching)
        self.lunge_cd   = random.uniform(2.0, 5.0)
        self.patrolling = False
        self.target_nx  = self.nx
        self.target_ny  = self.ny
        self.patrol_cd  = 0.0
        self.shoot_cd   = max(0.6, 4.0 - (wave - 1) * 0.2)
 
    def _player_quadrant(self, pnx, pny):
        return (int(pnx > 0.5), int(pny > 0.5))
 
    def _my_quadrant(self):
        return (int(self.nx > 0.5), int(self.ny > 0.5))
 
    def _player_dist_from_centre(self, pnx, pny):
        return math.hypot(pnx - 0.5, pny - 0.5)
 
    def _my_dist_from_centre(self):
        return math.hypot(self.nx - 0.5, self.ny - 0.5)
 
    def is_watched(self, pnx, pny):
        """True when the angel should be quantum-locked (cannot move)."""
        same_quad = self._player_quadrant(pnx, pny) == self._my_quadrant()
        angel_closer = self._my_dist_from_centre() < self._player_dist_from_centre(pnx, pny)
        return same_quad or angel_closer
 
    def _new_patrol_target(self, pnx, pny):
        angle  = random.uniform(0, math.pi * 2)
        radius = random.uniform(0.08, 0.22)
        self.target_nx = max(0.05, min(0.95, pnx + math.cos(angle) * radius))
        self.target_ny = max(0.05, min(0.95, pny + math.sin(angle) * radius * 0.7))
        self.patrol_cd = random.uniform(1.0, 2.5)
 
    def maybe_shoot(self, target_x, target_y):
        """Angels don't shoot — they lunge. Returns None always."""
        return None
 
    def update(self, player_nx=0.5, player_ny=0.5):
        watched = self.is_watched(player_nx, player_ny)
        self.frozen = watched
 
        if watched:
            return   # quantum locked — no movement at all
 
        # Not watched — move
        if not self.patrolling:
            self.depth += self.depth_speed
            # Creep toward player position
            self.nx += (player_nx - self.nx) * 0.004
            self.ny += (player_ny - self.ny) * 0.004
            if self.depth >= PATROL_DEPTH:
                self.patrolling = True
                self.depth      = PATROL_DEPTH
                self._new_patrol_target(player_nx, player_ny)
        else:
            # At patrol depth — steer aggressively toward player
            steer = PATROL_STEER * 2.2
            self.nx += (self.target_nx - self.nx) * steer
            self.ny += (self.target_ny - self.ny) * steer
            self.patrol_cd -= 1 / 60
            if self.patrol_cd <= 0:
                self._new_patrol_target(player_nx, player_ny)
 
    def draw(self):
        sx, sy, scale = project(self.nx, self.ny, self.depth)
        self.sx, self.sy, self.scale = sx, sy, scale
 
        brightness = min(255, int(255 * (self.depth / 0.12)))
        # Flicker slightly when not frozen to hint at movement
        if not self.frozen:
            brightness = min(255, brightness + random.randint(-15, 15))
        def c(col): return tuple(int(x * brightness / 255) for x in col)
 
        w = self.BASE_W * scale
        h = self.BASE_H * scale
        s = scale
 
        # Robe body — rough stone trapezoid
        body = [
            (sx - w * 0.55, sy - h * 0.5),
            (sx + w * 0.55, sy - h * 0.5),
            (sx + w * 0.35, sy + h * 0.3),
            (sx - w * 0.35, sy + h * 0.3),
        ]
        arcade.draw_polygon_filled(body, c(C_ANGEL_STONE))
        arcade.draw_polygon_outline(body, c(C_ANGEL_DARK), max(1, int(s * 1.5)))
 
        # Wings — two angular shapes behind body
        if scale > 0.15:
            left_wing = [
                (sx - w * 0.35, sy + h * 0.2),
                (sx - w * 1.1,  sy + h * 0.4),
                (sx - w * 0.9,  sy - h * 0.1),
                (sx - w * 0.3,  sy + h * 0.0),
            ]
            right_wing = [
                (sx + w * 0.35, sy + h * 0.2),
                (sx + w * 1.1,  sy + h * 0.4),
                (sx + w * 0.9,  sy - h * 0.1),
                (sx + w * 0.3,  sy + h * 0.0),
            ]
            arcade.draw_polygon_filled(left_wing,  c(C_ANGEL_DARK))
            arcade.draw_polygon_filled(right_wing, c(C_ANGEL_DARK))
            arcade.draw_polygon_outline(left_wing,  c(C_ANGEL_STONE), max(1, int(s)))
            arcade.draw_polygon_outline(right_wing, c(C_ANGEL_STONE), max(1, int(s)))
 
        # Head
        if scale > 0.10:
            arcade.draw_ellipse_filled(sx, sy + h * 0.42, w * 0.55, h * 0.22,
                                       c(C_ANGEL_STONE))
            # Face — when frozen: hands-over-face (two dark patches)
            # when moving: hollow eyes glowing
            if self.frozen:
                if scale > 0.25:
                    arcade.draw_ellipse_filled(sx - w*0.12, sy + h*0.44,
                                               w*0.16, h*0.10, c(C_ANGEL_DARK))
                    arcade.draw_ellipse_filled(sx + w*0.12, sy + h*0.44,
                                               w*0.16, h*0.10, c(C_ANGEL_DARK))
            else:
                if scale > 0.22:
                    eye_col = (min(255, brightness + 40), 20, 20)
                    arcade.draw_circle_filled(sx - w*0.12, sy + h*0.44,
                                             max(1.5, 3*s), eye_col)
                    arcade.draw_circle_filled(sx + w*0.12, sy + h*0.44,
                                             max(1.5, 3*s), eye_col)
 
    def rect(self):
        w = self.BASE_W * self.scale * 1.1
        h = self.BASE_H * self.scale
        return (self.sx - w/2, self.sy - h/2,
                self.sx + w/2, self.sy + h/2)
 
 
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
def draw_mini_tardis(cx, cy, scale=1.0):
    w  = 28 * scale
    h  = 38 * scale
    draw_rect_filled(cx, cy, w, h, C_TARDIS_BLUE)
    draw_rect_outline(cx, cy, w, h, C_TARDIS_LIGHT, max(1, int(2 * scale)))
    draw_rect_filled(cx - 6*scale, cy + 6*scale, 7*scale, 9*scale, C_TARDIS_LIGHT)
    draw_rect_filled(cx + 6*scale, cy + 6*scale, 7*scale, 9*scale, C_TARDIS_LIGHT)
    arcade.draw_circle_filled(cx, cy + h/2 + 8*scale, 4*scale, (220, 240, 255))
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
        
        # Create Text objects for better performance
        self.text_score = arcade.Text("", 14, SCREEN_H - 28, C_TEXT_GOLD, 16, font_name="Courier New", bold=True)
        self.text_wave = arcade.Text("", SCREEN_W // 2, SCREEN_H - 28, C_TEXT_BLUE, 16, anchor_x="center", font_name="Courier New", bold=True)
        self.text_pierce = arcade.Text("", 14, 14, C_DROP_PIERCE, 13, font_name="Courier New", bold=True)
        self.text_fire = arcade.Text("", 14, 30, C_DROP_FIRE, 13, font_name="Courier New", bold=True)
        self.text_flash = arcade.Text("", SCREEN_W // 2, SCREEN_H // 2 + 30, C_TEXT_GOLD, 24, anchor_x="center", anchor_y="center", font_name="Courier New", bold=True)
        self.text_condition_red = arcade.Text("!! CONDITION RED !!", SCREEN_W // 2, SCREEN_H // 2 - 20, C_RED, 20, anchor_x="center", font_name="Courier New", bold=True)
        
        # Title screen text
        self.text_title_main = arcade.Text("TARDIS  VOID", SCREEN_W // 2, SCREEN_H // 2 + 130, C_TARDIS_LIGHT, 52, anchor_x="center", font_name="Courier New", bold=True)
        self.text_title_sub = arcade.Text("A  D O C T O R  W H O  S P A C E  S H O O T E R", SCREEN_W // 2, SCREEN_H // 2 + 80, C_TEXT_GOLD, 14, anchor_x="center", font_name="Courier New")
        self.text_title_controls = [
            arcade.Text("ARROW KEYS / WASD  —  Move", SCREEN_W // 2, SCREEN_H // 2 - 10, C_TEXT_BLUE, 15, anchor_x="center", font_name="Courier New"),
            arcade.Text("SPACE              —  Fire", SCREEN_W // 2, SCREEN_H // 2 - 38, C_TEXT_BLUE, 15, anchor_x="center", font_name="Courier New"),
            arcade.Text("Destroy Dalek Saucers to advance!", SCREEN_W // 2, SCREEN_H // 2 - 66, C_TEXT_BLUE, 15, anchor_x="center", font_name="Courier New"),
            arcade.Text("Don't let them reach you!", SCREEN_W // 2, SCREEN_H // 2 - 94, C_TEXT_BLUE, 15, anchor_x="center", font_name="Courier New"),
        ]
        self.text_title_press = arcade.Text("PRESS  SPACE  TO  BEGIN", SCREEN_W // 2, SCREEN_H // 2 - 130, C_TEXT_GOLD, 20, anchor_x="center", font_name="Courier New", bold=True)
        
        # Game over screen text
        self.text_game_over_main = arcade.Text("EXTERMINATED", SCREEN_W // 2, SCREEN_H // 2 + 80, C_RED, 54, anchor_x="center", font_name="Courier New", bold=True)
        self.text_game_over_score = arcade.Text("", SCREEN_W // 2, SCREEN_H // 2 + 10, C_TEXT_GOLD, 24, anchor_x="center", font_name="Courier New")
        self.text_game_over_wave = arcade.Text("", SCREEN_W // 2, SCREEN_H // 2 - 30, C_TEXT_BLUE, 18, anchor_x="center", font_name="Courier New")
        self.text_game_over_msg = arcade.Text("All regenerations exhausted.", SCREEN_W // 2, SCREEN_H // 2 - 65, (160, 140, 200), 14, anchor_x="center", font_name="Courier New")
        self.text_game_over_press = arcade.Text("PRESS  R  TO  REGENERATE", SCREEN_W // 2, SCREEN_H // 2 - 110, C_TEXT_GOLD, 18, anchor_x="center", font_name="Courier New", bold=True)
        
        self._init_scene()
 
    def _init_scene(self):
        self.stars         = [Star() for _ in range(160)]
        self.vortex        = [VortexRing() for _ in range(30)]
        self.player        = Player()
        self.bullets       = []
        self.enemies       = []
        self.daleks        = []
        self.cybermen      = []  # cyberships
        self.cyberman_units = []  # individual cybermen
        self.angels        = []
        self.pickups       = []
        self.enemy_bullets = []
        self.particles     = []
        self.score         = 0
        self.lives         = 3
        self.wave          = 1
        self.spawn_timer   = 0.0
        self.dalek_timer   = 2.5
        self.cyber_timer   = 5.0
        self.angel_timer   = 12.0   # angels appear later
        # Powerup stacks
        self.stat_pierce   = 0   # each stack: +10% chance bullet pierces on kill
        self.stat_fire     = 0   # each stack: -0.02s shoot cooldown
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
            self.shoot_cd = max(0.06, 0.18 - self.stat_fire * 0.02)
 
        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.alive]
 
        # Spawn saucers
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.enemies) < MAX_ENEMIES:
            self.enemies.append(Enemy(self.wave))
            self.spawn_timer = max(0.5, ENEMY_SPAWN_INTERVAL * (0.92 ** (self.wave - 1)))
 
        # Saucers deploy individual Daleks from their position (wave 2+)
        if self.wave >= 2:
            for e in self.enemies:
                dalek = e.maybe_deploy()
                if dalek and len(self.daleks) < MAX_ENEMIES:
                    self.daleks.append(dalek)
 
        # Cybermen ships emerge from the vortex centre (wave 3+)
        self.cyber_timer -= dt
        if self.wave >= 3 and self.cyber_timer <= 0 and len(self.cybermen) < MAX_ENEMIES:
            self.cybermen.append(Cyberman(self.wave))
            cyber_interval   = max(1.2, 5.0 - (self.wave - 3) * 0.3)
            self.cyber_timer = cyber_interval

        # Cyber ships deploy individual Cybermen (wave 3+)
        if self.wave >= 3:
            for cy in self.cybermen:
                cyberman_unit = cy.maybe_deploy()
                if cyberman_unit and len(self.cyberman_units) < MAX_ENEMIES:
                    self.cyberman_units.append(cyberman_unit)
 
        # Weeping Angels — appear from wave 4, max 3 on screen at once
        self.angel_timer -= dt
        if self.wave >= 4 and self.angel_timer <= 0 and len(self.angels) < 3:
            self.angels.append(WeepingAngel(self.wave))
            self.angel_timer = max(8.0, 18.0 - (self.wave - 4) * 1.5)
 
        # Compute player normalised position once for enemy steering
        pnx = self.player.x / SCREEN_W
        pny = self.player.y / SCREEN_H
 
        for e in self.enemies: e.update(pnx, pny)
        self.enemies = [e for e in self.enemies if e.alive]
 
        for d in self.daleks: d.update(pnx, pny)
        self.daleks = [d for d in self.daleks if d.alive]
 
        for cy in self.cybermen: cy.update(pnx, pny)
        self.cybermen = [cy for cy in self.cybermen if cy.alive]

        for cu in self.cyberman_units: cu.update(pnx, pny)
        self.cyberman_units = [cu for cu in self.cyberman_units if cu.alive]
 
        for ang in self.angels: ang.update(pnx, pny)
        self.angels = [ang for ang in self.angels if ang.alive]
 
        # Enemy shooting (saucers)
        for e in self.enemies:
            shot = e.maybe_shoot(self.player.x, self.player.y)
            if shot:
                self.enemy_bullets.append(shot)
 
        # Dalek shooting (faster rate)
        for d in self.daleks:
            # Sometimes target cybermen instead of player
            target_x, target_y = self.player.x, self.player.y
            if random.random() < 0.15 and (self.cybermen or self.cyberman_units):  # 15% chance
                # Target a random cyber enemy
                cyber_targets = self.cybermen + self.cyberman_units
                target_enemy = random.choice(cyber_targets)
                target_x, target_y = target_enemy.sx, target_enemy.sy
            shot = d.maybe_shoot(target_x, target_y)
            if shot:
                self.enemy_bullets.append(shot)
 
        # Cyberman shooting (fast bullets, less frequent)
        for cy in self.cybermen:
            shot = cy.maybe_shoot(self.player.x, self.player.y)
            if shot:
                self.enemy_bullets.append(shot)

        # Individual Cyberman shooting (less frequent than Daleks)
        for cu in self.cyberman_units:
            # Sometimes target daleks instead of player
            target_x, target_y = self.player.x, self.player.y
            if random.random() < 0.12 and (self.daleks or self.enemies):  # 12% chance
                # Target a random dalek enemy
                dalek_targets = self.daleks + self.enemies
                target_enemy = random.choice(dalek_targets)
                target_x, target_y = target_enemy.sx, target_enemy.sy
            shot = cu.maybe_shoot(target_x, target_y)
            if shot:
                self.enemy_bullets.append(shot)
 
        for eb in self.enemy_bullets: eb.update()
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]
 
        # Bullet ↔ enemy (saucers) — drops life pickup
        for b in self.bullets[:]:
            for e in self.enemies[:]:
                if b.alive and e.alive and rects_overlap(b.rect(), e.rect()):
                    pierce_roll = random.random() < self.stat_pierce * 0.10
                    if not pierce_roll:
                        b.alive = False
                    e.alive = False
                    self.score      += 100 * self.wave
                    self.wave_kills += 1
                    self.particles  += explode(e.sx, e.sy,
                        [C_DALEK_GOLD, C_DALEK_DARK, (255, 200, 50), C_WHITE])
                    if random.random() < 0.18:   # 18% drop rate
                        self.pickups.append(Pickup(e.sx, e.sy, "life"))
                    break
 
        # Bullet ↔ dalek — drops pierce powerup
        for b in self.bullets[:]:
            for d in self.daleks[:]:
                if b.alive and d.alive and rects_overlap(b.rect(), d.rect()):
                    pierce_roll = random.random() < self.stat_pierce * 0.10
                    if not pierce_roll:
                        b.alive = False
                    d.alive = False
                    self.score      += 150 * self.wave
                    self.wave_kills += 1
                    self.particles  += explode(d.sx, d.sy,
                        [C_DALEK_GOLD, C_RED, (255, 160, 20), C_WHITE])
                    if random.random() < 0.22:   # 22% drop rate
                        self.pickups.append(Pickup(d.sx, d.sy, "pierce"))
                    break
 
        # Bullet ↔ cyberman — drops fire rate powerup
        for b in self.bullets[:]:
            for cy in self.cybermen[:]:
                if b.alive and cy.alive and rects_overlap(b.rect(), cy.rect()):
                    pierce_roll = random.random() < self.stat_pierce * 0.10
                    if not pierce_roll:
                        b.alive = False
                    cy.alive = False
                    self.score      += 200 * self.wave
                    self.wave_kills += 1
                    self.particles  += explode(cy.sx, cy.sy,
                        [C_CYBER_SILVER, C_CYBER_GLOW, C_CYBER_DARK, C_WHITE])
                    if random.random() < 0.30:   # 30% drop rate
                        self.pickups.append(Pickup(cy.sx, cy.sy, "fire"))
                    break

        # Bullet ↔ individual cyberman — drops fire rate powerup
        for b in self.bullets[:]:
            for cu in self.cyberman_units[:]:
                if b.alive and cu.alive and rects_overlap(b.rect(), cu.rect()):
                    pierce_roll = random.random() < self.stat_pierce * 0.10
                    if not pierce_roll:
                        b.alive = False
                    cu.alive = False
                    self.score      += 180 * self.wave
                    self.wave_kills += 1
                    self.particles  += explode(cu.sx, cu.sy,
                        [C_CYBER_SILVER, C_CYBER_GLOW, C_CYBER_DARK, C_WHITE])
                    if random.random() < 0.25:   # 25% drop rate
                        self.pickups.append(Pickup(cu.sx, cu.sy, "fire"))
                    break
 
        # Bullet ↔ angel — angels can be stunned briefly but not killed
        for b in self.bullets[:]:
            for ang in self.angels[:]:
                if b.alive and ang.alive and rects_overlap(b.rect(), ang.rect()):
                    pierce_roll = random.random() < self.stat_pierce * 0.10
                    if not pierce_roll:
                        b.alive = False
                    # Angels are quantum-locked by the hit flash — no kill
                    ang.frozen = True
                    ang.patrol_cd = max(ang.patrol_cd, 1.5)
                    self.particles += explode(ang.sx, ang.sy,
                        [C_ANGEL_STONE, C_ANGEL_GLOW, C_WHITE], n=12)
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
 
        # Cyberman ↔ player (collision)
        if self.player.invuln == 0:
            pr = self.player.rect()
            for cy in self.cybermen[:]:
                if rects_overlap(pr, cy.rect()):
                    cy.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                        [C_TARDIS_BLUE, C_CYBER_GLOW, C_WHITE], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 120
                        self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)
                    break

        # Individual Cyberman ↔ player (collision)
        if self.player.invuln == 0:
            pr = self.player.rect()
            for cu in self.cyberman_units[:]:
                if rects_overlap(pr, cu.rect()):
                    cu.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                        [C_TARDIS_BLUE, C_CYBER_GLOW, C_WHITE], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 120
                        self.flash("REGENERATING...", 2.0, C_TEXT_GOLD)
                    break
 
        # Angel ↔ player — angels that reach you take a life
        if self.player.invuln == 0:
            pr = self.player.rect()
            for ang in self.angels[:]:
                if not ang.frozen and rects_overlap(pr, ang.rect()):
                    ang.alive = False
                    self.particles += explode(self.player.x, self.player.y,
                        [C_ANGEL_STONE, C_ANGEL_GLOW, C_WHITE], n=40)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        self.player.invuln = 120
                        # Time vortex jump: random level 1-200
                        old_wave = self.wave
                        self.wave = random.randint(1, 200)
                        self.wave_kills = 0
                        self.wave_target = 8 + self.wave * 2
                        self.flash(f"TIME VORTEX JUMP: EPISODE {self.wave}!", 3.0, C_ANGEL_GLOW)
                    break
 
        # Pickup collection
        pr = self.player.rect()
        for pk in self.pickups[:]:
            pk.update(self.player.x, self.player.y)
            if rects_overlap(pr, pk.rect()):
                pk.alive = False
                if pk.kind == "life":
                    self.lives += 1
                    self.flash("+1 REGENERATION", 1.5, C_DROP_LIFE)
                elif pk.kind == "pierce":
                    self.stat_pierce += 1
                    self.flash(f"PIERCE UPGRADED  x{self.stat_pierce}", 1.5, C_DROP_PIERCE)
                elif pk.kind == "fire":
                    self.stat_fire += 1
                    self.flash(f"FIRE RATE UPGRADED  +{self.stat_fire}", 1.5, C_DROP_FIRE)
        self.pickups = [pk for pk in self.pickups if pk.alive]
 
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
        for pk in self.pickups:  pk.draw()
        for b in self.bullets:   b.draw()
        for eb in self.enemy_bullets: eb.draw()
        all_enemies = sorted(self.enemies + self.daleks + self.cybermen + self.cyberman_units + self.angels,
                             key=lambda e: e.depth)
        for e in all_enemies:
            e.draw()
        self.player.draw()
        
        # Update and draw HUD text
        self.text_score.text = f"SCORE  {self.score:06d}"
        self.text_score.draw()
        self.text_wave.text = f"WAVE {self.wave}"
        self.text_wave.draw()
        for i in range(self.lives):
            lx = SCREEN_W - 20 - i * 22
            draw_rect_filled(lx, SCREEN_H - 20, 14, 18, C_TARDIS_BLUE)
            draw_rect_outline(lx, SCREEN_H - 20, 14, 18, C_TARDIS_LIGHT, 1)
        # Powerup stacks bottom-left
        if self.stat_pierce > 0:
            self.text_pierce.text = f"PIERCE x{self.stat_pierce}"
            self.text_pierce.draw()
        if self.stat_fire > 0:
            self.text_fire.text = f"FIRE +{self.stat_fire}"
            self.text_fire.draw()
 
        if self.flash_timer > 0:
            self.text_flash.text = self.flash_msg
            self.text_flash.color = self._flash_colour
            self.text_flash.draw()
 
        if self.condition_red:
            self.text_condition_red.draw()
 
        if self.state == "game_over":
            self._draw_game_over()
 
    def _draw_title(self):
        draw_overlay(170)
        draw_mini_tardis(SCREEN_W // 2, SCREEN_H // 2 + 220, 2.0)
        self.text_title_main.draw()
        self.text_title_sub.draw()
        for text_obj in self.text_title_controls:
            text_obj.draw()
        if int(self.elapsed * 2) % 2 == 0:
            self.text_title_press.draw()
 
    def _draw_game_over(self):
        draw_overlay(200)
        self.text_game_over_main.draw()
        self.text_game_over_score.text = f"FINAL SCORE:  {self.score:06d}"
        self.text_game_over_score.draw()
        self.text_game_over_wave.text = f"REACHED EPISODE:  {self.wave}"
        self.text_game_over_wave.draw()
        self.text_game_over_msg.draw()
        if int(self.elapsed * 2) % 2 == 0:
            self.text_game_over_press.draw()
 
    def flash(self, msg, duration, colour):
        self.flash_msg     = msg
        self.flash_timer   = duration
        self._flash_colour = colour
 
 
def main():
    GameWindow()
    arcade.run()
 
if __name__ == "__main__":
    main()