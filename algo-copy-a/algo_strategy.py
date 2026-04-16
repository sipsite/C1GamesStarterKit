import gamelib
import random


PRIORITY_1_TURRETS = [
    [13, 13], [12, 12], [14, 13], [15, 12],
]

PRIORITY_1_SUPPORTS = [
    [13, 12], [14, 12], [13, 11], [14, 11],
]

PRIORITY_2_TURRETS = [
    [0, 13], [27, 13], [1, 13], [26, 13], [3, 13], [24, 13],
    [6, 13], [21, 13], [9, 13], [18, 13],
]

PRIORITY_3_TURRETS = [
    [11, 11], [16, 11], [10, 12], [17, 12],
]

PRIORITY_3_SUPPORTS = [
    [13, 10], [14, 10],
]

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()

    def on_game_start(self, config):
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)

        self.build_defenses(game_state)
        self.send_scouts(game_state)

        game_state.submit_turn()

    def build_defenses(self, game_state):
        game_state.attempt_spawn(TURRET, PRIORITY_1_TURRETS)
        game_state.attempt_spawn(SUPPORT, PRIORITY_1_SUPPORTS)
        game_state.attempt_upgrade(PRIORITY_1_SUPPORTS)
        game_state.attempt_spawn(TURRET, PRIORITY_2_TURRETS)
        game_state.attempt_spawn(TURRET, PRIORITY_3_TURRETS)
        game_state.attempt_spawn(SUPPORT, PRIORITY_3_SUPPORTS)
        game_state.attempt_upgrade(PRIORITY_3_SUPPORTS)

    def send_scouts(self, game_state):
        if game_state.get_resource(MP) < game_state.type_cost(SCOUT)[MP]:
            return

        spawn_location = self.get_best_scout_spawn_location(game_state)
        if spawn_location is None:
            return
        game_state.attempt_spawn(SCOUT, spawn_location, 1000)

    def get_best_scout_spawn_location(self, game_state):
        turret_damage = gamelib.GameUnit(TURRET, game_state.config).damage_i
        best_location = None
        best_damage = None

        for location in self.get_friendly_edge_locations(game_state):
            if not game_state.can_spawn(SCOUT, location):
                continue

            target_edge = game_state.get_target_edge(location)
            target_edge_locations = game_state.game_map.get_edge_locations(target_edge)
            path = game_state.find_path_to_edge(location, target_edge)
            if not path or path[-1] not in target_edge_locations:
                continue

            total_damage = 0
            for path_location in path:
                attackers = game_state.get_attackers(path_location, 0)
                total_damage += len(attackers) * turret_damage

            if best_damage is None or total_damage < best_damage:
                best_location = location
                best_damage = total_damage

        return best_location

    def get_friendly_edge_locations(self, game_state):
        return (
            game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        )


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
