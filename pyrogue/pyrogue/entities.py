"""
Gerarchia delle entità viventi (Entity, Player, Monster) in PyRogue.

Questo modulo implementa i principi fondamentali della OOP:
- Ereditarietà: `Player` e `Monster` ereditano dalla classe base astratta `Entity`.
- Incapsulamento: gestione sicura di salute (HP), mana (MP), energia di turno e stati alterati.
- Polimorfismo: metodi unificati per subire danni (`take_damage`), guarire (`heal`) e calcolare lo stato vitale (`is_alive`).
- Fabbriche specializzate: funzioni per generare Goblin, Orchi, Demoni e il Boss finale con statistiche bilanciate.
"""
import random
from typing import Optional, List, Dict, Any
from pyrogue.constants import (
    CHAR_PLAYER, CHAR_GOBLIN, CHAR_ORC, CHAR_DEMON, CHAR_BOSS,
    COLOR_PLAYER, COLOR_GOBLIN, COLOR_ORC, COLOR_DEMON, COLOR_BOSS
)
from pyrogue.items import Weapon, Potion, generate_random_weapon
from pyrogue.magic import Spell, DEFAULT_SPELLS


class Entity:
    """
    Classe base per qualsiasi essere vivente presente nel dungeon (giocatore o mostro).

    Attributi condivisi:
    - `x, y`: Coordinate bidimensionali attuali nella griglia.
    - `name`: Nome identificativo visualizzato nel log di combattimento.
    - `char`: Carattere ASCII rappresentativo sulla mappa Curses.
    - `color`: Indice della coppia di colore ANSI associata.
    - `hp, max_hp`: Punti Ferita attuali e massimi.
    - `str_stat`: Punteggio di Forza (utilizzato per impugnare armi pesanti e scalare i danni).
    - `spd`: Velocità di azione (punti energia accumulati a ogni ciclo di turno).
    - `energy`: Accumulatore di punti azione (quando raggiunge la soglia 10, l'entità agisce).
    - `fire_turns`: Contatore di turni residui per lo stato alterato Bruciatura.
    - `is_alert`: Flag di allerta; quando True, il mostro insegue attivamente il giocatore.
    """

    def __init__(
        self,
        x: int,
        y: int,
        name: str,
        char: str,
        color: int,
        hp: int,
        max_hp: int,
        str_stat: int,
        spd: int
    ):
        self.x = x
        self.y = y
        self.name = name
        self.char = char
        self.color = color
        self.hp = hp
        self.max_hp = max_hp
        self.str_stat = str_stat
        self.spd = spd
        self.energy = 0        # Accumulatore per il sistema a turni asincrono
        self.fire_turns = 0    # Durata dell'effetto continuo di bruciatura
        self.is_alert = False  # Si attiva quando l'entità viene attaccata o avvista il nemico

    @property
    def is_alive(self) -> bool:
        """Restituisce True se l'entità ha ancora Punti Ferita superiori a zero."""
        return self.hp > 0

    def take_damage(self, amount: int):
        """Applica una quantità di danno, riducendo gli HP (senza scendere sotto 0) e allertando l'entità."""
        self.hp = max(0, self.hp - amount)
        self.is_alert = True

    def heal(self, amount: int):
        """Ripristina una quantità di HP senza eccedere il valore massimo consentito (max_hp)."""
        self.hp = min(self.max_hp, self.hp + amount)


class Player(Entity):
    """
    Rappresenta l'eroe controllato dal giocatore umano.

    Estende `Entity` aggiungendo:
    - Riserva di Mana/Magika (`mp, max_mp`) per lanciare incantesimi.
    - Direzione dell'ultimo movimento (`last_dx, last_dy`), fondamentale per mirare con armi a distanza.
    - Slot di equipaggiamento attivo: arma da mischia (`equipped_melee`) e arma da tiro (`equipped_ranged`).
    - Zaino per armi secondarie (`weapons_bag`), pozioni (`hp_potions`, `mp_potions`) e grimorio (`known_spells`).
    """

    def __init__(self, x: int = 0, y: int = 0):
        super().__init__(
            x=x,
            y=y,
            name="Hero",
            char=CHAR_PLAYER,
            color=COLOR_PLAYER,
            hp=30,
            max_hp=30,
            str_stat=10,
            spd=10
        )
        self.mp = 10
        self.max_mp = 10
        self.last_dx = 1  # Direzione di sguardo predefinita verso Est (dx=1, dy=0)
        self.last_dy = 0
        
        # Equipaggiamento iniziale di sopravvivenza
        self.equipped_melee: Optional[Weapon] = Weapon(
            name="Rusty Dagger", weapon_type="melee", weight=3, min_dmg=2, max_dmg=5
        )
        self.equipped_ranged: Optional[Weapon] = Weapon(
            name="Wooden Slingshot", weapon_type="ranged", weight=2, min_dmg=2, max_dmg=4, charges=10
        )
        self.weapons_bag: List[Weapon] = []
        
        # Scorta iniziale di pozioni curative
        self.hp_potions: int = 2
        self.mp_potions: int = 1
        
        # Conoscenza degli incantesimi base
        self.known_spells: List[Spell] = list(DEFAULT_SPELLS)

    def restore_mp(self, amount: int):
        """Ripristina punti mana all'eroe fino al limite massimo consentito."""
        self.mp = min(self.max_mp, self.mp + amount)

    def consume_mp(self, amount: int) -> bool:
        """Consuma una quota di mana per lanciare un incantesimo. Ritorna False se il mana è insufficiente."""
        if self.mp >= amount:
            self.mp -= amount
            return True
        return False

    def equip_weapon(self, weapon: Weapon) -> Optional[Weapon]:
        """
        Equipaggia un'arma nello slot appropriato (mischia o distanza).

        Se lo slot era già occupato, la vecchia arma viene riposta nello zaino (`weapons_bag`).
        Restituisce la vecchia arma disequipaggiata (o None).
        """
        old_weapon = None
        if weapon.weapon_type == 'melee':
            old_weapon = self.equipped_melee
            self.equipped_melee = weapon
        else:
            old_weapon = self.equipped_ranged
            self.equipped_ranged = weapon
            
        if weapon in self.weapons_bag:
            self.weapons_bag.remove(weapon)
        if old_weapon:
            self.weapons_bag.append(old_weapon)
        return old_weapon


class Monster(Entity):
    """
    Rappresenta un avversario non giocante controllato dall'AI nel dungeon.

    Estende `Entity` memorizzando:
    - Intervallo di danno naturale (`min_dmg, max_dmg`).
    - Tipologia di creatura (`monster_type`: 'goblin', 'orc', 'demon', 'boss').
    """

    def __init__(
        self,
        x: int,
        y: int,
        name: str,
        char: str,
        color: int,
        hp: int,
        max_hp: int,
        str_stat: int,
        spd: int,
        min_dmg: int,
        max_dmg: int,
        monster_type: str
    ):
        super().__init__(x, y, name, char, color, hp, max_hp, str_stat, spd)
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.monster_type = monster_type

    def roll_damage(self) -> int:
        """Estrae casualmente l'ammontare di danno inferto dall'attacco del mostro."""
        return random.randint(self.min_dmg, self.max_dmg)


# ==============================================================================
# Fabbriche Specializzate per le Tipologie di Mostri
# ==============================================================================

def create_goblin(x: int, y: int, depth: int = 1) -> Monster:
    """Crea un Goblin (g): creatura agile e scattante (SPD 12 > Player 10), ma fragile."""
    hp_val = 6 + depth * 2
    return Monster(
        x=x, y=y,
        name="Goblin",
        char=CHAR_GOBLIN,
        color=COLOR_GOBLIN,
        hp=hp_val, max_hp=hp_val,
        str_stat=6,
        spd=12,  # Velocità superiore all'eroe: guadagna turni extra nel tempo
        min_dmg=1 + depth // 2,
        max_dmg=3 + depth // 2,
        monster_type="goblin"
    )


def create_orc(x: int, y: int, depth: int = 1) -> Monster:
    """Crea un Orco (O): guerriero corazzato, lento (SPD 7 < Player 10) ma dotato di colpi pesanti."""
    hp_val = 12 + depth * 3
    return Monster(
        x=x, y=y,
        name="Orc",
        char=CHAR_ORC,
        color=COLOR_ORC,
        hp=hp_val, max_hp=hp_val,
        str_stat=14,
        spd=7,   # Più lento dell'eroe: il giocatore può distanziarlo tatticamente
        min_dmg=3 + depth,
        max_dmg=6 + depth,
        monster_type="orc"
    )


def create_demon(x: int, y: int, depth: int = 1) -> Monster:
    """Crea un Demone (D): avversario bilanciato e letale con attacchi magici."""
    hp_val = 10 + depth * 2
    return Monster(
        x=x, y=y,
        name="Demon",
        char=CHAR_DEMON,
        color=COLOR_DEMON,
        hp=hp_val, max_hp=hp_val,
        str_stat=10,
        spd=10,  # Pari velocità rispetto all'eroe (1:1)
        min_dmg=4 + depth,
        max_dmg=8 + depth,
        monster_type="demon"
    )


def create_boss(x: int, y: int) -> Monster:
    """Crea il Signore dei Demoni (B): il Boss finale che presidia il quinto livello del dungeon."""
    hp_val = 60
    return Monster(
        x=x, y=y,
        name="Infernal Demon Lord",
        char=CHAR_BOSS,
        color=COLOR_BOSS,
        hp=hp_val, max_hp=hp_val,
        str_stat=18,
        spd=11,  # Leggermente più rapido del giocatore per chiudere le distanze con aggressività
        min_dmg=8,
        max_dmg=15,
        monster_type="boss"
    )


def spawn_random_monster(x: int, y: int, depth: int = 1) -> Monster:
    """
    Genera un mostro casuale ponderato in base alla profondità del piano sotterraneo.

    Nei primi piani predominano i deboli Goblin (50%); scendendo nelle profondità
    la probabilità di incontrare Orchi e temibili Demoni cresce sensibilmente.
    """
    weights = [50, 30, 20]  # Goblin, Orco, Demone
    if depth >= 3:
        weights = [30, 35, 35]
    choice = random.choices(["goblin", "orc", "demon"], weights=weights)[0]
    if choice == "goblin":
        return create_goblin(x, y, depth)
    elif choice == "orc":
        return create_orc(x, y, depth)
    else:
        return create_demon(x, y, depth)
