"""
Rappresentazione e fabbrica delle tessere della mappa (Tile) in PyRogue.

Ogni cella della griglia 2D è un'istanza di `Tile`, che definisce:
- Il carattere ASCII visualizzato a video (`char`).
- La transitabilità fisica per eroe e mostri (`walkable`).
- La trasparenza ottica per linea di vista e incantesimi (`transparent`).
- Un nome descrittivo (`name`) per il log eventi e il debug.
"""
from typing import Dict, Any
from pyrogue.constants import (
    CHAR_WALL, CHAR_FLOOR, CHAR_DOOR_CLOSED, CHAR_DOOR_OPEN,
    CHAR_WATER, CHAR_SPIKES, CHAR_FIRE, CHAR_CHEST, CHAR_STAIRS
)


class Tile:
    """
    Rappresenta una singola tessera della griglia del dungeon.

    La separazione tra `walkable` (attraversabilità fisica) e `transparent`
    (visibilità ottica) è un principio cardine del design dei Roguelike:
    permette di modellare porte chiuse (opache e chiuse), pozze d'acqua
    (trasparenti e calpestabili), o colonne/vetrate (intransitabili ma visibili).
    """

    def __init__(self, char: str, walkable: bool, transparent: bool, name: str):
        self.char = char
        self.walkable = walkable
        self.transparent = transparent
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        """Serializza lo stato della tessera in un dizionario (utile per salvataggi su file)."""
        return {
            "char": self.char,
            "walkable": self.walkable,
            "transparent": self.transparent,
            "name": self.name
        }


# ==============================================================================
# Funzioni Fabbrica (Factory Functions) per Tessere Predefinite
# ==============================================================================

def make_wall() -> Tile:
    """Crea una tessera di muro solido impenetrabile (#), opaca e non attraversabile."""
    return Tile(CHAR_WALL, walkable=False, transparent=False, name="Wall")


def make_floor() -> Tile:
    """Crea una tessera di pavimento calpestabile (.), trasparente e libera al passaggio."""
    return Tile(CHAR_FLOOR, walkable=True, transparent=True, name="Floor")


def make_door(opened: bool = False) -> Tile:
    """
    Crea una porta in legno:
    - Se aperta (`opened=True`), glifo `/`, transitabile e trasparente.
    - Se chiusa (`opened=False`), glifo `+`, non transitabile fino all'apertura e opaca.
    """
    if opened:
        return Tile(CHAR_DOOR_OPEN, walkable=True, transparent=True, name="Open Door")
    return Tile(CHAR_DOOR_CLOSED, walkable=False, transparent=False, name="Closed Door")


def make_water() -> Tile:
    """Crea una pozza d'acqua (~): calpestabile, trasparente e capace di estinguere le fiamme."""
    return Tile(CHAR_WATER, walkable=True, transparent=True, name="Water")


def make_spikes() -> Tile:
    """Crea una trappola a spuntoni (^): calpestabile ma infligge danni fisici al contatto."""
    return Tile(CHAR_SPIKES, walkable=True, transparent=True, name="Spikes")


def make_fire() -> Tile:
    """Crea un fuoco ardente (*): calpestabile ma applica danni da combustione e bruciatura nel tempo."""
    return Tile(CHAR_FIRE, walkable=True, transparent=True, name="Fire Trap")


def make_chest(opened: bool = False) -> Tile:
    """
    Crea un forziere del tesoro ($):
    - Se chiuso, contiene equipaggiamento casuale o pozioni.
    - Una volta aperto dal giocatore, si trasforma visivamente in pavimento calpestabile.
    """
    if opened:
        return Tile(CHAR_FLOOR, walkable=True, transparent=True, name="Opened Chest")
    return Tile(CHAR_CHEST, walkable=True, transparent=True, name="Chest")


def make_stairs() -> Tile:
    """Crea la scala discendente (>): calpestabile, conduce al piano successivo del dungeon."""
    return Tile(CHAR_STAIRS, walkable=True, transparent=True, name="Stairs Down")
