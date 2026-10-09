"""
Gestione di armi, pozioni e generazione dell'equipaggiamento in PyRogue.

Questo modulo definisce:
- La classe `Weapon` per armi da mischia (melee) e a distanza (ranged con munizioni/cariche).
- Il catalogo di armi predefinite (`PRESET_WEAPONS`) con pesi e intervalli di danno bilanciati.
- L'algoritmo di generazione casuale dell'equipaggiamento scalato per profondità di piano.
- La classe `Potion` per consumabili curativi di Punti Vita (HP) e Punti Magia (MP).
"""
import random
from typing import Optional, Dict, Any, List


class Weapon:
    """
    Rappresenta un'arma equipaggiabile dall'eroe.

    Attributi principali:
    - `name`: Nome dell'arma visualizzato nell'inventario e nei messaggi di combattimento.
    - `weapon_type`: Tipologia ('melee' per corpo a corpo, 'ranged' per armi da lancio/arco).
    - `weight`: Peso in libbre. Confrontato con la Forza (STR) dell'eroe in `combat.py`:
      se l'arma è troppo pesante per chi la impugna, aumenta il rischio di fallire il colpo (*fumble*).
    - `min_dmg` e `max_dmg`: Intervallo dei dadi di danno (es. 4..9).
    - `charges`: Numero di colpi/munizioni rimasti (-1 per armi da mischia a uso infinito).
    """

    def __init__(
        self,
        name: str,
        weapon_type: str,
        weight: int,
        min_dmg: int,
        max_dmg: int,
        charges: int = -1
    ):
        self.name = name
        self.weapon_type = weapon_type
        self.weight = weight
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.charges = charges

    def roll_damage(self) -> int:
        """Estrae un valore di danno casuale compreso uniformemente tra min_dmg e max_dmg."""
        return random.randint(self.min_dmg, self.max_dmg)

    def is_usable(self) -> bool:
        """Verifica se l'arma può essere usata (le armi a distanza richiedono almeno 1 carica)."""
        if self.weapon_type == 'ranged':
            return self.charges > 0
        return True

    def consume_charge(self) -> bool:
        """Consuma una munizione per le armi a distanza. Restituisce True se il colpo era disponibile."""
        if self.weapon_type == 'ranged' and self.charges > 0:
            self.charges -= 1
            return True
        return False

    def __str__(self) -> str:
        """Formattazione leggibile per l'elenco nell'inventario grafico modale."""
        if self.weapon_type == 'ranged':
            return f"{self.name} (Tiro | Munizioni:{self.charges} | Danno:{self.min_dmg}-{self.max_dmg} | Peso:{self.weight})"
        return f"{self.name} (Mischia | Danno:{self.min_dmg}-{self.max_dmg} | Peso:{self.weight})"


# ==============================================================================
# Catalogo di Armi Predefinite (Modelli e Bilanciamento)
# ==============================================================================
PRESET_WEAPONS: List[Dict[str, Any]] = [
    # --- Armi da Mischia (Melee) ---
    {"name": "Rusty Dagger", "type": "melee", "weight": 3, "min_dmg": 2, "max_dmg": 5},
    {"name": "Short Sword", "type": "melee", "weight": 6, "min_dmg": 4, "max_dmg": 9},
    {"name": "Iron Longsword", "type": "melee", "weight": 10, "min_dmg": 6, "max_dmg": 14},
    {"name": "Heavy Battleaxe", "type": "melee", "weight": 14, "min_dmg": 10, "max_dmg": 20},
    {"name": "Warhammer of Doom", "type": "melee", "weight": 18, "min_dmg": 15, "max_dmg": 28},
    # --- Armi a Distanza (Ranged con munizioni) ---
    {"name": "Wooden Slingshot", "type": "ranged", "weight": 2, "min_dmg": 2, "max_dmg": 4, "charges": 15},
    {"name": "Shortbow", "type": "ranged", "weight": 5, "min_dmg": 4, "max_dmg": 8, "charges": 12},
    {"name": "Heavy Crossbow", "type": "ranged", "weight": 11, "min_dmg": 8, "max_dmg": 16, "charges": 8},
    {"name": "Flame Wand", "type": "ranged", "weight": 7, "min_dmg": 10, "max_dmg": 18, "charges": 6},
]


def generate_random_weapon(depth: int = 1) -> Weapon:
    """
    Genera un'arma procedurale adatta alla profondità del piano attuale (`depth`).

    Nei piani iniziali (depth 1-2) vengono proposte armi leggere e facili da maneggiare;
    man mano che ci si addentra nell'abisso, compaiono armi pesanti ad altissimo danno.
    """
    valid_presets = [
        w for w in PRESET_WEAPONS 
        if w["weight"] <= 5 + depth * 3 or depth >= 4
    ]
    if not valid_presets:
        valid_presets = PRESET_WEAPONS
    chosen = random.choice(valid_presets)
    
    # Bonus progressivo ai danni in base al piano
    dmg_bonus = (depth - 1) // 2
    return Weapon(
        name=chosen["name"],
        weapon_type=chosen["type"],
        weight=chosen["weight"],
        min_dmg=chosen["min_dmg"] + dmg_bonus,
        max_dmg=chosen["max_dmg"] + dmg_bonus,
        charges=chosen.get("charges", -1)
    )


class Potion:
    """
    Rappresenta una pozione consumabile.

    Tipi disponibili:
    - 'hp': Ripristina Punti Vita all'eroe.
    - 'mp': Ripristina Punti Magia (Magika/Mana) per lanciare incantesimi.
    """

    def __init__(self, potion_type: str, heal_amount: int = 15):
        self.potion_type = potion_type
        self.heal_amount = heal_amount

    def __str__(self) -> str:
        if self.potion_type == 'hp':
            return f"Health Potion (+{self.heal_amount} HP)"
        return f"Magika Potion (+{self.heal_amount} MP)"
