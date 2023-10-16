from __future__ import annotations
import argparse

from output import FileOutput, log
from utils import PlayerTeam
from game import GameType, Options, Game

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

##############################################################################################################


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default="manual", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    parser.add_argument('--no_file_output', action='store_true', help='wether to enable output to file')
    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker
    # create a new game
    game = Game(options=options)

    if not (args.no_file_output):
        FileOutput.open_file("game_trace_[{}]_[{}]_[{}]".format(options.alpha_beta, options.max_time, options.max_turns))

    # the main game loop
    log("Welcome to AI Wargame. Destroy the enemy AI to win!")
    log(f"The current gamemode is set to {game.gamemode_name_string(game_type)}.")
    log(f"After {game.options.max_turns} turns, the Defender will win by default!")
    while True:
        log()
        log(game)
        winner = game.has_winner()
        if winner is not None:
            log(f"{winner.name} wins in {game.turns_played} turn(s)!")
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == PlayerTeam.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == PlayerTeam.Defender:
            game.human_turn()
        else:
            player = game.next_player
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                log("Computer doesn't know what to do!!!")
                exit(1)
    
    FileOutput.close()


##############################################################################################################

if __name__ == '__main__':
    main()
