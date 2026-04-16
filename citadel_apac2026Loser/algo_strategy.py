import gamelib


SUPPORT_LOCATIONS = [
    [0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [7, 13], [6, 13],
    [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13], [14, 13],
    [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [21, 13], [20, 13],
    [22, 13], [23, 13], [24, 13], [25, 13], [22, 10], [21, 9], [20, 8],
    [19, 7], [18, 6], [17, 5], [16, 4], [15, 3], [14, 2], [13, 2], [14, 0],
    [13, 0], [11, 2], [11, 3], [10, 3], [13, 4], [12, 5], [11, 5], [10, 5],
    [8, 5], [8, 6], [10, 6], [10, 7], [10, 8], [9, 8], [8, 8], [7, 8],
    [7, 6], [5, 8], [5, 9], [6, 10], [7, 10], [8, 10], [9, 10], [10, 10],
    [11, 10], [12, 9], [12, 8], [12, 7], [13, 7], [14, 6], [13, 3], [14, 3],
    [14, 4], [15, 4], [15, 6], [17, 6], [17, 7], [15, 7], [15, 8], [16, 9],
    [17, 9], [18, 9], [18, 7], [19, 10], [22, 11], [22, 12], [24, 11],
    [24, 10], [25, 11], [27, 13], [21, 12], [19, 11], [17, 12], [17, 11],
    [15, 10], [15, 11], [15, 9], [13, 11], [13, 12], [13, 9], [14, 9],
    [13, 8], [14, 8], [14, 7], [11, 11], [9, 12], [7, 11], [5, 12], [4, 11],
    [4, 9], [4, 12], [3, 12],
]

SCOUT_SPAWN_LOCATION = [1, 12]
SCOUT_TURN = 99


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()

    def on_game_start(self, config):
        self.config = config
        global SUPPORT, SCOUT, MP
        SUPPORT = config["unitInformation"][1]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        MP = 1

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)

        self.build_and_upgrade_supports(game_state)
        self.send_final_scout_wave(game_state)

        game_state.submit_turn()

    def build_and_upgrade_supports(self, game_state):
        game_state.attempt_spawn(SUPPORT, SUPPORT_LOCATIONS)
        game_state.attempt_upgrade(SUPPORT_LOCATIONS)

    def send_final_scout_wave(self, game_state):
        if game_state.turn_number != SCOUT_TURN:
            return
        game_state.attempt_spawn(SCOUT, SCOUT_SPAWN_LOCATION, 1000)


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
