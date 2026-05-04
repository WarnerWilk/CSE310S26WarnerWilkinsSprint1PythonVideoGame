import importlib.util
from pathlib import Path

# Dynamically load the V0.1.1 game module from its file path.
module_path = Path(__file__).resolve().parent / "PythonVideoGameClaudeV0.1.1.py"
spec = importlib.util.spec_from_file_location("game_v011", module_path)
game_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game_module)


class DemoGame(game_module.BlockGame):
    def __init__(self):
        super().__init__()
        self.frame = 0
        self.action_index = 0
        self.timeline = [
            (30, "move_right", True),
            (140, "move_right", False),
            (145, "jump", True),
            (170, "move_right", True),
            (280, "move_right", False),
            (300, "pick_box", True),
            (320, "move_right", True),
            (420, "move_right", False),
            (440, "rewind", True),
            (560, "rewind", False),
            (570, "move_left", True),
            (640, "move_left", False),
        ]

    def on_update(self, delta_time):
        self.frame += 1
        self._apply_timeline_actions()
        super().on_update(delta_time)

        if self.frame % 60 == 0:
            moving_platform_x = self.platforms[3][0]
            print(
                f"Frame {self.frame}: player=({self.player_x:.1f},{self.player_y:.1f}) "
                f"box=({self.box_x:.1f},{self.box_y:.1f}) "
                f"platform={moving_platform_x:.1f} rewinding={self.rewinding}"
            )

    def _apply_timeline_actions(self):
        while self.action_index < len(self.timeline) and self.timeline[self.action_index][0] == self.frame:
            _, action, value = self.timeline[self.action_index]
            self._run_action(action, value)
            self.action_index += 1

    def _run_action(self, action, value):
        if action == "move_right":
            self.move_right = value
            if value:
                self.move_left = False
        elif action == "move_left":
            self.move_left = value
            if value:
                self.move_right = False
        elif action == "jump" and value:
            if self.on_ground:
                self.vel_y = self.JUMP_VELOCITY if hasattr(self, "JUMP_VELOCITY") else game_module.JUMP_VELOCITY
        elif action == "pick_box" and value:
            close_enough = abs(self.player_x - self.box_x) < game_module.PLAYER_SIZE + game_module.BOX_SIZE
            if close_enough and self.box_on_ground:
                self.carrying_box = True
                self.box_vel_x = 0
                self.box_vel_y = 0
        elif action == "rewind":
            self.rewinding = value
            if value:
                self.carrying_box = False


def main():
    demo = DemoGame()
    demo.run()


if __name__ == "__main__":
    main()
