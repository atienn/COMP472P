from typing import Iterable
from utils import CoordPair, PlayerTeam
import math
# Python doesn't have a way to have clean way to deal with circular references. As a result,
# we need to import the whole "game" module here and change type hints for the Game class into "game.Game".
import game

# For our minimax/alpha-beta heuristics, MAX is the Defender and MIN is the attacker.
# Cheap test heuristic, we'll get more creative later, just grabs all the hp from the current player and tries to avoid damage
def sample_heuristic(state: "game.Game") -> int:
    total_hp = 0

    # Tally how advantageous the state is for Defender.
    for (coord,unit) in state.player_units(PlayerTeam.Defender):
        total_hp += unit.health
    
    # There is currently a bug with how the heuristic evaluation. 
    # For it to work as expected when AI is defender the score must be negated (return -total_hp).
    # For it to work as expected when AI is attacker the score needs to be left as-is (return total_hp).
    return total_hp


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
            max_depth: int, 
            current_depth: int = 0
        ):
        root.children = list()

        # generate the possible substates, evaluate them
        for next_state in root.state.next_state_candidates():
            child_node = Node(*next_state, root) # * unpacks next_state tuple into Game and Coordpair arguments
            root.children.append(child_node)

        # stop if we reached max depth
        current_depth += 1

        if current_depth >= max_depth: return
        # generate children
        for child in root.children:
            Node.generate_node_tree(child, max_depth, current_depth)
    

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

    #endregion


    @staticmethod
    def run_minimax(root: "Node", is_maximizing: bool) -> "Node":
        """Runs minimax over a node tree and retreives the best next state."""
        # populate the tree with estimated node values
        Node.minimax_propagate_values_up(root, is_maximizing)
        # select the best next state
        best_next_state = Node.get_max_node(root.children) if is_maximizing else Node.get_min_node(root.children)
        return best_next_state


    @staticmethod 
    def minimax_propagate_values_up(root: "Node", is_maximizing: bool) -> int:
        # if the node is a leaf, get its estimated value (compute e(n) if needed)
        if root.is_leaf(): 
            if root.value == None:
                root.value = sample_heuristic(root.state)
            return root.value
        
        # otherwise, propagate the call down the tree and select max/min once values are obtained
        else:
            invert_maximizing = not is_maximizing # compute only once
            children_values = [ Node.minimax_propagate_values_up(node, invert_maximizing) for node in root.children ]
            
            # find the value of this node from its children (whether it's at MAX or MIN level) and return it
            root.value = max(children_values) if is_maximizing else min(children_values)
            return root.value


    # TODO: implement this
    @staticmethod
    def run_alphabeta(
            root: "Node"
            # parameters
        ) -> "Node":
        pass