from typing import Iterable
# Python doesn't have a way to have clean way to deal with circular references. As a result,
# we need to import the whole "game" module here and change type hints for the Game class into "game.Game".
import game


def sample_heuristic(state: "game.Game") -> int:
    """Uniform cost search heuristic (h(n) = 0 for all n)."""
    return 0


class Node:
    state: "game.Game"
    children: list["Node"]
    parent: "Node"

    def __init__(self, state: "game.Game", parent: "Node" = None, children: Iterable["Node"] = None) -> "Node":
        self.state = state
        self.children = children
        self.parent = parent

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
            child_node = Node(next_state, root)
            root.children.append(child_node)

        # stop if we reached max depth
        current_depth += 1
        if current_depth >= max_depth: return
    
        # generate children
        for child in root.children:
            Node.generate_node_tree(child, max_depth, current_depth)

    # TODO: implement these
    
    @staticmethod
    def run_minimax(
            root: "Node"
            # parameters
        ):
        pass

    @staticmethod
    def run_alphabeta(
            root: "Node"
            # parameters
        ):
        pass