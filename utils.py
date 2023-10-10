from __future__ import annotations
import copy
from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, Iterable

class PlayerTeam(Enum):
    """The 2 players teams."""
    Attacker = 0
    Defender = 1

    is_bot : bool

    def next(self) -> PlayerTeam:
        """The next (other) player."""
        if self is PlayerTeam.Attacker:
            return PlayerTeam.Defender
        else:
            return PlayerTeam.Attacker


##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row : int = 0
    col : int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
                coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
                coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()
    
    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()
    
    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist,self.row+1+dist):
            for col in range(self.col-dist,self.col+1+dist):
                yield Coord(row,col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1,self.col)
        yield Coord(self.row,self.col-1)
        yield Coord(self.row+1,self.col)
        yield Coord(self.row,self.col+1)

    @classmethod
    def from_string(cls, s : str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None
    
    @classmethod
    def are_equal(cls, coord1 : Coord, coord2 : Coord) -> bool:
        return coord1.row == coord2.row and coord1.col == coord2.col

    @classmethod
    def are_adjacent_cross(cls, coord1 : Coord, coord2 : Coord) -> bool:
        """Checks if the two coordinates are adjacent (excluding diagonals)"""
        
        # If the coordinates are more than 1 away in any dimension -> false
        deltaX = abs(coord1.row - coord2.row)
        if(deltaX > 1): return False
        deltaY = abs(coord1.col - coord2.col)
        if(deltaY > 1): return False

        # After the guard checks above, the delta values can only be 0 or 1.
        # If both are 0, the coordinates point to the same cell, if both are 1, they are diagonal.
        return deltaX != deltaY

    @classmethod
    def are_adjecent(cls, coord1 : Coord, coord2 : Coord) -> bool:
        """Checks if the two coordinates are adjacent (including diagonals)"""
    
        # If the coordinates are more than 1 away in any dimension -> false
        deltaX = abs(coord1.row - coord2.row)
        if(deltaX > 1): return False
        deltaY = abs(coord1.col - coord2.col)
        if(deltaY > 1): return False

        # After the guard checks above, the delta values can only be 0 or 1.
        # We just need to ensure that both coordinates don't point to the same cell.
        return deltaX + deltaY > 0
    

        
##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src : Coord = field(default_factory=Coord)
    dst : Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()
    
    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row,self.dst.row+1):
            for col in range(self.src.col,self.dst.col+1):
                yield Coord(row,col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0,col0),Coord(row1,col1))
    
    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0,0),Coord(dim-1,dim-1))
    
    @classmethod
    def from_string(cls, s : str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None
        
    def delta(self: CoordPair) -> Tuple[int, int]:
        """The space difference between both coordinates."""
        return (self.dst.row - self.src.row, self.dst.col - self.src.col)

    def are_equal(self: CoordPair) -> bool:
        return Coord.are_equal(self.src, self.dst)

    def are_adjacent_cross(self: CoordPair) -> bool:
        """Checks if the two coordinates are adjacent (excluding diagonals)"""
        return Coord.are_adjacent_cross(self.src, self.dst)

    def are_adjecent(self : CoordPair) -> bool:
        """Checks if the two coordinates are adjacent (including diagonals)"""
        return Coord.are_adjecent(self.src, self.dst)