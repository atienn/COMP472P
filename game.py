from __future__ import annotations
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, Iterable
import random
import requests

from output import log
from utils import Coord, CoordPair, PlayerTeam
from units import UnitAction, UnitType, Unit
from ai_logic import Node, OutOfTimeException


class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3

##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth : int | None = 4
    max_time : float | None = 5.0
    game_type : GameType = GameType.AttackerVsDefender
    alpha_beta : bool = True
    max_turns : int | None = 100
    randomize_moves : bool = True
    broker : str | None = None
    heuristic_choice: int = 1


##############################################################################################################


@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth : dict[int,int] = field(default_factory=dict)
    total_seconds: float = 0.0


##############################################################################################################


@dataclass(slots=True)
class Game:

    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: PlayerTeam = PlayerTeam.Attacker
    turns_played : int = 0
    cumulative_evals : int = 0
    cumulative_evals_per_depth = {}
    average_branch_factor : int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True

    #region WELCOME

    def gamemode_name_string(self, type) -> str:
        game_names = {
            GameType.AttackerVsDefender : "Human (A) vs. Human (D)",
            GameType.AttackerVsComp : "Human (A) vs. Computer (D)",
            GameType.CompVsDefender : "Computer (A) vs. Human (D)",
            GameType.CompVsComp : "Computer (A) vs. Computer (D)",
        }
        return game_names[type]

    def next_player_is_human(self) -> bool:
        return self.options.game_type == GameType.AttackerVsDefender or (self.options.game_type == GameType.AttackerVsComp and self.next_player == PlayerTeam.Attacker) or (self.options.game_type == GameType.CompVsDefender and self.next_player == PlayerTeam.Defender)

    #endregion

    #region BOARD

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=PlayerTeam.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=PlayerTeam.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=PlayerTeam.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=PlayerTeam.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=PlayerTeam.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=PlayerTeam.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=PlayerTeam.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=PlayerTeam.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=PlayerTeam.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=PlayerTeam.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=PlayerTeam.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=PlayerTeam.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_cell_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def is_coord_valid(self, coord: Coord) -> bool:
        """Check if a Coord is valid within the board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    #endregion

    #region UNIT BEHAVIOR

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_coord_valid(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_coord_valid(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is None: return
        if unit.is_alive() == False:
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == PlayerTeam.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)
    
    def destroy(self, coord: Coord): 
        target = self.get(coord)
        if target is not None:
            target.health = -1 # kill unit outright
            self.remove_dead(coord)

    def explode(self, blast_point: Coord):
        for x in range(3):
            for y in range(3):
                exploding_tile = Coord(blast_point.row-1+x,blast_point.col-1+y)
                self.mod_health(exploding_tile, -2)


    # Swapped to using Enums instead of hard-coded string values simply because it's less likely to result
    # in errors or unexpected behavior (reminder that things like "false" evaluates to boolean False in
    # python while other strings typically evaluate as True)
    def determine_action(self, coords : CoordPair) -> Tuple[UnitAction, str]:
        """Determines the action expressed by a CoordPair."""
        # Check that coordinates are valid.
        if not self.is_coord_valid(coords.src) or not self.is_coord_valid(coords.dst):
            return (UnitAction.Invalid, "Specified coordinate does not exist!")
        
        # The unit that will do something this turn.
        actingUnit = self.get(coords.src) 
        if actingUnit is None:
            return (UnitAction.Invalid, "Coordinate does not contain a unit!")
        if actingUnit.player != self.next_player:
            return (UnitAction.Invalid, "Unit does not belong to this player!")
        if coords.are_equal():
            return (UnitAction.Kaboom, "Detonate")
        if not coords.are_adjacent_cross():
            return (UnitAction.Invalid, "Units can only move in cardinal directions!")
        
        # The unit (if any) that will be acted upon (attacked/repaired).
        otherUnit = self.get(coords.dst)
        
        if otherUnit is None:
            # If unit doesn't have free movement, restrictions apply
            if not actingUnit.can_move_freely():
                # Check if the destination isn't closer to home base
                deltaX, deltaY = coords.delta()
                if actingUnit.player == PlayerTeam.Defender and (deltaX < 0 or deltaY < 0):
                    return (UnitAction.Invalid, "Non-tech defender unit cannot move towards its base.")
                elif actingUnit.player == PlayerTeam.Attacker and (deltaX > 0 or deltaY > 0):
                    return (UnitAction.Invalid, "Non-virus attacker unit cannot move towards its base.")

                # Check if the unit isn't "engaged" with enemy unit
                for adjacentTile in coords.src.iter_adjacent():
                    adjacentUnit = self.get(adjacentTile)
                    if adjacentUnit is not None and actingUnit.player != adjacentUnit.player:
                        return (UnitAction.Invalid, "Unit cannot move; it is engaged with another unit.")

            return (UnitAction.Move, "Move") # With guard condition above, unit can only move one space.
        
        if otherUnit.player != self.next_player:
            return (UnitAction.Attack, "Attack")
        if otherUnit.player == self.next_player and Unit.repair_amount(actingUnit, otherUnit) > 0:
            return (UnitAction.Repair, "Repair")
        
        # default case
        return (UnitAction.Invalid, "Action was not recognized.")

    def attempt_move(self, coords: CoordPair):
        action, descriptor = self.determine_action(coords)
        # log(descriptor)
        return self.perform_move(coords, action)

    def perform_move(self, coords: CoordPair, action: UnitAction) -> Tuple[bool,str]:
        """Performs an action expressed by a CoordPair."""
        actingUnit = self.get(coords.src)

        if action == UnitAction.Move:
            self.set(coords.dst, actingUnit)
            self.set(coords.src, None)
            return (True, f"{self.next_player.name}'s {actingUnit.unit_name_string()} moves from {coords.src.to_string()} to {coords.dst.to_string()}.\n")
        if action == UnitAction.Kaboom:
            exploder = self.get(coords.dst)
            self.destroy(coords.dst)
            self.explode(coords.dst)
            return (True, f"{self.next_player.name}'s {exploder.unit_name_string()} at {coords.dst.to_string()} explodes in a fiery blast!! (2 damage to all nearby units)\n")

        otherUnit = self.get(coords.dst)

        if action == UnitAction.Attack:
            # both units should always deal the same damage to one another, 
            # but do damage the calculation both ways just in case
            lost_amount_atk = actingUnit.damage_amount(otherUnit)
            lost_amount_def = otherUnit.damage_amount(actingUnit)
            self.mod_health(coords.dst, -actingUnit.damage_amount(otherUnit))
            self.mod_health(coords.src, -otherUnit.damage_amount(actingUnit))
            return (True,f"{self.next_player.name}'s {actingUnit.unit_name_string()} at {coords.src.to_string()} attacks the {otherUnit.unit_name_string()} at {coords.dst.to_string()}! ({lost_amount_atk} damage dealt, {lost_amount_def} damage taken as retaliation)\n")
        if action == UnitAction.Repair:
            health_value = actingUnit.repair_amount(otherUnit)
            otherUnit.mod_health(health_value)
            return (True,f"{self.next_player.name}'s {actingUnit.unit_name_string()} at {coords.src.to_string()} repairs their {otherUnit.unit_name_string()} ally at {coords.dst.to_string()}! ({health_value} damage repaired)\n")

        return (False, "invalid move")

    #endregion

    #region GAME LIFECYCLE

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    # this method is unused
    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> PlayerTeam | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return PlayerTeam.Defender
        if self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return PlayerTeam.Attacker
        return PlayerTeam.Defender

    #endregion

    #region HUMAN TURN

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_coord_valid(coords.src) and self.is_coord_valid(coords.dst):
                return coords
            else:
                log('Invalid coordinates! Try again.')
    
    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            log("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.attempt_move(mv)
                    log(f"Broker {self.next_player.name}: ",end='')
                    log(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success,result) = self.attempt_move(mv)
                if success:
                    log(f"Player {self.next_player.name}: ",end='')
                    log(result)
                    self.next_turn()
                    self.is_finished()
                    break
                else:
                    log(result)
                    log("The move is not valid! Try again.")

    #endregion

    #region COMPUTER TURN

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is None: return None
        (success, result) = self.attempt_move(mv)
        if success:
            log(f"Computer {self.next_player.name}: ",end='')
            log(result)
            self.next_turn()
        else:
            log("ERROR: AI suggesting invalid move!")
            log(result)
        return mv

    def player_units(self, player: PlayerTeam) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)

    def move_candidates(self, player) -> Iterable[Tuple[CoordPair, UnitAction]]:
        """Generate valid move candidates for the next player."""
        # we clone the coordpairs as not to have units getting moved by accident
        move = CoordPair()
        for (src,_) in self.player_units(player):
            move.src = src

            # Check if moving to each adjacent unit is a valid move.
            for dst in src.iter_adjacent():
                move.dst = dst
                # if the move is valid return it
                action, _ = self.determine_action(move)
                if action != UnitAction.Invalid:
                    yield (move.clone(), action)

            # Lastly, check self-destruct (same source and destination coords)
            # Should always a valid move, check is there just in case.
            move.dst = src
            action, _ = self.determine_action(move)
            if action != UnitAction.Invalid:
                yield (move.clone(), action)
                
    
    def next_state_candidates(self) -> Iterable[Tuple[Game, CoordPair]]:
        other_player = PlayerTeam.next(self.next_player)
        for move, action in self.move_candidates(self.next_player):
            state = self.clone()
            state.next_player = other_player
            state.perform_move(move, action) # unpack tuple into CoordPair and UnitAction
            yield (state, move)


    def search_for_best_move(self) -> Tuple[int, CoordPair | None, float ]: 
        # clone the game state, store it into a node
        root = Node(self.clone())

        next_nodes_to_search = [root]
        nodes_queued = []
        current_max_depth = 1 # Start at the not very ambitious min depth
        best_move = None

        tree_size = 1
        leaf_nodes_num = 0
        time_cutoff = 0.85
        if self.options.heuristic_choice == 2:
            time_cutoff = 0.5

        start_time = datetime.now()
        is_maximizing = self.next_player == PlayerTeam.Defender # defender is MAX

        try:
            while Node.out_of_time_check(root, start_time) < self.options.max_time*time_cutoff: # While at least 10% of the time limit remains...
                for node in next_nodes_to_search: # Give all leaf nodes new children.
                    # generate the node tree under the node representing the current game state
                    new_nodes = Node.generate_successors(node)
                    nodes_queued += new_nodes
                    leaf_nodes_num += len(new_nodes) - 1
                    tree_size += len(new_nodes)
                    if Node.out_of_time_check(root, start_time) > self.options.max_time*time_cutoff: # Having 10% time left instantly stops tree construction.
                        break 
                # runs alpha-beta or minimax on the tree (depending on whichever is set active)
                best_move = Node.run_alphabeta(root, is_maximizing) if self.options.alpha_beta else Node.run_minimax(root, is_maximizing)
                self.cumulative_evals += len(nodes_queued)
                if self.cumulative_evals_per_depth.get(current_max_depth) == None:
                    self.cumulative_evals_per_depth[current_max_depth] = 0
                self.cumulative_evals_per_depth[current_max_depth] += len(nodes_queued)
                next_nodes_to_search = nodes_queued # The leaf nodes are recorded to continue building where we left off in the first loop.
                nodes_queued = []
                if current_max_depth < self.options.max_depth: # Increase the depth while we still have time. If we haven't reached the max depth, that is.
                    current_max_depth += 1
                else:
                    break
        # if Node.out_of_time_check() throw an exception, drop everything and return best move found
        except OutOfTimeException:
            log("Move search ran out of time!\n")
        
        # if we could not find a best move (like if max_time = 0), return a random move
        if best_move == None:
            # create a node to encapsulate a randomly picked "best" move
            next_state, move, _ = root.state.random_next_state()
            best_move = Node(next_state, move) 

        non_leaf_node_amount = tree_size - leaf_nodes_num
        self.average_branch_factor = round(tree_size/non_leaf_node_amount,4)
        # return the coordpair that represents enacting the best move found
        return (best_move.value, best_move.action, 0)
        
    def random_next_state(self) -> tuple[Game, CoordPair, UnitAction]:
        """Returns a random successor state to this one."""
        # get a list of all possible moves that can be performed and shuffle it
        move_candidates = list(self.move_candidates(self.next_player))
        if len(move_candidates) == 0: return None
        random.shuffle(move_candidates)

        # clone the current game and perform the first move of the list on it
        move, action = move_candidates[0]
        next_state = self.clone()
        next_state.perform_move(move, action)
        return (next_state, move, action)

    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta."""
    
        start_time = datetime.now()
        score, move, avg_depth = self.search_for_best_move()

        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        log(f"Heuristic score: {score}\n")
        log(f"Cumulative evals: {self.cumulative_evals}\n")
        all_depths_evals = ""
        all_depths_evals_percent = ""
        list_of_depths = list(self.cumulative_evals_per_depth.values())
        for i in range(0,len(list_of_depths)):
            all_depths_evals += " " + str(i+1) + "=" + str(list_of_depths[i])
            all_depths_evals_percent += " " + str(i+1) + "=" + str(round(list_of_depths[i]/self.cumulative_evals*100, 2)) + "%"
        log(f"Cumulative evals by depth: {all_depths_evals}\n")
        log(f"Cumulative evals % by depth: {all_depths_evals_percent}\n")
        log(f"Average branching factor: {self.average_branch_factor}\n")
        log(f"Elapsed time for this action: {elapsed_seconds:0.1f}s\n")
        
        return move

    #endregion

    #region BROKER

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # log(f"Sent move to broker: {move}")
                pass
            else:
                log(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            log(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        log(f"Got move from broker: {move}")
                        return move
                    else:
                        # log("Got broker data for wrong turn.")
                        # log(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # log("Got no data from broker")
                    pass
            else:
                log(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            log(f"Broker error: {error}")
        return None

    #endregion

    #region STRING REPRESENTATION

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}/{self.options.max_turns}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()
    
    #endregion