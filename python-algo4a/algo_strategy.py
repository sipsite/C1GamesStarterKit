from collections import deque

import gamelib


SUPPORT_LOCATIONS = [
    [13, 13], [14, 13], [14, 12], [13, 12],
]

WALL_CHECK_Y = 14


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

        self.build_supports(game_state)
        self.build_blocking_walls(game_state)
        self.send_scouts(game_state)

        game_state.submit_turn()

    def build_supports(self, game_state):
        game_state.attempt_spawn(SUPPORT, SUPPORT_LOCATIONS)
        game_state.attempt_upgrade(SUPPORT_LOCATIONS)

    def build_blocking_walls(self, game_state):
        if game_state.turn_number == 0:
            return

        for enemy_location in self.get_wall_check_locations_center_out(game_state):
            wall_location = [enemy_location[0], enemy_location[1] - 1]
            should_block = self.should_block_enemy_front(game_state, enemy_location)

            if should_block:
                if not game_state.contains_stationary_unit(wall_location):
                    game_state.attempt_spawn(WALL, wall_location)
                continue

            wall = game_state.contains_stationary_unit(wall_location)
            if wall and wall.player_index == 0 and wall.unit_type == WALL:
                game_state.attempt_remove(wall_location)

        for wall_location in self.get_wall_upgrade_locations_edge_in(game_state):
            wall = game_state.contains_stationary_unit(wall_location)
            if wall and wall.player_index == 0 and wall.unit_type == WALL and not wall.upgraded:
                game_state.attempt_upgrade(wall_location)

    def send_scouts(self, game_state):
        if game_state.get_resource(MP) < game_state.type_cost(SCOUT)[MP]:
            return

        best_location = self.get_best_scout_spawn_location(game_state)
        if best_location is None:
            return
        game_state.attempt_spawn(SCOUT, best_location, 1000)

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

    def get_wall_check_locations_center_out(self, game_state):
        locations = []
        for x in range(game_state.ARENA_SIZE):
            location = [x, WALL_CHECK_Y]
            if game_state.game_map.in_arena_bounds(location):
                locations.append(location)
        center = (game_state.ARENA_SIZE - 1) / 2
        return sorted(locations, key=lambda location: (abs(location[0] - center), location[0]))

    def get_wall_upgrade_locations_edge_in(self, game_state):
        locations = []
        for x in range(game_state.ARENA_SIZE):
            location = [x, WALL_CHECK_Y - 1]
            if game_state.game_map.in_arena_bounds(location):
                locations.append(location)
        center = (game_state.ARENA_SIZE - 1) / 2
        return sorted(locations, key=lambda location: (-abs(location[0] - center), location[0]))

    def should_block_enemy_front(self, game_state, enemy_location):
        structure = game_state.contains_stationary_unit(enemy_location)
        if structure and structure.player_index == 1:
            return False
        if structure:
            return True
        return self.can_reach_enemy_spawn_edges(game_state, enemy_location)

    def can_reach_enemy_spawn_edges(self, game_state, start_location):
        if game_state.contains_stationary_unit(start_location):
            return False

        target_locations = {
            tuple(location)
            for location in (
                game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT)
                + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
            )
        }
        queue = deque([tuple(start_location)])
        visited = {tuple(start_location)}

        while queue:
            x, y = queue.popleft()
            if (x, y) in target_locations:
                return True

            for next_location in ([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]):
                next_key = tuple(next_location)
                if next_key in visited:
                    continue
                if not game_state.game_map.in_arena_bounds(next_location):
                    continue
                if game_state.contains_stationary_unit(next_location):
                    continue
                visited.add(next_key)
                queue.append(next_key)

        return False


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
