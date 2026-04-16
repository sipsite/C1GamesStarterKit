from collections import deque

import gamelib


SUPPORT_LOCATIONS = [
    [13, 13], [14, 13], [14, 12], [13, 12],
]

WALL_CHECK_Y = 14


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        self.counterattack_x = None
        self.counterattack_ready_turn = None
        self.counterattack_ready_x = None
        self.counterattack_prep_turn = None

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
        self.counterattack_prep_turn = None

        self.build_blocking_walls(game_state)
        best_scout_location = self.get_best_scout_spawn_location(game_state)
        self.manage_supports(game_state, best_scout_location)
        self.build_rearguard_walls(game_state)
        self.send_scouts(game_state, best_scout_location)

        game_state.submit_turn()

    def manage_supports(self, game_state, best_scout_location):
        if self.counterattack_prep_turn == game_state.turn_number:
            return

        if self.is_counterattack_turn(game_state):
            self.build_counterattack_supports(game_state)
            return

        if (
            best_scout_location is None
            or game_state.get_resource(MP) < game_state.type_cost(SCOUT)[MP]
        ):
            self.delete_all_supports(game_state)
            return

        self.keep_two_supports(game_state)

    def build_blocking_walls(self, game_state):
        if game_state.turn_number == 0:
            return
        if self.counterattack_ready_turn is not None and self.counterattack_ready_turn < game_state.turn_number:
            self.counterattack_ready_turn = None
            self.counterattack_ready_x = None

        base_r_locations = []
        wall_cost = game_state.type_cost(WALL)[SP]

        for enemy_location in self.get_wall_check_locations_center_out(game_state):
            wall_location = [enemy_location[0], enemy_location[1] - 1]
            should_block = self.should_block_enemy_front(game_state, enemy_location)

            if should_block:
                base_r_locations.append(wall_location)

        self.counterattack_x = self.choose_counterattack_x(base_r_locations)
        if self.counterattack_ready_x != self.counterattack_x:
            self.counterattack_ready_turn = None
            self.counterattack_ready_x = None
        if self.prepare_counterattack(game_state):
            return

        desired_walls = self.get_desired_wall_locations(base_r_locations, self.counterattack_x, game_state)
        walls_to_remove = []
        walls_to_spawn = []

        for wall_location in self.get_managed_wall_locations(game_state):
            wall = game_state.contains_stationary_unit(wall_location)
            if (
                wall
                and wall.player_index == 0
                and wall.unit_type == WALL
                and tuple(wall_location) not in desired_walls
            ):
                walls_to_remove.append(wall_location)

        for wall_location in self.get_spawn_locations_center_out(desired_walls):
            if not game_state.contains_stationary_unit(wall_location):
                walls_to_spawn.append(wall_location)

        total_spawn_cost = len(walls_to_spawn) * wall_cost
        if game_state.get_resource(SP) >= total_spawn_cost:
            for wall_location in walls_to_remove:
                game_state.attempt_remove(wall_location)
            for wall_location in walls_to_spawn:
                game_state.attempt_spawn(WALL, wall_location)

        for wall_location in self.get_counterattack_upgrade_locations(self.counterattack_x):
            if (
                self.counterattack_ready_x == self.counterattack_x
                and wall_location == [self.counterattack_x, WALL_CHECK_Y - 2]
            ):
                continue
            wall = game_state.contains_stationary_unit(wall_location)
            if (
                wall
                and wall.player_index == 0
                and wall.unit_type == WALL
                and not wall.upgraded
            ):
                game_state.attempt_upgrade(wall_location)

    def send_scouts(self, game_state, best_location):
        if game_state.get_resource(MP) < game_state.type_cost(SCOUT)[MP]:
            return

        if self.is_counterattack_turn(game_state):
            if best_location is not None:
                game_state.attempt_spawn(SCOUT, best_location, 1000)
            self.counterattack_ready_turn = None
            self.counterattack_ready_x = None
            return

        if best_location is None:
            return
        game_state.attempt_spawn(SCOUT, best_location, 1000)

    def build_counterattack_supports(self, game_state):
        built_or_upgraded = 0
        for location in SUPPORT_LOCATIONS:
            if built_or_upgraded >= 3:
                return

            structure = game_state.contains_stationary_unit(location)
            if not structure:
                if game_state.attempt_spawn(SUPPORT, location) > 0:
                    if game_state.attempt_upgrade(location) > 0:
                        built_or_upgraded += 1
                continue

            if structure.player_index != 0 or structure.unit_type != SUPPORT or structure.upgraded:
                continue

            if game_state.attempt_upgrade(location) > 0:
                built_or_upgraded += 1

    def keep_two_supports(self, game_state):
        keep_locations = SUPPORT_LOCATIONS[:2]
        for location in keep_locations:
            structure = game_state.contains_stationary_unit(location)
            if not structure:
                game_state.attempt_spawn(SUPPORT, location)

        for location in SUPPORT_LOCATIONS[2:]:
            structure = game_state.contains_stationary_unit(location)
            if structure and structure.player_index == 0 and structure.unit_type == SUPPORT:
                game_state.attempt_remove(location)

    def delete_all_supports(self, game_state):
        for location in SUPPORT_LOCATIONS:
            structure = game_state.contains_stationary_unit(location)
            if structure and structure.player_index == 0 and structure.unit_type == SUPPORT:
                game_state.attempt_remove(location)

    def is_counterattack_turn(self, game_state):
        return (
            self.counterattack_ready_turn == game_state.turn_number
            and self.counterattack_ready_x is not None
        )

    def build_rearguard_walls(self, game_state):
        if self.counterattack_prep_turn == game_state.turn_number:
            return

        for x in range(game_state.ARENA_SIZE):
            front_location = [x, WALL_CHECK_Y - 1]
            back_location = [x, WALL_CHECK_Y - 2]
            if not game_state.game_map.in_arena_bounds(front_location):
                continue
            if not game_state.game_map.in_arena_bounds(back_location):
                continue

            structure = game_state.contains_stationary_unit(front_location)
            if not structure or structure.player_index != 0:
                continue
            if structure.unit_type not in [WALL, TURRET]:
                continue
            if structure.health >= structure.max_health / 3:
                continue

            if game_state.attempt_spawn(WALL, back_location) > 0:
                game_state.attempt_upgrade(back_location)
                continue

            back_structure = game_state.contains_stationary_unit(back_location)
            if (
                back_structure
                and back_structure.player_index == 0
                and back_structure.unit_type == WALL
                and not back_structure.upgraded
            ):
                game_state.attempt_upgrade(back_location)

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

    def choose_counterattack_x(self, base_r_locations):
        all_r_xs = {location[0] for location in base_r_locations}
        candidate_xs = {
            location[0]
            for location in base_r_locations
            if location[0] < 10 or location[0] > 17
        }
        if self.counterattack_x in candidate_xs:
            return self.counterattack_x
        if not candidate_xs:
            return None

        def candidate_score(x):
            has_three = (x - 1 in all_r_xs) and (x + 1 in all_r_xs)
            distance_to_target = min(abs(x - 7), abs(x - 20))
            return (0 if has_three else 1, distance_to_target, x)

        return min(candidate_xs, key=candidate_score)

    def get_desired_wall_locations(self, base_r_locations, counterattack_x, game_state):
        desired_walls = {tuple(location) for location in base_r_locations}
        if counterattack_x is None:
            return desired_walls

        counterattack_location = (counterattack_x, WALL_CHECK_Y - 1)
        desired_walls.discard(counterattack_location)

        for location in self.get_counterattack_upgrade_locations(counterattack_x):
            if game_state.game_map.in_arena_bounds(location):
                desired_walls.add(tuple(location))

        if self.counterattack_ready_turn == game_state.turn_number and self.counterattack_ready_x == counterattack_x:
            desired_walls.discard((counterattack_x, WALL_CHECK_Y - 2))

        return desired_walls

    def get_counterattack_upgrade_locations(self, counterattack_x):
        if counterattack_x is None:
            return []
        return [
            [counterattack_x - 1, WALL_CHECK_Y - 1],
            [counterattack_x + 1, WALL_CHECK_Y - 1],
            [counterattack_x, WALL_CHECK_Y - 2],
        ]

    def get_managed_wall_locations(self, game_state):
        managed_locations = []
        for x in range(game_state.ARENA_SIZE):
            for y in [WALL_CHECK_Y - 1, WALL_CHECK_Y - 2]:
                location = [x, y]
                if game_state.game_map.in_arena_bounds(location):
                    managed_locations.append(location)
        return managed_locations

    def get_spawn_locations_center_out(self, desired_walls):
        locations = [[x, y] for x, y in desired_walls]
        center = (28 - 1) / 2
        return sorted(locations, key=lambda location: (abs(location[0] - center), location[0], -location[1]))

    def prepare_counterattack(self, game_state):
        if self.counterattack_x is None:
            return False
        if self.counterattack_ready_turn is not None:
            return False
        my_mp = game_state.get_resource(MP)
        if my_mp <= game_state.enemy_health * 1.1: # and my_mp < 12:
            return False

        wall_location = [self.counterattack_x, WALL_CHECK_Y - 2]
        wall = game_state.contains_stationary_unit(wall_location)
        if not wall or wall.player_index != 0 or wall.unit_type != WALL:
            return False

        if game_state.attempt_remove(wall_location) > 0:
            self.remove_all_non_support_structures(game_state)
            self.counterattack_prep_turn = game_state.turn_number
            self.counterattack_ready_turn = game_state.turn_number + 1
            self.counterattack_ready_x = self.counterattack_x
            return True
        return False

    def remove_all_non_support_structures(self, game_state):
        remove_locations = []
        for location in game_state.game_map:
            structure = game_state.contains_stationary_unit(location)
            if not structure or structure.player_index != 0:
                continue
            if structure.unit_type == SUPPORT:
                continue
            remove_locations.append(location)

        if remove_locations:
            game_state.attempt_remove(remove_locations)

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
                if next_location[1] <= 13:
                    continue
                if game_state.contains_stationary_unit(next_location):
                    continue
                visited.add(next_key)
                queue.append(next_key)

        return False


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
