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
- 
### D3