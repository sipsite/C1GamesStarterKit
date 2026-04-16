import gamelib
import random
import math
import warnings
import os
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

# constants
c1 = 1 # start building at c1 round
c2 = 0.4 # proportion of support among "turrent and support"
c3 = 1 # upgrade cost adds up to proportion c3
cc1 = 0.4
cc2 = 30
cc3 = 0.1


PRIORITY_1_TURRETS = [
    [8, 9], [19, 9],
]

PRIORITY_2_WALLS = [
    [0, 13], [1, 12], [2, 11], [3, 10], [4, 9], [5, 8], [27, 13], [26, 13],
]

PRIORITY_3_WALLS = [
    [14, 2], [15, 3], [16, 4], [17, 5], [18, 6], [19, 7],
    [20, 8], [22, 10], [23, 11], [24, 12], [25, 13],
]

PRIORITY_4_WALLS = [
    [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], [11, 2], [12, 2], [13, 2],
]

PRIORITY_5_FIXED_TURRETS = [
    [8, 10], [13, 9],
]

PRIORITY_5_TURRETS = [
    [21, 10], [22, 11], [19, 8], [18, 9], [21, 11], [21, 12], [17, 10],
]

PRIORITY_5_SUPPORTS = [
    [14, 3], [13, 3], [12, 3], [12, 4], [13, 4], [14, 4],
]

PRIORITY_6_TURRETS = [
    [2, 13], [3, 13], [2, 12], [24, 13], [23, 13],
]

UPGRADE_PRIORITY_1_WALLS = [
    [0, 13], [1, 12], [27, 13], [26, 13],
]

UPGRADE_PRIORITY_2_TURRETS = [
    [2, 13], [3, 13], [23, 13], [24, 13],
]

UPGRADE_PRIORITY_3_TURRETS = [
    [8, 9], [19, 9],
    [8, 10], [13, 9],
]

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
        self.log_path = os.path.join(os.path.dirname(__file__), "f1_debug.log")

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
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
        # This is a good place to do initial setup
        self.scored_on_locations = []
        with open(self.log_path, "w", encoding="utf-8") as log_file:
            log_file.write("f1 debug log\n")

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        # Old starter algo behavior kept as comments for reference only.
        # game_state.attempt_spawn(DEMOLISHER, [24, 10], 3)
        # self.starter_strategy(game_state)

        self.build_image_layout(game_state)
        self.execute_military_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def build_image_layout(self, game_state):
        if game_state.turn_number < c1:
            return

        total_sp = game_state.get_resource(SP)
        layout_was_complete = self.is_building_complete(game_state)
        building_budget = total_sp if not layout_was_complete else total_sp * (1 - c3)

        self.run_build_priorities(game_state, building_budget)

        if self.is_building_complete(game_state):
            upgrade_budget = min(total_sp * c3, game_state.get_resource(SP))
            self.run_upgrade_priorities(game_state, upgrade_budget)

    def execute_military_strategy(self, game_state):
        u1 = self.f1(game_state, [12, 1])
        u2 = self.f1(game_state, [16, 2])
        best_location = [12, 1] if u1 <= u2 else [16, 2]
        best_attack = min(u1, u2)
        self.log_line(
            "f1, turn={}, u1(12,1)={}, u2(16,2)={}, chosen={}, u={}".format(
                game_state.turn_number,
                u1,
                u2,
                best_location,
                best_attack,
            )
        )

        if game_state.turn_number <= 3:
            game_state.attempt_spawn(INTERCEPTOR, [7, 6], 1)
            game_state.attempt_spawn(INTERCEPTOR, [20, 6], 1)
            return

        enemy_mp = game_state.get_resource(MP, 1)
        my_mp = game_state.get_resource(MP)
        enemy_health = game_state.enemy_health

        interceptor_count = int(enemy_mp // 10)
        if interceptor_count > 0:
            game_state.attempt_spawn(INTERCEPTOR, [19, 5], interceptor_count)

        attack_probability = self.w1(my_mp - best_attack * cc1, 13)
        if random.random() >= attack_probability:
            return

        if enemy_health * 1.1 < my_mp and best_attack < cc2:
            scout_probability = self.w1(my_mp - cc1 * best_attack, enemy_health)
            if random.random() < scout_probability:
                self.send_all_of_type(game_state, SCOUT, best_location)
                return

        if my_mp <= 15:
            return

        fallback_attack_probability = self.w1(
            my_mp - best_attack * cc1,
            10 + math.sqrt(max(game_state.turn_number, 1)),
        )
        if random.random() >= fallback_attack_probability:
            return

        demolisher_probability = self.w1(best_attack * cc3, 1)
        if random.random() < demolisher_probability:
            self.send_all_of_type(game_state, DEMOLISHER, best_location)
        else:
            self.send_all_of_type(game_state, SCOUT, best_location)

    def spawn_in_order(self, game_state, unit_type, locations):
        for location in locations:
            if game_state.contains_stationary_unit(location):
                continue
            spawned = game_state.attempt_spawn(unit_type, location)
            if spawned == 0:
                return False
        return True

    def spawn_random_mix(self, game_state, support_locations, turret_locations):
        while True:
            remaining_supports = self.get_remaining_locations(game_state, support_locations)
            remaining_turrets = self.get_remaining_locations(game_state, turret_locations)

            if not remaining_supports and not remaining_turrets:
                return True

            build_support = random.random() < c2
            if build_support:
                if self.spawn_next(game_state, SUPPORT, remaining_supports):
                    continue
                if self.spawn_next(game_state, TURRET, remaining_turrets):
                    continue
            else:
                if self.spawn_next(game_state, TURRET, remaining_turrets):
                    continue
                if self.spawn_next(game_state, SUPPORT, remaining_supports):
                    continue

            return False

    def spawn_next(self, game_state, unit_type, locations):
        for location in locations:
            spawned = game_state.attempt_spawn(unit_type, location)
            if spawned > 0:
                return True
        return False

    def get_remaining_locations(self, game_state, locations):
        return [
            location for location in locations
            if not game_state.contains_stationary_unit(location)
        ]

    def run_build_priorities(self, game_state, budget):
        budget_state = self.make_budget_state(game_state, budget)
        self.spawn_in_order_with_budget(game_state, TURRET, PRIORITY_1_TURRETS, budget_state)
        self.spawn_in_order_with_budget(game_state, WALL, PRIORITY_2_WALLS, budget_state)
        self.spawn_in_order_with_budget(game_state, WALL, PRIORITY_3_WALLS, budget_state)
        self.spawn_in_order_with_budget(game_state, WALL, PRIORITY_4_WALLS, budget_state)
        self.spawn_in_order_with_budget(game_state, TURRET, PRIORITY_5_FIXED_TURRETS, budget_state)
        self.spawn_random_mix_with_budget(
            game_state,
            PRIORITY_5_SUPPORTS,
            PRIORITY_5_TURRETS,
            budget_state,
        )
        self.spawn_in_order_with_budget(game_state, TURRET, PRIORITY_6_TURRETS, budget_state)

    def run_upgrade_priorities(self, game_state, budget):
        budget_state = self.make_budget_state(game_state, budget)
        self.upgrade_in_order_with_budget(game_state, UPGRADE_PRIORITY_1_WALLS, budget_state)
        self.upgrade_in_order_with_budget(game_state, UPGRADE_PRIORITY_2_TURRETS, budget_state)
        self.upgrade_in_order_with_budget(game_state, UPGRADE_PRIORITY_3_TURRETS, budget_state)
        self.upgrade_random_mix_with_budget(
            game_state,
            PRIORITY_5_SUPPORTS,
            PRIORITY_5_TURRETS,
            budget_state,
        )
        self.upgrade_in_order_with_budget(game_state, PRIORITY_6_TURRETS, budget_state)

    def is_building_complete(self, game_state):
        return (
            self.locations_match_type(game_state, WALL, PRIORITY_2_WALLS)
            and self.locations_match_type(game_state, WALL, PRIORITY_3_WALLS)
            and self.locations_match_type(game_state, WALL, PRIORITY_4_WALLS)
            and self.locations_match_type(game_state, TURRET, PRIORITY_1_TURRETS)
            and self.locations_match_type(game_state, TURRET, PRIORITY_5_FIXED_TURRETS)
            and self.locations_match_type(game_state, TURRET, PRIORITY_5_TURRETS)
            and self.locations_match_type(game_state, SUPPORT, PRIORITY_5_SUPPORTS)
            and self.locations_match_type(game_state, TURRET, PRIORITY_6_TURRETS)
        )

    def locations_match_type(self, game_state, unit_type, locations):
        for location in locations:
            structure = self.get_structure_at(game_state, location)
            if structure is None or structure.unit_type != unit_type:
                return False
        return True

    def get_structure_at(self, game_state, location):
        structure = game_state.contains_stationary_unit(location)
        return structure if structure else None

    def make_budget_state(self, game_state, budget):
        return {
            "start_sp": game_state.get_resource(SP),
            "budget": max(float(budget), 0.0),
        }

    def spent_budget(self, game_state, budget_state):
        return budget_state["start_sp"] - game_state.get_resource(SP)

    def can_spend_sp(self, game_state, budget_state, cost):
        return self.spent_budget(game_state, budget_state) + cost <= budget_state["budget"] + 1e-9

    def spawn_in_order_with_budget(self, game_state, unit_type, locations, budget_state):
        for location in locations:
            structure = self.get_structure_at(game_state, location)
            if structure is not None:
                continue
            cost = game_state.type_cost(unit_type)[SP]
            if not self.can_spend_sp(game_state, budget_state, cost):
                return False
            if game_state.attempt_spawn(unit_type, location) == 0:
                return False
        return True

    def spawn_random_mix_with_budget(self, game_state, support_locations, turret_locations, budget_state):
        while True:
            remaining_supports = self.get_remaining_type_locations(game_state, SUPPORT, support_locations)
            remaining_turrets = self.get_remaining_type_locations(game_state, TURRET, turret_locations)

            if not remaining_supports and not remaining_turrets:
                return True

            build_support = random.random() < c2
            if build_support:
                if self.spawn_next_with_budget(game_state, SUPPORT, remaining_supports, budget_state):
                    continue
                if self.spawn_next_with_budget(game_state, TURRET, remaining_turrets, budget_state):
                    continue
            else:
                if self.spawn_next_with_budget(game_state, TURRET, remaining_turrets, budget_state):
                    continue
                if self.spawn_next_with_budget(game_state, SUPPORT, remaining_supports, budget_state):
                    continue

            return False

    def spawn_next_with_budget(self, game_state, unit_type, locations, budget_state):
        cost = game_state.type_cost(unit_type)[SP]
        if not self.can_spend_sp(game_state, budget_state, cost):
            return False
        for location in locations:
            spawned = game_state.attempt_spawn(unit_type, location)
            if spawned > 0:
                return True
        return False

    def get_remaining_type_locations(self, game_state, unit_type, locations):
        remaining = []
        for location in locations:
            structure = self.get_structure_at(game_state, location)
            if structure is None:
                remaining.append(location)
            elif structure.unit_type != unit_type:
                remaining.append(location)
        return remaining

    def upgrade_in_order_with_budget(self, game_state, locations, budget_state):
        for location in locations:
            structure = self.get_structure_at(game_state, location)
            if structure is None or structure.upgraded:
                continue
            cost = game_state.type_cost(structure.unit_type, True)[SP]
            if not self.can_spend_sp(game_state, budget_state, cost):
                return False
            if game_state.attempt_upgrade(location) == 0:
                return False
        return True

    def upgrade_random_mix_with_budget(self, game_state, support_locations, turret_locations, budget_state):
        while True:
            remaining_supports = self.get_unupgraded_locations(game_state, support_locations)
            remaining_turrets = self.get_unupgraded_locations(game_state, turret_locations)

            if not remaining_supports and not remaining_turrets:
                return True

            build_support = random.random() < c2
            if build_support:
                if self.upgrade_next_with_budget(game_state, remaining_supports, budget_state):
                    continue
                if self.upgrade_next_with_budget(game_state, remaining_turrets, budget_state):
                    continue
            else:
                if self.upgrade_next_with_budget(game_state, remaining_turrets, budget_state):
                    continue
                if self.upgrade_next_with_budget(game_state, remaining_supports, budget_state):
                    continue

            return False

    def get_unupgraded_locations(self, game_state, locations):
        remaining = []
        for location in locations:
            structure = self.get_structure_at(game_state, location)
            if structure is not None and not structure.upgraded:
                remaining.append(location)
        return remaining

    def upgrade_next_with_budget(self, game_state, locations, budget_state):
        for location in locations:
            structure = self.get_structure_at(game_state, location)
            if structure is None or structure.upgraded:
                continue
            cost = game_state.type_cost(structure.unit_type, True)[SP]
            if not self.can_spend_sp(game_state, budget_state, cost):
                return False
            if game_state.attempt_upgrade(location) > 0:
                return True
        return False

    def choose_attack_path(self, game_state, locations):
        best_location = locations[0]
        best_attack = self.f1(game_state, best_location)
        for location in locations[1:]:
            attack = self.f1(game_state, location)
            if attack < best_attack:
                best_location = location
                best_attack = attack
        return best_location, best_attack

    def f1(self, game_state, location):
        return self.estimate_path_attack(game_state, location)

    def estimate_path_attack(self, game_state, location):
        path = game_state.find_path_to_edge(location)
        if not path:
            return float("inf")

        pressure = 0
        for path_location in path:
            attackers = game_state.get_attackers(path_location, 0)
            pressure += len(attackers)
        return pressure

    def w1(self, x, x0):
        x0 = max(float(x0), 0.1)
        return math.tanh((2 * x / x0) - 1) / 2 + 0.5

    def send_all_of_type(self, game_state, unit_type, location):
        affordable = game_state.number_affordable(unit_type)
        if affordable <= 0:
            return 0
        return game_state.attempt_spawn(unit_type, location, affordable)

    def log_line(self, message):
        with open(self.log_path, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_interceptors(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our demolishers to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.demolisher_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

                # Only spawn Scouts every other turn
                # Sending more at once is better since attacks can only hit a single scout at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    scout_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
                    game_state.attempt_spawn(SCOUT, best_location, 1000)

                # Lastly, if we have spare SP, let's build some supports
                support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(SUPPORT, support_locations)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        
        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[8, 12], [19, 12]]
        game_state.attempt_spawn(WALL, wall_locations)
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(wall_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
