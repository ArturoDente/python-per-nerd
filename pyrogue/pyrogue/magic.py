"""
Sistema di incantesimi e magia (Grimorio) in PyRogue.

Questo modulo definisce la classe `Spell` e il repertorio degli incantesimi base:
- `Magic Missile` (Dardo Magico): dardo arcano che colpisce con precisione infallibile un bersaglio in vista.
- `Heal` (Cura): rigenerazione rapida dei Punti Ferita (HP) consumando mana (MP).
- `Fireball` (Palla di Fuoco): devastante proiettile di fuoco che infligge danni da impatto e ustioni continuate.
"""
from typing import Optional, List, Tuple


class Spell:
    """
    Rappresenta un incantesimo lanciabile dall'eroe attraverso il grimorio (`[M]`).

    Attributi:
    - `name`: Nome dell'incantesimo.
    - `mp_cost`: Quantità di Punti Magia (MP) richiesti per il lancio.
    - `description`: Descrizione breve degli effetti per il menu modale.
    - `spell_type`: Categoria logica ('damage', 'heal', 'fire_damage').
    - `min_effect` / `max_effect`: Intervallo di efficacia (danno inflitto o punti vita guariti).
    """

    def __init__(
        self,
        name: str,
        mp_cost: int,
        description: str,
        spell_type: str,
        min_effect: int,
        max_effect: int
    ):
        self.name = name
        self.mp_cost = mp_cost
        self.description = description
        self.spell_type = spell_type
        self.min_effect = min_effect
        self.max_effect = max_effect

    def __str__(self) -> str:
        """Formattazione per l'elenco nel menu di selezione incantesimi."""
        return f"{self.name} (Costo MP: {self.mp_cost}) - {self.description}"


# ==============================================================================
# Grimorio degli Incantesimi Predefiniti
# ==============================================================================

# 1. Dardo Magico: attacco arcano a bersaglio singolo a media distanza
SPELL_MAGIC_MISSILE = Spell(
    name="Magic Missile",
    mp_cost=3,
    description="Dardo arcano infallibile contro il nemico visibile più vicino.",
    spell_type="damage",
    min_effect=8,
    max_effect=14
)

# 2. Cura: magia di recupero vitale per situazioni critiche
SPELL_HEAL = Spell(
    name="Heal",
    mp_cost=4,
    description="Ripristina istantaneamente Punti Ferita all'eroe.",
    spell_type="heal",
    min_effect=15,
    max_effect=25
)

# 3. Palla di Fuoco: magia offensiva pesante ad alto costo con bruciatura nel tempo
SPELL_FIREBALL = Spell(
    name="Fireball",
    mp_cost=6,
    description="Esplosione fiammeggiante con danni ad area e ustioni continuate.",
    spell_type="fire_damage",
    min_effect=14,
    max_effect=22
)

# Lista degli incantesimi noti all'eroe all'inizio della partita
DEFAULT_SPELLS: List[Spell] = [SPELL_MAGIC_MISSILE, SPELL_HEAL, SPELL_FIREBALL]
