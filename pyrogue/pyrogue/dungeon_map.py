"""
Generazione procedurale del dungeon e meccaniche su griglia matriciale in PyRogue.

Questo modulo implementa l'algoritmo geometrico di generazione dei livelli:
- La classe `Room`: modella stanze rettangolari con coordinate Bounding Box (AABB)
  e test di intersezione spaziale (`intersects`).
- La classe `DungeonMap`: incapsula la matrice bidimensionale delle tessere (`tiles[y][x]`),
  la lista delle stanze, le entità nemiche presenti e le scale di discesa.
- La funzione `generate_dungeon()`: coordina la generazione procedurale dei livelli normali (1-4)
  scavando stanze non sovrapposte e collegandole con corridoi ad "L" continui.
- La funzione `_generate_boss_level()`: costruisce la cittadella fortificata del Boss finale
  al 5° livello, con anticamera, cortili difensivi, cancelli fortificati e guardie d'élite.
"""
import random
from typing import List, Tuple, Optional
from pyrogue.constants import (
    DEFAULT_MAP_WIDTH, DEFAULT_MAP_HEIGHT,
    CHAR_WALL, CHAR_FLOOR, CHAR_DOOR_CLOSED, CHAR_DOOR_OPEN,
    CHAR_WATER, CHAR_SPIKES, CHAR_FIRE, CHAR_CHEST, CHAR_STAIRS
)
from pyrogue.tile import (
    Tile, make_wall, make_floor, make_door, make_water,
    make_spikes, make_fire, make_chest, make_stairs
)
from pyrogue.entities import Monster, spawn_random_monster, create_boss


class Room:
    """
    Rappresenta una stanza rettangolare nel piano del dungeon.

    Definita tramite le coordinate cartesiane dei suoi vertici opposti:
    - (x1, y1): Angolo superiore sinistro (inclusivo).
    - (x2, y2): Angolo inferiore destro (inclusivo).
    """

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        """Restituisce le coordinate centrali (cx, cy) arrotondate a intero."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def intersects(self, other: 'Room') -> bool:
        """
        Verifica se questa stanza si sovrappone a un'altra tramite il test AABB.
        Due rettangoli allineati agli assi si intersecano se e solo se i loro
        intervalli si sovrappongono contemporaneamente sia sull'asse X che sull'asse Y.
        """
        return (
            self.x1 <= other.x2 and self.x2 >= other.x1 and
            self.y1 <= other.y2 and self.y2 >= other.y1
        )


class DungeonMap:
    """
    Rappresenta l'intera mappa bidimensionale del piano sotterraneo.

    Inizializzata a 'muro pieno': una matrice di dimensioni `height x width`
    in cui ogni singola cella è inizialmente un muro impenetrabile (`#`).
    'Scavare' una stanza o un corridoio significa semplicemente sovrascrivere
    le tessere corrispondenti con istanze di pavimento calpestabile (`.`).
    """

    def __init__(self, width: int = DEFAULT_MAP_WIDTH, height: int = DEFAULT_MAP_HEIGHT):
        self.width = width
        self.height = height
        # Inizializzazione della matrice 2D a muro solido impenetrabile
        self.tiles: List[List[Tile]] = [[make_wall() for _ in range(width)] for _ in range(height)]
        self.rooms: List[Room] = []
        self.monsters: List[Monster] = []
        self.stairs_pos: Optional[Tuple[int, int]] = None
        self.player_start: Tuple[int, int] = (1, 1)

    def in_bounds(self, x: int, y: int) -> bool:
        """Verifica che le coordinate (x, y) risiedano entro i confini fisici della griglia."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        """Verifica se una cella è attraversabile da un'entità."""
        if not self.in_bounds(x, y):
            return False
        return self.tiles[y][x].walkable

    def get_tile(self, x: int, y: int) -> Tile:
        """Restituisce l'oggetto Tile presente alle coordinate (x, y)."""
        return self.tiles[y][x]

    def set_tile(self, x: int, y: int, tile: Tile):
        """Assegna un nuovo oggetto Tile alle coordinate (x, y)."""
        if self.in_bounds(x, y):
            self.tiles[y][x] = tile


def generate_dungeon(
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    depth: int = 1,
    is_boss_level: bool = False
) -> DungeonMap:
    """
    Algoritmo principale di generazione procedurale del dungeon.

    Passaggi operativi:
    1. Se il livello corrente è il quinto (`is_boss_level=True`), costruisce l'arena del Boss.
    2. Altrimenti, esegue fino a 30 tentativi di estrazione per stanze candidate rettangolari:
       - Estrae larghezza `w`, altezza `h` e posizione `(x, y)` casuali.
       - Verifica con `intersects()` che la nuova stanza non collisioni con quelle già posizionate.
       - Se libera, scava il pavimento interno trasformando le tessere in `make_floor()`.
       - Connette la stanza al centro della stanza precedente scavando un tunnel ad 'L'
         (un tratto orizzontale e uno verticale con ordine casuale).
    3. Posiziona l'eroe al centro della prima stanza e le scale al centro dell'ultima stanza.
    4. Posiziona le porte di legno in corrispondenza delle soglie perimetrali delle stanze.
    5. Distribuisce trappole (fiamme, spuntoni), pozze d'acqua, forzieri e mostri proporzionali a `depth`.
    """
    dungeon = DungeonMap(width, height)
    
    if is_boss_level:
        return _generate_boss_level(dungeon)

    max_rooms = 8
    min_size = 5
    max_size = 11

    rooms: List[Room] = []
    for _ in range(30):
        w = random.randint(min_size, max_size)
        h = random.randint(min_size, max_size)
        x = random.randint(1, width - w - 1)
        y = random.randint(1, height - h - 1)
        new_room = Room(x, y, w, h)

        # Scarta la stanza candidata se interseca una stanza già scavata
        if any(new_room.intersects(other) for other in rooms):
            continue

        # Scavo del perimetro interno: trasforma le celle da muro (#) a pavimento calpestabile (.)
        for rx in range(new_room.x1 + 1, new_room.x2):
            for ry in range(new_room.y1 + 1, new_room.y2):
                dungeon.set_tile(rx, ry, make_floor())

        if rooms:
            # Connessione della nuova stanza alla precedente tramite corridoio ad "L"
            prev_x, prev_y = rooms[-1].center
            curr_x, curr_y = new_room.center

            # Scelta casuale: prima tratto orizzontale poi verticale, o viceversa
            if random.choice([True, False]):
                _dig_h_tunnel(dungeon, prev_x, curr_x, prev_y)
                _dig_v_tunnel(dungeon, prev_y, curr_y, curr_x)
            else:
                _dig_v_tunnel(dungeon, prev_y, curr_y, prev_x)
                _dig_h_tunnel(dungeon, prev_x, curr_x, curr_y)

        rooms.append(new_room)
        if len(rooms) >= max_rooms:
            break

    dungeon.rooms = rooms
    if not rooms:
        # Fallback di sicurezza: se nessun tentativo è andato a buon fine, crea una stanza gigante
        rooms = [Room(2, 2, width - 4, height - 4)]
        for rx in range(3, width - 3):
            for ry in range(3, height - 3):
                dungeon.set_tile(rx, ry, make_floor())
        dungeon.rooms = rooms

    # Punto di partenza del giocatore: centro della prima stanza scavata
    dungeon.player_start = rooms[0].center

    # Scala discendente per il piano successivo: centro dell'ultima stanza
    stairs_x, stairs_y = rooms[-1].center
    dungeon.set_tile(stairs_x, stairs_y, make_stairs())
    dungeon.stairs_pos = (stairs_x, stairs_y)

    # Inserimento delle porte sui confini perimetrali delle stanze
    _place_doors(dungeon)

    # Popolamento delle stanze intermedie con insidie, tesori e mostri
    for i, room in enumerate(rooms):
        if i == 0:
            continue  # La stanza di partenza dell'eroe rimane sempre sicura e sgombra

        # Pozze d'acqua (25% di probabilità per stanza)
        if random.random() < 0.25:
            wx = random.randint(room.x1 + 1, room.x2 - 1)
            wy = random.randint(room.y1 + 1, room.y2 - 1)
            if (wx, wy) != dungeon.stairs_pos and dungeon.get_tile(wx, wy).char == CHAR_FLOOR:
                dungeon.set_tile(wx, wy, make_water())

        # Trappole a spuntoni (25% di probabilità per stanza)
        if random.random() < 0.25:
            sx = random.randint(room.x1 + 1, room.x2 - 1)
            sy = random.randint(room.y1 + 1, room.y2 - 1)
            if (sx, sy) != dungeon.stairs_pos and dungeon.get_tile(sx, sy).char == CHAR_FLOOR:
                dungeon.set_tile(sx, sy, make_spikes())

        # Trappole di fiamme ardenti (25% di probabilità per stanza)
        if random.random() < 0.25:
            fx = random.randint(room.x1 + 1, room.x2 - 1)
            fy = random.randint(room.y1 + 1, room.y2 - 1)
            if (fx, fy) != dungeon.stairs_pos and dungeon.get_tile(fx, fy).char == CHAR_FLOOR:
                dungeon.set_tile(fx, fy, make_fire())

        # Forziere del tesoro con armi (40% di probabilità per stanza)
        if random.random() < 0.4:
            cx = random.randint(room.x1 + 1, room.x2 - 1)
            cy = random.randint(room.y1 + 1, room.y2 - 1)
            if (cx, cy) != dungeon.stairs_pos and dungeon.get_tile(cx, cy).char == CHAR_FLOOR:
                dungeon.set_tile(cx, cy, make_chest())

        # Spawn mostri (1 o 2 creature per stanza)
        num_monsters = random.randint(1, 2)
        for _ in range(num_monsters):
            mx = random.randint(room.x1 + 1, room.x2 - 1)
            my = random.randint(room.y1 + 1, room.y2 - 1)
            if (
                (mx, my) != dungeon.stairs_pos and
                (mx, my) != dungeon.player_start and
                dungeon.get_tile(mx, my).walkable and
                not any(m.x == mx and m.y == my for m in dungeon.monsters)
            ):
                monster = spawn_random_monster(mx, my, depth)
                dungeon.monsters.append(monster)

    return dungeon


def _dig_h_tunnel(dungeon: DungeonMap, x1: int, x2: int, y: int):
    """Scava un corridoio orizzontale trasformando le tessere tra x1 e x2 alla quota y in pavimento."""
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if dungeon.in_bounds(x, y):
            dungeon.set_tile(x, y, make_floor())


def _dig_v_tunnel(dungeon: DungeonMap, y1: int, y2: int, x: int):
    """Scava un corridoio verticale trasformando le tessere tra y1 e y2 alla colonna x in pavimento."""
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if dungeon.in_bounds(x, y):
            dungeon.set_tile(x, y, make_floor())


def _place_doors(dungeon: DungeonMap):
    """
    Posiziona porte di legno (+) nei punti di giunzione dove i corridoi attraversano le pareti perimetrali delle stanze.
    Analizza i bordi orizzontali e verticali delle stanze alla ricerca di caselle scavate a pavimento.
    """
    for room in dungeon.rooms:
        # Controllo delle soglie sui muri perimetrali orizzontali (sopra e sotto)
        for x in range(room.x1 + 1, room.x2):
            for y in (room.y1, room.y2):
                if dungeon.in_bounds(x, y) and dungeon.get_tile(x, y).char == CHAR_FLOOR:
                    if (x, y) != dungeon.stairs_pos and (x, y) != dungeon.player_start:
                        if random.random() < 0.6:
                            dungeon.set_tile(x, y, make_door())

        # Controllo delle soglie sui muri perimetrali verticali (sinistra e destra)
        for y in range(room.y1 + 1, room.y2):
            for x in (room.x1, room.x2):
                if dungeon.in_bounds(x, y) and dungeon.get_tile(x, y).char == CHAR_FLOOR:
                    if (x, y) != dungeon.stairs_pos and (x, y) != dungeon.player_start:
                        if random.random() < 0.6:
                            dungeon.set_tile(x, y, make_door())


def _generate_boss_level(dungeon: DungeonMap) -> DungeonMap:
    """
    Costruisce il quinto livello speciale: la cittadella fortificata del Boss finale.

    Struttura architettonica:
    - Anticamera di partenza con l'eroe e forzieri di rifornimento.
    - Primo Cancello fortificato (Gate 1) presidiato da un'avanguardia di Orchi armati.
    - Cortile centrale con pozze d'acqua e fiamme, difeso da Demoni d'élite.
    - Secondo Cancello fortificato (Gate 2) che dà accesso alla Sala del Trono.
    - Sala del Trono: ospita il Signore dei Demoni (Boss) e le sue guardie demoniache personali.
    """
    start_x, start_y = 3, 2
    end_x, end_y = dungeon.width - 4, dungeon.height - 3
    dungeon.rooms = [Room(start_x, start_y, end_x - start_x, end_y - start_y)]

    # 1. Scavo dell'arena perimetrale complessiva
    for x in range(start_x, end_x + 1):
        for y in range(start_y, end_y + 1):
            if x == start_x or x == end_x or y == start_y or y == end_y:
                dungeon.set_tile(x, y, make_wall())
            else:
                dungeon.set_tile(x, y, make_floor())

    # 2. Primo Cancello difensivo (Muro a x = 16 con porte pesanti)
    gate1_x = 16
    for y in range(start_y + 1, end_y):
        dungeon.set_tile(gate1_x, y, make_wall())
    dungeon.set_tile(gate1_x, start_y + 4, make_door())
    dungeon.set_tile(gate1_x, end_y - 4, make_door())

    # 3. Secondo Cancello difensivo (Muro a x = 30 con porte rinforzate)
    gate2_x = 30
    for y in range(start_y + 1, end_y):
        dungeon.set_tile(gate2_x, y, make_wall())
    dungeon.set_tile(gate2_x, (start_y + end_y) // 2 - 2, make_door())
    dungeon.set_tile(gate2_x, (start_y + end_y) // 2 + 2, make_door())

    # Partenza del giocatore nell'Anticamera iniziale
    mid_y = (start_y + end_y) // 2
    dungeon.player_start = (start_x + 2, mid_y)

    # Insidie nel cortile tra Cancello 1 e Cancello 2
    dungeon.set_tile(23, start_y + 3, make_water())
    dungeon.set_tile(23, end_y - 3, make_water())
    dungeon.set_tile(23, mid_y - 2, make_fire())
    dungeon.set_tile(23, mid_y + 2, make_fire())

    # Forzieri di rifornimento negli angoli dell'anticamera e della sala del trono
    dungeon.set_tile(start_x + 2, start_y + 2, make_chest())
    dungeon.set_tile(start_x + 2, end_y - 2, make_chest())
    dungeon.set_tile(end_x - 2, start_y + 2, make_chest())
    dungeon.set_tile(end_x - 2, end_y - 2, make_chest())

    # POPOLAMENTO DEI DIFENSORI DELLA CITTADELLA:
    # 1. Avanguardia dell'Anticamera (posta a guardia di Gate 1):
    orc1 = spawn_random_monster(gate1_x - 3, start_y + 4, depth=4)
    orc1.is_alert = True
    orc2 = spawn_random_monster(gate1_x - 3, end_y - 4, depth=4)
    orc2.is_alert = True
    dungeon.monsters.extend([orc1, orc2])

    # 2. Guardia d'élite del Cortile Centrale (tra Gate 1 e Gate 2):
    demon1 = spawn_random_monster(25, mid_y - 3, depth=5)
    demon1.is_alert = True
    demon2 = spawn_random_monster(25, mid_y + 3, depth=5)
    demon2.is_alert = True
    dungeon.monsters.extend([demon1, demon2])

    # 3. Sala del Trono: Il Boss finale e i suoi luogotenenti demoniaci
    boss_x = (gate2_x + end_x) // 2
    boss = create_boss(boss_x, mid_y)
    boss.is_alert = True
    dungeon.monsters.append(boss)

    guard1 = spawn_random_monster(boss_x + 3, mid_y - 2, depth=5)
    guard1.is_alert = True
    guard2 = spawn_random_monster(boss_x + 3, mid_y + 2, depth=5)
    guard2.is_alert = True
    dungeon.monsters.extend([guard1, guard2])

    return dungeon
