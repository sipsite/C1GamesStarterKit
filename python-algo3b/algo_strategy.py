import gamelib
import random
from sys import maxsize


SCOUT_SPAWNS = [[13, 0], [14, 0], [9, 4], [18, 4]]

# 手动列出位于 x + y >= 15 且 x - y <= 12 的己方半场 support 点，
# 并按 y 从小到大优先建造；实际部署时跳过 x + y == 22 和 x - y == 5。
SUPPORT_LOCATIONS = [
    [13, 2], [14, 2],
    [12, 3], [13, 3], [14, 3], [15, 3],
    [11, 4], [12, 4], [13, 4], [14, 4], [15, 4], [16, 4],
    [10, 5], [11, 5], [12, 5], [13, 5], [14, 5], [15, 5], [16, 5], [17, 5],
    [9, 6], [10, 6], [11, 6], [12, 6], [13, 6], [14, 6], [15, 6], [16, 6], [17, 6], [18, 6],
    [8, 7], [9, 7], [10, 7], [11, 7], [12, 7], [13, 7], [14, 7], [15, 7], [16, 7], [17, 7], [18, 7], [19, 7],
    [7, 8], [8, 8], [9, 8], [10, 8], [11, 8], [12, 8], [13, 8], [14, 8], [15, 8], [16, 8], [17, 8], [18, 8], [19, 8], [20, 8],
    [6, 9], [7, 9], [8, 9], [9, 9], [10, 9], [11, 9], [12, 9], [13, 9], [14, 9], [15, 9], [16, 9], [17, 9], [18, 9], [19, 9], [20, 9], [21, 9],
    [5, 10], [6, 10], [7, 10], [8, 10], [9, 10], [10, 10], [11, 10], [12, 10], [13, 10], [14, 10], [15, 10], [16, 10], [17, 10], [18, 10], [19, 10], [20, 10], [21, 10], [22, 10],
    [4, 11], [5, 11], [6, 11], [7, 11], [8, 11], [9, 11], [10, 11], [11, 11], [12, 11], [13, 11], [14, 11], [15, 11], [16, 11], [17, 11], [18, 11], [19, 11], [20, 11], [21, 11], [22, 11], [23, 11],
    [3, 12], [4, 12], [5, 12], [6, 12], [7, 12], [8, 12], [9, 12], [10, 12], [11, 12], [12, 12], [13, 12], [14, 12], [15, 12], [16, 12], [17, 12], [18, 12], [19, 12], [20, 12], [21, 12], [22, 12], [23, 12], [24, 12],
    [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13], [14, 13], [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13],
]


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write("Random seed: {}".format(seed))

    def on_game_start(self, config):
        gamelib.debug_write("Configuring python-algo3...")
        self.config = config
        global SUPPORT, SCOUT, MP, SP
        SUPPORT = config["unitInformation"][1]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        MP = 1
        SP = 0

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)

        self.build_supports(game_state)
        self.send_even_scouts(game_state)

        game_state.submit_turn()

    def build_supports(self, game_state):
        support_cost = game_state.type_cost(SUPPORT)[SP]
        for location in SUPPORT_LOCATIONS:
            if game_state.get_resource(SP) < support_cost:
                break
            if location[0] + location[1] == 22 or location[0] - location[1] == 5 or location[0] + location[1] == 23 or location[0] - location[1] == 4: 
                continue
            if game_state.contains_stationary_unit(location):
                continue
            game_state.attempt_spawn(SUPPORT, location)

    def send_even_scouts(self, game_state):
        scout_count = game_state.number_affordable(SCOUT)
        if scout_count <= 0:
            return

        per_spawn = scout_count // len(SCOUT_SPAWNS)
        remainder = scout_count % len(SCOUT_SPAWNS)
        spawn_counts = [per_spawn] * len(SCOUT_SPAWNS)

        for index in range(remainder):
            spawn_counts[index] += 1

        for location, count in zip(SCOUT_SPAWNS, spawn_counts):
            if count > 0:
                game_state.attempt_spawn(SCOUT, location, count)


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
