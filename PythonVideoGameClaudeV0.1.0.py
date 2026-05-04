"""
Block Game - Gravity edition.
Controls: A/D = Move left/right | W or SPACE = Jump
"""

import arcade

# --- Constants ---
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE  = "Block Game"

WALL_THICKNESS = 20
PLAYER_SIZE    = 25
PLAYER_SPEED   = 4
JUMP_VELOCITY  = 12
GRAVITY        = 0.5

OBSTACLE_SIZE  = 70

# Platform dimensions
PLATFORM_W = 160
PLATFORM_H = 18

PLAYER_COLOR   = arcade.color.CYAN
WALL_COLOR     = arcade.color.LIGHT_GRAY
BG_COLOR       = arcade.color.DARK_BLUE_GRAY
OBSTACLE_COLOR = arcade.color.DARK_ORANGE
PLATFORM_COLOR = (100, 200, 120)   # muted green


def rect_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    """Return (overlap_x, overlap_y) for two AABB rectangles (center, half-size)."""
    ox = (aw + bw) - abs(ax - bx)
    oy = (ah + bh) - abs(ay - by)
    return ox, oy


class BlockGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(BG_COLOR)

        # --- Player ---
        self.player_x  = SCREEN_WIDTH / 2
        self.player_y  = WALL_THICKNESS + PLAYER_SIZE / 2 + 1
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.on_ground = False

        # Movement flags
        self.move_left  = False
        self.move_right = False

        # --- Wall inner boundaries ---
        self.wall_left   = WALL_THICKNESS
        self.wall_right  = SCREEN_WIDTH  - WALL_THICKNESS
        self.wall_bottom = WALL_THICKNESS
        self.wall_top    = SCREEN_HEIGHT - WALL_THICKNESS

        # --- Immovable centre obstacle ---
        self.obstacle_x = SCREEN_WIDTH  / 2
        self.obstacle_y = SCREEN_HEIGHT / 2

        # --- Platforms (cx, cy, half_w, half_h) ---
        # Lower-left platform
        p1_cx = SCREEN_WIDTH * 0.25
        p1_cy = SCREEN_HEIGHT * 0.35
        # Upper-right platform (one step higher and to the right)
        p2_cx = SCREEN_WIDTH * 0.62
        p2_cy = SCREEN_HEIGHT * 0.58
        hw = PLATFORM_W / 2
        hh = PLATFORM_H / 2
        self.platforms = [
            (p1_cx, p1_cy, hw, hh),
            (p2_cx, p2_cy, hw, hh),
        ]

    # ------------------------------------------------------------------
    def on_draw(self):
        self.clear()

        # Walls
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, WALL_THICKNESS, WALL_COLOR)
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, SCREEN_HEIGHT - WALL_THICKNESS, SCREEN_HEIGHT, WALL_COLOR)
        arcade.draw_lrbt_rectangle_filled(0, WALL_THICKNESS, 0, SCREEN_HEIGHT, WALL_COLOR)
        arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH - WALL_THICKNESS, SCREEN_WIDTH, 0, SCREEN_HEIGHT, WALL_COLOR)

        # Platforms
        for (cx, cy, hw, hh) in self.platforms:
            arcade.draw_lrbt_rectangle_filled(cx - hw, cx + hw, cy - hh, cy + hh, PLATFORM_COLOR)
            arcade.draw_lrbt_rectangle_outline(cx - hw, cx + hw, cy - hh, cy + hh, arcade.color.WHITE, border_width=1)

        # Obstacle
        oh = OBSTACLE_SIZE / 2
        arcade.draw_lrbt_rectangle_filled(
            self.obstacle_x - oh, self.obstacle_x + oh,
            self.obstacle_y - oh, self.obstacle_y + oh,
            OBSTACLE_COLOR
        )
        arcade.draw_lrbt_rectangle_outline(
            self.obstacle_x - oh, self.obstacle_x + oh,
            self.obstacle_y - oh, self.obstacle_y + oh,
            arcade.color.WHITE, border_width=2
        )

        # Player
        ph = PLAYER_SIZE / 2
        arcade.draw_lrbt_rectangle_filled(
            self.player_x - ph, self.player_x + ph,
            self.player_y - ph, self.player_y + ph,
            PLAYER_COLOR
        )
        arcade.draw_lrbt_rectangle_outline(
            self.player_x - ph, self.player_x + ph,
            self.player_y - ph, self.player_y + ph,
            arcade.color.WHITE, border_width=2
        )

        # HUD
        arcade.draw_text(
            "A/D: move   W/Space: jump",
            WALL_THICKNESS + 8,
            SCREEN_HEIGHT - WALL_THICKNESS - 24,
            arcade.color.WHITE,
            font_size=13
        )

    # ------------------------------------------------------------------
    def on_update(self, delta_time):
        ph = PLAYER_SIZE / 2

        # Horizontal movement
        if self.move_left:
            self.vel_x = -PLAYER_SPEED
        elif self.move_right:
            self.vel_x = PLAYER_SPEED
        else:
            self.vel_x = 0

        # Gravity
        self.vel_y -= GRAVITY

        # Apply velocity
        self.player_x += self.vel_x
        self.player_y += self.vel_y

        self.on_ground = False

        # --- Wall collisions ---
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

        # --- Obstacle collision (AABB push-out) ---
        oh = OBSTACLE_SIZE / 2
        ox, oy = rect_overlap(self.player_x, self.player_y, ph, ph,
                               self.obstacle_x, self.obstacle_y, oh, oh)
        if ox > 0 and oy > 0:
            if ox < oy:
                if self.player_x < self.obstacle_x:
                    self.player_x -= ox
                else:
                    self.player_x += ox
                self.vel_x = 0
            else:
                if self.player_y < self.obstacle_y:
                    self.player_y -= oy
                    self.vel_y = 0
                else:
                    self.player_y += oy
                    self.vel_y = 0
                    self.on_ground = True

        # --- Platform collisions ---
        for (cx, cy, hw, hh) in self.platforms:
            ox, oy = rect_overlap(self.player_x, self.player_y, ph, ph,
                                   cx, cy, hw, hh)
            if ox > 0 and oy > 0:
                # Land on top
                if self.vel_y <= 0 and self.player_y > cy:
                    self.player_y += oy
                    self.vel_y = 0
                    self.on_ground = True
                # Bump head on underside
                elif self.vel_y > 0 and self.player_y < cy:
                    self.player_y -= oy
                    self.vel_y = 0
                # Side collision
                elif ox < oy:
                    if self.player_x < cx:
                        self.player_x -= ox
                    else:
                        self.player_x += ox
                    self.vel_x = 0

    # ------------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.move_left = True
        elif key == arcade.key.D:
            self.move_right = True
        elif key in (arcade.key.W, arcade.key.SPACE):
            if self.on_ground:
                self.vel_y = JUMP_VELOCITY

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