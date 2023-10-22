import math
from typing import Iterable, ClassVar
from datetime import datetime
from utils import Coord, CoordPair, PlayerTeam
from units import UnitType
from output import log
# Python doesn't have a way to have clean way to deal with circular references. As a result,
# we need to import the whole "game" module here and change type hints for the Game class into "game.Game".
import game

# For our minimax/alpha-beta heuristics, MAX is the Defender and MIN is the attacker.
def heuristic_e0(state: "game.Game") -> int:
    return heuristic_e0_army_score(state, PlayerTeam.Defender) - heuristic_e0_army_score(state, PlayerTeam.Attacker)

def heuristic_e0_army_score(state: "game.Game", player: PlayerTeam):
    score = 0
    for (_,unit) in state.player_units(player):
        if unit.type == UnitType.AI: # AI is worth 9999
            score += 9999
        else: # every other unit type is worth 3
            score += 3
    return score


def heuristic_e1(state: "game.Game") -> int:
    total_hp = 0

    # REMINDER ON HOW HEURISTICS WORK: Heuristics are always one-sided, they always evaluate the "advantageousness" of
    # the game state from the same player's perspective, regardless of who the current player is.
    # In our case, we evaluate the game state from the perspective of the defender (but it could also be the other way around).
    # This is why we have MAX and MIN. MAX (defender) tries to maximize the advantageousness of the game state from the defender's perspective (itself),
    # while MIN (attacker) tries to minimize it (leading it to be more attacker-advantageous).
    # If we have a heuristic that alternates between player perspectives, the minimax algorithm (and subsequently alpha-beta) simply don't work as expected.
    # As a result, I'm commenting out the code for game state evaluation from the Attacker's perspective, but keeping it so we can use it for reference later.
    # Now without it, the Attacker AI seems to want to kill the Defender's Techs much more.

    # We can still have multiple different heuristics, but all must compute the advantageousness of the game from the MAX player's perspective.

    # # # if state.next_player == PlayerTeam.Attacker: # Tally how advantageous the state is for Attacker.
    # # #     enemy_ai_coord = None
    # # #     for (coord,unit) in state.player_units(PlayerTeam.Defender):
    # # #         if unit.type == UnitType.AI:
    # # #             total_hp += unit.health*10 # That enemy AI MUST die!
    # # #             enemy_ai_coord = coord
    # # #         else:
    # # #             total_hp += unit.health # But your enemy in general being alive is bad.
    # # #     if enemy_ai_coord == None:
    # # #         return -9999 # Winning the game. Not bad at all.
    # # #     for (coord,unit) in state.player_units(PlayerTeam.Attacker):
    # # #         if unit.type == UnitType.Virus:
    # # #             total_hp -= unit.health*(10 - Coord.get_manhattan_distance(coord, enemy_ai_coord)) # When viruses get closer to that enemy AI, that's good.
    # # #         else:
    # # #             total_hp -= unit.health*2 # Don't get caught up in combat, though, focus on rushing that AI.
    # # # else: # Tally how advantageous the state is for Defender.

    my_ai_coord = None
    for (coord,unit) in state.player_units(PlayerTeam.Defender):
        if unit.type == UnitType.AI:
            total_hp -= unit.health*10 # Your AI being alive is VERY important.
            my_ai_coord = coord
        else:
            total_hp -= unit.health # Your army being alive in general is kind of important.
    if my_ai_coord == None:
        return 9999 # Losing the game is REALLY BAD.
    for (coord,unit) in state.player_units(PlayerTeam.Attacker):
        if unit.type == UnitType.Virus:
            total_hp += unit.health*(10 - Coord.get_manhattan_distance(coord, my_ai_coord)) # Viruses are bad. Viruses close to your AI is REALLY BAD.
        elif unit.type == UnitType.AI:
            total_hp += unit.health*5 # The attacker should be protecting its AI too. And the defender might be interested in killing it over just stalling.
        else:
            total_hp += unit.health*2 # Your enemy being alive in general is bad.
    return total_hp

# e1, but also assign score based on how many moves each player can do.
# I threw this together super quickly, feel free to change.
def heuristic_e2(state: "game.Game") -> int:
    moves_weight = 1 # change this as needed
    return heuristic_e1(state) + moves_weight * (len(state.move_candidates(PlayerTeam.Defender)) - len(state.move_candidates(PlayerTeam.Defender)))

class OutOfTimeException(Exception):
    pass

class Node:
    value: int | None # the estimated value of this game state for the maximizing player
    state: "game.Game" # the game state this node represents
    parent: "Node" # the game state that preceded this one
    action: CoordPair # what action was performed from the parent state to reach this one
    children: list["Node"] # the list of possible next game states from this one

    def __init__(self, state: "game.Game", from_parent: CoordPair = None, parent: "Node" = None, children: Iterable["Node"] = None) -> "Node":
        self.state = state
        self.parent = parent
        self.action = from_parent
        self.children = children
        self.value = None

    def is_root(self: "Node") -> bool:
        return self.parent is None
    
    def is_leaf(self: "Node") -> bool: 
        return self.children is None or len(self.children) == 0

    @staticmethod
    def generate_node_tree(
            root: "Node",
            current_depth: int = 0
        ):
        root.children = list()

        # generate the possible substates, evaluate them
        for next_state in root.state.next_state_candidates():
            child_node = Node(*next_state, root) # * unpacks next_state tuple into Game and Coordpair arguments
            root.children.append(child_node)
        return root.children
    

    #region UTILITY

    @staticmethod
    def get_max_node(list: list["Node"]) -> "Node":
        """Retrieves the node with the largest value from a list."""
        max_value = -math.inf
        max_node = None

        for node in list:
            # ignore nodes without a value
            if node.value == None: continue
            # if node has larger value, replace stored one
            if node.value > max_value:
                max_value = node.value
                max_node = node
        
        return max_node
    
    @staticmethod
    def get_min_node(list: list["Node"]) -> "Node":
        """Retrieves the node with the smallest value from a list."""
        min_value = math.inf
        min_node = None

        for node in list:
            # ignore nodes without a value
            if node.value == None: continue
            # if node has smaller value, replace stored one
            if node.value < min_value:
                min_value = node.value
                min_node = node
        
        return min_node

    @staticmethod
    def take_best_next_state(root: "Node", is_maximizing: bool, error_str: str = None) -> "Node":
        # select the best next state, the node with largest/smallest value depending on MAX or MIN player.
        best_next_state = Node.get_max_node(root.children) if is_maximizing else Node.get_min_node(root.children)

        # if the result is None, then the root doesn't have any child with a heuristic value
        if best_next_state is None: 
            log(error_str)
            next_state, move, _ = root.state.random_next_state()
            return Node(next_state, move, root)
        return best_next_state
    
    @staticmethod
    def out_of_time_check(root: "Node", start_time: datetime):
        """Raises an OutOfTimeException if time elapsed exceeds the game's max search time."""
        if start_time is None: 
            return
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time >= root.state.options.max_time:
            raise OutOfTimeException("Ran out of time (%f)" % elapsed_time)
        else:
            return elapsed_time

    #endregion


    @staticmethod
    def run_minimax(root: "Node", is_maximizing: bool) -> "Node":
        """Runs minimax over a node tree and retreives the best next state."""
        # get the current time to keep track of how long minimax has been running
        start_time = datetime.now()

        # try to populate the tree with estimated node values
        try: 
            Node.minimax_propagate_values_up(root, is_maximizing, start_time)
        # if we run out of time, return the best immediate node that we had time to evaluate
        except OutOfTimeException:
            return Node.take_best_next_state(root, is_maximizing, "Minimax did not have time to evaluate any of the next actions. Returned a random move instead.")
        # if minimax had time to complete, return the best state
        return Node.take_best_next_state(root, is_maximizing, "The game state does not seem to have any possible successors. Attempting to return a random move...")


    @staticmethod 
    def minimax_propagate_values_up(
            root: "Node",
            is_maximizing: bool,
            start_time: datetime = None
        ) -> int:

        # check if we're out of time
        Node.out_of_time_check(root, start_time)

        # if the node is a leaf, get its estimated value (compute e(n) if needed)
        if root.is_leaf(): 
            if root.value == None:
                root.value = heuristic_e1(root.state)
            return root.value
        
        # otherwise, propagate the call down the tree and select max/min once values are obtained
        else:
            invert_maximizing = not is_maximizing # compute only once
            children_values = [ Node.minimax_propagate_values_up(node, invert_maximizing, start_time) for node in root.children ]
            
            # find the value of this node from its children (whether it's at MAX or MIN level) and return it
            root.value = max(children_values) if is_maximizing else min(children_values)
            return root.value


    @staticmethod
    def run_alphabeta(root: "Node", is_maximizing: bool) -> "Node":
        """Runs alpha-beta over a node tree and retreives the best next state."""
        # get the current time to keep track of how long minimax has been running
        start_time = datetime.now()

        # try to populate the tree with estimated node values
        try:
            Node.alphabeta_propagate_values_up(root, -math.inf, +math.inf, is_maximizing, start_time)
    
        # if we run out of time, return the best immediate node that we had time to evaluate
        except OutOfTimeException:
            return Node.take_best_next_state(root, is_maximizing, "Alpha-Beta did not have time to evaluate any of the next actions. Returned a random move instead.")
        # if alpha-beta had time to complete, return the best state
        return Node.take_best_next_state(root, is_maximizing, "The game state does not seem to have any possible successors. Attempting to return a random move...")



    @staticmethod
    def alphabeta_propagate_values_up(
            root: "Node",
            alpha: int,
            beta: int,
            is_maximizing: bool,
            start_time: datetime
        ) -> int:

        # check if we're out of time
        Node.out_of_time_check(root, start_time)

        if root.is_leaf():
            if root.value == None:
                root.value = heuristic_e1(root.state)
            return root.value

        if is_maximizing:
            best = -math.inf
            invert_maximizing = not is_maximizing # taking this outside the loop as to only compute it once
            for child in root.children:
                score = Node.alphabeta_propagate_values_up(child, alpha, beta, invert_maximizing, start_time)
                best = max(best,score)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            root.value = best
            return root.value
        else:
            best = math.inf
            invert_maximizing = not is_maximizing # taking this outside the loop as to only compute it once
            for child in root.children:
                score = Node.alphabeta_propagate_values_up(child, alpha, beta, invert_maximizing, start_time)
                best = min(best,score)
                beta = min(beta, best)
                if beta <= alpha:
                    break
            root.value = best
            return root.value
