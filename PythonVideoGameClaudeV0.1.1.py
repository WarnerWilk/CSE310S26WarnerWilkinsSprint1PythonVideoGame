"""
Block Game - Camera scrolling edition.
Controls: A/D = Move left/right | W or SPACE = Jump

The world is larger than the screen. The camera follows the player,
scrolling smoothly in both axes while staying clamped to world bounds.
"""

import arcade

# --- Screen ---
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE  = "Block Game"

# --- World size (larger than screen) ---
WORLD_WIDTH  = 2400
WORLD_HEIGHT = 1800

# --- Physics ---
WALL_THICKNESS = 20
PLAYER_SIZE    = 25
PLAYER_SPEED   = 4
JUMP_VELOCITY  = 12
GRAVITY        = 0.5
FRICTION       = 0.3

# --- Camera deadzone: player must move this far from screen centre before camera shifts ---
CAM_MARGIN_X = SCREEN_WIDTH  * 0.25
CAM_MARGIN_Y = SCREEN_HEIGHT * 0.25

# --- Platform ---
PLATFORM_W = 160
PLATFORM_H = 18

# --- Movable block ---
BOX_SIZE  = 28
BOX_COLOR = arcade.color.ORANGE

# --- Colours ---
PLAYER_COLOR   = arcade.color.CYAN
WALL_COLOR     = arcade.color.LIGHT_GRAY
BG_COLOR       = arcade.color.DARK_BLUE_GRAY
PLATFORM_COLOR = (100, 200, 120)


def rect_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    ox = (aw + bw) - abs(ax - bx)
    oy = (ah + bh) - abs(ay - by)
    return ox, oy


class BlockGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(BG_COLOR)

        # Camera offset (world coord of the bottom-left of the viewport)
        self.cam_x = 0.0
        self.cam_y = 0.0

        # --- Player (world coords) ---
        self.player_x  = WALL_THICKNESS + PLAYER_SIZE / 2 + 1
        self.player_y  = WALL_THICKNESS + PLAYER_SIZE / 2 + 1
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.on_ground = False

        # Movement flags
        self.move_left  = False
        self.move_right = False

        # --- World wall boundaries ---
        self.wall_left   = WALL_THICKNESS
        self.wall_right  = WORLD_WIDTH  - WALL_THICKNESS
        self.wall_bottom = WALL_THICKNESS
        self.wall_top    = WORLD_HEIGHT - WALL_THICKNESS

        # --- Platforms (world coords: cx, cy, half_w, half_h) ---
        hw = PLATFORM_W / 2
        hh = PLATFORM_H / 2
        self.platforms = [
            # Platform 1 (leftmost) at 160 units height
            [WORLD_WIDTH * 0.1, 160, hw, hh],
            # Platform 2 (middle) at 200 units height
            [WORLD_WIDTH * 0.25, 200, hw, hh],
            # Platform 3 at 300 units height
            [WORLD_WIDTH * 0.37, 300, hw, hh],
            # Platform 4 (moving) at 200 units height
            [WORLD_WIDTH * 0.5, 200, hw, hh],
        ]

        # Moving platform variables
        self.moving_platform_dir = 1  # 1 for right, -1 for left
        self.moving_platform_speed = 1  # pixels per frame
        self.on_moving_platform = False
        self.moving_platform_vel = 0

        # Time rewind history
        self.platform_history = []
        self.box_history = []
        self.rewinding = False
        self.max_history = 600

        # Movable box
        self.box_x = WORLD_WIDTH * 0.4
        self.box_y = WALL_THICKNESS + BOX_SIZE / 2 + 1
        self.box_vel_x = 0.0
        self.box_vel_y = 0.0
        self.box_on_ground = False
        self.carrying_box = False

        # Centre camera on player at start
        self._update_camera()

    # ------------------------------------------------------------------
    def _update_camera(self):
        """Scroll camera so player stays within the deadzone margins."""
        # Desired camera so player is centred
        target_x = self.player_x - SCREEN_WIDTH  / 2
        target_y = self.player_y - SCREEN_HEIGHT / 2

        # Only shift when player leaves the deadzone
        left_bound   = self.cam_x + (SCREEN_WIDTH  / 2 - CAM_MARGIN_X)
        right_bound  = self.cam_x + (SCREEN_WIDTH  / 2 + CAM_MARGIN_X)
        bottom_bound = self.cam_y + (SCREEN_HEIGHT / 2 - CAM_MARGIN_Y)
        top_bound    = self.cam_y + (SCREEN_HEIGHT / 2 + CAM_MARGIN_Y)

        if self.player_x < left_bound:
            self.cam_x = self.player_x - (SCREEN_WIDTH  / 2 - CAM_MARGIN_X)
        elif self.player_x > right_bound:
            self.cam_x = self.player_x - (SCREEN_WIDTH  / 2 + CAM_MARGIN_X)

        if self.player_y < bottom_bound:
            self.cam_y = self.player_y - (SCREEN_HEIGHT / 2 - CAM_MARGIN_Y)
        elif self.player_y > top_bound:
            self.cam_y = self.player_y - (SCREEN_HEIGHT / 2 + CAM_MARGIN_Y)

        # Clamp camera to world bounds
        self.cam_x = max(0, min(WORLD_WIDTH  - SCREEN_WIDTH,  self.cam_x))
        self.cam_y = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, self.cam_y))

    def _wx(self, world_x):
        """World X → screen X."""
        return world_x - self.cam_x

    def _wy(self, world_y):
        """World Y → screen Y."""
        return world_y - self.cam_y

    # ------------------------------------------------------------------
    def on_draw(self):
        self.clear()

        cx, cy = self.cam_x, self.cam_y

        # --- World walls ---
        # Bottom
        arcade.draw_lrbt_rectangle_filled(
            self._wx(0), self._wx(WORLD_WIDTH),
            self._wy(0), self._wy(WALL_THICKNESS),
            WALL_COLOR)
        # Top
        arcade.draw_lrbt_rectangle_filled(
            self._wx(0), self._wx(WORLD_WIDTH),
            self._wy(WORLD_HEIGHT - WALL_THICKNESS), self._wy(WORLD_HEIGHT),
            WALL_COLOR)
        # Left
        arcade.draw_lrbt_rectangle_filled(
            self._wx(0), self._wx(WALL_THICKNESS),
            self._wy(0), self._wy(WORLD_HEIGHT),
            WALL_COLOR)
        # Right
        arcade.draw_lrbt_rectangle_filled(
            self._wx(WORLD_WIDTH - WALL_THICKNESS), self._wx(WORLD_WIDTH),
            self._wy(0), self._wy(WORLD_HEIGHT),
            WALL_COLOR)

        # --- Platforms ---
        for (pcx, pcy, hw, hh) in self.platforms:
            sx = self._wx(pcx); sy = self._wy(pcy)
            arcade.draw_lrbt_rectangle_filled(sx - hw, sx + hw, sy - hh, sy + hh, PLATFORM_COLOR)
            arcade.draw_lrbt_rectangle_outline(sx - hw, sx + hw, sy - hh, sy + hh, arcade.color.WHITE, border_width=1)

        # --- Movable box ---
        bh = BOX_SIZE / 2
        bx = self._wx(self.box_x); by = self._wy(self.box_y)
        arcade.draw_lrbt_rectangle_filled(bx - bh, bx + bh, by - bh, by + bh, BOX_COLOR)
        arcade.draw_lrbt_rectangle_outline(bx - bh, bx + bh, by - bh, by + bh, arcade.color.WHITE, border_width=2)

        # --- Player ---
        ph = PLAYER_SIZE / 2
        sx = self._wx(self.player_x); sy = self._wy(self.player_y)
        arcade.draw_lrbt_rectangle_filled(sx - ph, sx + ph, sy - ph, sy + ph, PLAYER_COLOR)
        arcade.draw_lrbt_rectangle_outline(sx - ph, sx + ph, sy - ph, sy + ph, arcade.color.WHITE, border_width=2)

        # --- HUD (fixed to screen) ---
        arcade.draw_text(
            "A/D: move   W/Space: jump   P: pick up/drop   R: rewind",
            WALL_THICKNESS + 8,
            SCREEN_HEIGHT - WALL_THICKNESS - 24,
            arcade.color.WHITE,
            font_size=13
        )

    # ------------------------------------------------------------------
    def on_update(self, delta_time):
        ph = PLAYER_SIZE / 2

        # Update moving platform and rewind playback
        moving_platform = self.platforms[3]
        if self.rewinding:
            if len(self.platform_history) > 1:
                self.platform_history.pop()
                prev_x, prev_dir = self.platform_history[-1]
                moving_platform[0] = prev_x
                self.moving_platform_dir = prev_dir
            else:
                self.rewinding = False
        else:
            self.platform_history.append((moving_platform[0], self.moving_platform_dir))
            if len(self.platform_history) > self.max_history:
                self.platform_history.pop(0)
            moving_platform[0] += self.moving_platform_speed * self.moving_platform_dir
            min_x = WORLD_WIDTH * 0.5
            max_x = WORLD_WIDTH * 0.6
            if moving_platform[0] < min_x or moving_platform[0] > max_x:
                self.moving_platform_dir *= -1
                moving_platform[0] = max(min_x, min(max_x, moving_platform[0]))

        # Horizontal movement
        if self.on_moving_platform:
            if self.move_left:
                self.vel_x = -PLAYER_SPEED + self.moving_platform_vel
            elif self.move_right:
                self.vel_x = PLAYER_SPEED + self.moving_platform_vel
            else:
                self.vel_x = self.moving_platform_vel
        elif self.on_ground:
            if self.move_left:
                self.vel_x = -PLAYER_SPEED
            elif self.move_right:
                self.vel_x = PLAYER_SPEED
            else:
                if abs(self.vel_x) <= FRICTION:
                    self.vel_x = 0
                elif self.vel_x > 0:
                    self.vel_x -= FRICTION
                else:
                    self.vel_x += FRICTION
        else:
            # Airborne: only change velocity if input
            if self.move_left:
                self.vel_x = -PLAYER_SPEED
            elif self.move_right:
                self.vel_x = PLAYER_SPEED
            # else: keep current horizontal velocity

        # Gravity
        self.vel_y -= GRAVITY

        # Apply velocity
        self.player_x += self.vel_x
        self.player_y += self.vel_y

        # Movable box physics / carrying / rewind
        bh = BOX_SIZE / 2
        if self.rewinding:
            if len(self.box_history) > 1:
                self.box_history.pop()
                prev_x, prev_y, prev_vx, prev_vy, _ = self.box_history[-1]
                self.box_x = prev_x
                self.box_y = prev_y
                self.box_vel_x = prev_vx
                self.box_vel_y = prev_vy
                self.carrying_box = False
            else:
                self.rewinding = False
        elif self.carrying_box:
            self.box_x = self.player_x
            self.box_y = self.player_y + ph + bh + 1
            self.box_vel_x = 0
            self.box_vel_y = 0
            self.box_on_ground = False
            self.box_history.append((self.box_x, self.box_y, self.box_vel_x, self.box_vel_y, True))
            if len(self.box_history) > self.max_history:
                self.box_history.pop(0)
        else:
            self.box_history.append((self.box_x, self.box_y, self.box_vel_x, self.box_vel_y, False))
            if len(self.box_history) > self.max_history:
                self.box_history.pop(0)
            self.box_vel_y -= GRAVITY
            self.box_x += self.box_vel_x
            self.box_y += self.box_vel_y
            self.box_on_ground = False

        self.on_ground = False

        # --- World wall collisions ---
        if self.player_x - ph < self.wall_left:
            self.player_x = self.wall_left + ph
            self.vel_x = 0
        elif self.player_x + ph > self.wall_right:
            self.player_x = self.wall_right - ph
            self.vel_x = 0

        if self.player_y - ph < self.wall_bottom:
            self.player_y = self.wall_bottom + ph
            self.vel_y = 0
            self.on_ground = True

        if self.player_y + ph > self.wall_top:
            self.player_y = self.wall_top - ph
            self.vel_y = 0

        # --- Box world collisions ---
        if self.box_x - bh < self.wall_left:
            self.box_x = self.wall_left + bh
            self.box_vel_x = 0
        elif self.box_x + bh > self.wall_right:
            self.box_x = self.wall_right - bh
            self.box_vel_x = 0

        if self.box_y - bh < self.wall_bottom:
            self.box_y = self.wall_bottom + bh
            self.box_vel_y = 0
            self.box_on_ground = True

        if self.box_y + bh > self.wall_top:
            self.box_y = self.wall_top - bh
            self.box_vel_y = 0

        # --- Platform collisions ---
        self.on_moving_platform = False  # Reset flag
        for i, platform in enumerate(self.platforms):
            pcx, pcy, hw, hh = platform[0], platform[1], platform[2], platform[3]
            ox, oy = rect_overlap(self.player_x, self.player_y, ph, ph,
                                   pcx, pcy, hw, hh)
            if ox > 0 and oy > 0:
                if self.vel_y <= 0 and self.player_y > pcy:
                    self.player_y += oy
                    self.vel_y = 0
                    self.on_ground = True
                    # If on moving platform, set flag and velocity
                    if i == 3:
                        self.on_moving_platform = True
                        self.moving_platform_vel = self.moving_platform_speed * self.moving_platform_dir
                elif self.vel_y > 0 and self.player_y < pcy:
                    self.player_y -= oy
                    self.vel_y = 0
                elif ox < oy:
                    if self.player_x < pcx:
                        self.player_x -= ox
                    else:
                        self.player_x += ox
                    self.vel_x = 0

            # Box collisions with platforms
            box_ox, box_oy = rect_overlap(self.box_x, self.box_y, bh, bh,
                                          pcx, pcy, hw, hh)
            if box_ox > 0 and box_oy > 0:
                if self.box_vel_y <= 0 and self.box_y > pcy:
                    self.box_y += box_oy
                    self.box_vel_y = 0
                    self.box_on_ground = True
                elif self.box_vel_y > 0 and self.box_y < pcy:
                    self.box_y -= box_oy
                    self.box_vel_y = 0
                elif box_ox < box_oy:
                    if self.box_x < pcx:
                        self.box_x -= box_ox
                    else:
                        self.box_x += box_ox
                    self.box_vel_x = 0

        if self.box_on_ground and not self.carrying_box:
            if abs(self.box_vel_x) <= FRICTION:
                self.box_vel_x = 0
            elif self.box_vel_x > 0:
                self.box_vel_x -= FRICTION
            else:
                self.box_vel_x += FRICTION

        # --- Player / box collision ---
        if not self.carrying_box:
            box_ox, box_oy = rect_overlap(self.player_x, self.player_y, ph, ph,
                                          self.box_x, self.box_y, bh, bh)
            if box_ox > 0 and box_oy > 0:
                if self.vel_y <= 0 and self.player_y > self.box_y:
                    self.player_y += box_oy
                    self.vel_y = 0
                    self.on_ground = True
                    # carry the block when standing on it
                    self.box_x += self.vel_x * 0.1
                elif self.vel_y > 0 and self.player_y < self.box_y:
                    self.player_y -= box_oy
                    self.vel_y = 0
                elif box_ox < box_oy:
                    if self.player_x < self.box_x:
                        self.player_x -= box_ox
                        self.box_vel_x = self.vel_x
                    else:
                        self.player_x += box_ox
                        self.box_vel_x = self.vel_x
                    self.vel_x = 0

        # Update camera after all movement resolved
        self._update_camera()

    # ------------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.move_left = True
        elif key == arcade.key.D:
            self.move_right = True
        elif key in (arcade.key.W, arcade.key.SPACE):
            if self.on_ground:
                self.vel_y = JUMP_VELOCITY
        elif key == arcade.key.P:
            if self.carrying_box:
                self.carrying_box = False
                self.box_vel_x = self.vel_x
                self.box_vel_y = 0
            else:
                close_enough = abs(self.player_x - self.box_x) < PLAYER_SIZE + BOX_SIZE and abs(self.player_y - self.box_y) < PLAYER_SIZE + BOX_SIZE
                if close_enough and self.box_on_ground:
                    self.carrying_box = True
                    self.box_vel_x = 0
                    self.box_vel_y = 0
        elif key == arcade.key.R:
            if self.rewinding:
                self.rewinding = False
            else:
                self.rewinding = True
                self.carrying_box = False

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.move_left = False
        elif key == arcade.key.D:
            self.move_right = False


def main():
    game = BlockGame()
    game.run()


if __name__ == "__main__":
    main()