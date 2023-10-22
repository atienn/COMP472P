# To-do List
Thing that we need to do for the project. Expand as needed.

### 

- [x] Units attack/heal when trying to move into another's space
- [x] Remove units when they die
- [x] Units recognize being "engaged" and cannot move while in that state (excluding Tech & Virus)
- [x] Units cannot move back towards their "base" (excluding Tech & Virus)
- [x] Whenever a unit tries to heal, the move should be made invalid if the heal is 0 or the target is full HP
- [x] Add option to write game output to file
- [ ] (optional) Bot Player that inputs random moves (just to validate end-to-end)
- [x] (optional) Sperate code into multiple files (e.g. "game.py", "input-output.py", "bot.py", etc) for the sake of code organization.

### D2
- [x] Restructure `determine_action()` so that it doesn't log directly if a move is invalid or not (see `move_candidates()`).
- [x] Restructure the way moves get enacted as not to have duplicate move validity verification in computer decision-making (see `next_state_candidates()`, will likely be within `perform_move()` method) 
- [x] Review the log messages (unit attacks unit for X damage!) as they seem to be wrong
- [x] Heuristic stuff:
* The winning strategy for Attacker seems to be: get your programs to wreck at least one tech, then send in the viruses to pwn the AI.
* If the Defender gets to a state where only both AIs are left alive, it has basically won because of the rule where the AIs can only move away from their base - unless their AI has moved forward already.
* The Defender should value its Techs more. And block Viruses trying to go for sneaky rushes through openings.
- [x] Rework `generate_node_tree()` and integrate successor generation within minimax/alpha-beta instead of generating whole tree and then navigating it
- [ ] Review the output. Heuristic score sometimes shows "9999" for no reason, evals per depth is empty, eval perf is always 0.
### D3