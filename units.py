from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import ClassVar

from utils import PlayerTeam

class UnitAction(Enum):
    """Actions that units can take during play."""
    InvalidNoExist = 0 # default value should always be invalid
    InvalidNoUnderstand = 5
    InvalidNoDiagonal = 6
    InvalidNoOwn = 7
    InvalidNoReturnVirus = 8
    InvalidNoReturnTech = 9
    InvalidNoDisengage = 10
    InvalidNoUnit = 11
    Move = 1
    Attack = 2
    Repair = 3
    Kaboom = 4

class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4


##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: PlayerTeam = PlayerTeam.Attacker
    type: UnitType = UnitType.Program
    health : int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table : ClassVar[list[list[int]]] = [
        [3,3,3,3,1], # AI
        [1,1,6,1,1], # Tech
        [9,6,1,6,1], # Virus
        [3,3,3,3,1], # Program
        [1,1,1,1,1], # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table : ClassVar[list[list[int]]] = [
        [0,1,1,0,0], # AI
        [3,0,0,3,3], # Tech
        [0,0,0,0,0], # Virus
        [0,0,0,0,0], # Program
        [0,0,0,0,0], # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0
    
    def unit_name_string(self) -> str:
        unit_names = {
            UnitType.Program : "Program",
            UnitType.Tech : "Tech",
            UnitType.Virus : "Virus",
            UnitType.Firewall : "Firewall",
            UnitType.AI : "AI",
        }
        return unit_names[self.type]
    
    def can_move_freely(self) -> bool:
        """If this unit is allowed to disengage from combat or move towards their base."""
        return self.type == UnitType.Tech or self.type == UnitType.Virus

    def mod_health(self, health_delta : int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"
    
    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()
    
    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount
