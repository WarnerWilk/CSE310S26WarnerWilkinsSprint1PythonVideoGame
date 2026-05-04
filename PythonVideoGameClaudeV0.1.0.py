"""
Block Game - A simple arcade game where you move a block around a walled arena.
Controls: W = Up, A = Left, S = Down, D = Right
"""

import arcade

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Block Game"

WALL_THICKNESS = 20
PLAYER_SIZE = 25
PLAYER_SPEED = 4
OBSTACLE_SIZE = 70

PLAYER_COLOR = arcade.color.CYAN
WALL_COLOR = arcade.color.LIGHT_GRAY
BACKGROUND_COLOR = arcade.color.DARK_BLUE_GRAY
OBSTACLE_COLOR = arcade.color.DARK_ORANGE


class BlockGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(BACKGROUND_COLOR)

        # Player position (lower portion of screen to start)
        self.player_x = SCREEN_WIDTH / 2
        self.player_y = SCREEN_HEIGHT * 0.2

        # Immovable obstacle block (center of screen)
        self.obstacle_x = SCREEN_WIDTH / 2
        self.obstacle_y = SCREEN_HEIGHT / 2

        # Movement flags
        self.move_up = False
        self.move_down = False
        self.move_left = False
        self.move_right = False

        # Wall boundaries (inner edge of each wall)
        self.wall_left   = WALL_THICKNESS
        self.wall_right  = SCREEN_WIDTH - WALL_THICKNESS
        self.wall_bottom = WALL_THICKNESS
        self.wall_top    = SCREEN_HEIGHT - WALL_THICKNESS

    def on_draw(self):
        self.clear()

        # Draw walls
        # Bottom wall
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, 0, WALL_THICKNESS, WALL_COLOR
        )
        # Top wall
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, SCREEN_HEIGHT - WALL_THICKNESS, SCREEN_HEIGHT, WALL_COLOR
        )
        # Left wall
        arcade.draw_lrbt_rectangle_filled(
            0, WALL_THICKNESS, 0, SCREEN_HEIGHT, WALL_COLOR
        )
        # Right wall
        arcade.draw_lrbt_rectangle_filled(
            SCREEN_WIDTH - WALL_THICKNESS, SCREEN_WIDTH, 0, SCREEN_HEIGHT, WALL_COLOR
        )

        # Draw immovable obstacle block
        ohalf = OBSTACLE_SIZE / 2
        arcade.draw_lrbt_rectangle_filled(
            self.obstacle_x - ohalf,
            self.obstacle_x + ohalf,
            self.obstacle_y - ohalf,
            self.obstacle_y + ohalf,
            OBSTACLE_COLOR
        )
        arcade.draw_lrbt_rectangle_outline(
            self.obstacle_x - ohalf,
            self.obstacle_x + ohalf,
            self.obstacle_y - ohalf,
            self.obstacle_y + ohalf,
            arcade.color.WHITE,
            border_width=2
        )

        # Draw player block
        half = PLAYER_SIZE / 2
        arcade.draw_lrbt_rectangle_filled(
            self.player_x - half,
            self.player_x + half,
            self.player_y - half,
            self.player_y + half,
            PLAYER_COLOR
        )

        # Draw a subtle border on the player block
        arcade.draw_lrbt_rectangle_outline(
            self.player_x - half,
            self.player_x + half,
            self.player_y - half,
            self.player_y + half,
            arcade.color.WHITE,
            border_width=2
        )

        # HUD
        arcade.draw_text(
            "WASD to move",
            WALL_THICKNESS + 8,
            SCREEN_HEIGHT - WALL_THICKNESS - 24,
            arcade.color.WHITE,
            font_size=14
        )

    def on_update(self, delta_time):
        # Move the player
        if self.move_up:
            self.player_y += PLAYER_SPEED
        if self.move_down:
            self.player_y -= PLAYER_SPEED
        if self.move_left:
            self.player_x -= PLAYER_SPEED
        if self.move_right:
            self.player_x += PLAYER_SPEED

        # Clamp to wall boundaries
        half = PLAYER_SIZE / 2
        self.player_x = max(self.wall_left + half,
                            min(self.wall_right - half, self.player_x))
        self.player_y = max(self.wall_bottom + half,
                            min(self.wall_top - half, self.player_y))

        # Collide with obstacle block
        ohalf = OBSTACLE_SIZE / 2
        phalf = PLAYER_SIZE / 2
        overlap_x = (phalf + ohalf) - abs(self.player_x - self.obstacle_x)
        overlap_y = (phalf + ohalf) - abs(self.player_y - self.obstacle_y)

        if overlap_x > 0 and overlap_y > 0:
            # Push out along the axis of least penetration
            if overlap_x < overlap_y:
                if self.player_x < self.obstacle_x:
                    self.player_x -= overlap_x
                else:
                    self.player_x += overlap_x
            else:
                if self.player_y < self.obstacle_y:
                    self.player_y -= overlap_y
                else:
                    self.player_y += overlap_y

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W:
            self.move_up = True
        elif key == arcade.key.S:
            self.move_down = True
        elif key == arcade.key.A:
            self.move_left = True
        elif key == arcade.key.D:
            self.move_right = True

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W:
            self.move_up = False
        elif key == arcade.key.S:
            self.move_down = False
        elif key == arcade.key.A:
            self.move_left = False
        elif key == arcade.key.D:
            self.move_right = False


def main():
    game = BlockGame()
    game.run()


if __name__ == "__main__":
    main()