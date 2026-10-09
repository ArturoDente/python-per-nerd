"""
Risoluzione del combattimento, fisica dei proiettili, trappole e stati alterati in PyRogue.

Questo modulo incapsula tutte le regole di scontro del dungeon (Model puro, zero dipendenze da Curses):
- Attacco corpo a corpo con penalità di peso (Forza vs Peso dell'arma).
- Meccanica di tiro a distanza: il proiettile avanza in linea retta casella per casella finché non impatta su un ostacolo o un nemico.
- Attacco in mischia dei mostri con tiro dei dadi RPG.
- Lancio degli incantesimi con consumo di mana e applicazione dello stato Bruciato.
- Risoluzione delle insidie ambientali: pozze d'acqua (estinguono il fuoco), spuntoni (danno fisico istantaneo) e fiamme (danno continuo nel tempo).
"""
import random
import math
from typing import Tuple, List, Optional
from pyrogue.constants import CHAR_WATER, CHAR_SPIKES, CHAR_FIRE, CHAR_DOOR_CLOSED
from pyrogue.entities import Player, Monster, Entity
from pyrogue.tile import Tile, make_door, make_floor
from pyrogue.items import Weapon, Potion, generate_random_weapon
from pyrogue.magic import Spell, SPELL_MAGIC_MISSILE, SPELL_HEAL, SPELL_FIREBALL


class CombatEngine:
    """
    Motore logico delle interazioni di combattimento e degli effetti ambientali.

    Mantiene il registro storico dei messaggi (`message_log`), che viene visualizzato
    a scorrimento nell'interfaccia utente Curses senza mai consumare memoria incontrollata.
    """

    def __init__(self):
        self.message_log: List[str] = []

    def log(self, message: str):
        """Aggiunge una riga al registro messaggi, mantenendo al massimo le ultime 100 voci in memoria."""
        self.message_log.append(message)
        if len(self.message_log) > 100:
            self.message_log.pop(0)

    def player_attack_monster(self, player: Player, monster: Monster) -> bool:
        """
        Risolve un attacco in mischia dell'eroe contro un mostro adiacente.

        Meccanica Peso contro Forza:
        Se il peso dell'arma impugnata supera la Forza dell'eroe (`weight > str_stat`),
        si applica una probabilità di fallimento del colpo (*fumble*) proporzionale al sovrappeso:
        `miss_chance = min(0.75, 0.50 + overweight * 0.05)`.

        Restituisce True se il mostro è stato sconfitto.
        """
        weapon = player.equipped_melee
        weapon_name = weapon.name if weapon else "a mani nude"
        weight = weapon.weight if weapon else 0
        
        # Controllo della penalità per arma troppo pesante rispetto alla Forza
        if weight > player.str_stat:
            overweight = weight - player.str_stat
            miss_chance = min(0.75, 0.50 + overweight * 0.05)
            if random.random() < miss_chance:
                self.log(f"Penalità peso arma! L'arma {weapon_name} è troppo pesante e manchi il colpo!")
                return False

        # Calcolo del danno tramite dadi dell'arma o pugno a mani nude
        if weapon:
            damage = weapon.roll_damage()
        else:
            damage = random.randint(1, 3)

        monster.take_damage(damage)
        if monster.is_alive:
            self.log(f"Colpisci {monster.name} con {weapon_name} per {damage} danni! [HP: {monster.hp}/{monster.max_hp}]")
        else:
            self.log(f"Colpisci {monster.name} con {weapon_name} per {damage} danni! [HP: 0/{monster.max_hp}]")
            self.log(f"--> Hai sconfitto {monster.name}!")
            return True
        return False

    def player_fire_ranged(self, player: Player, dungeon, dx: int, dy: int) -> Tuple[bool, Optional[Monster]]:
        """
        Scaglia un proiettile con l'arma a distanza equipaggiata lungo il vettore direzionale (dx, dy).

        Algoritmo di propagazione lineare casella per casella:
        Il proiettile avanza fino a un massimo di 15 caselle. A ogni passo:
        1. Se esce dai confini della mappa o incontra una tessera opaca (muro, porta chiusa), si arresta.
        2. Se incontra un mostro vivo alle coordinate correnti, applica i danni ed esaurisce il colpo.

        Restituisce una tupla (azione_compiuta, mostro_ucciso).
        """
        weapon = player.equipped_ranged
        if not weapon:
            self.log("Nessuna arma a distanza equipaggiata!")
            return False, None

        if not weapon.is_usable():
            self.log(f"Il tuo {weapon.name} ha esaurito i colpi/munizioni!")
            return False, None

        # Consuma una carica/munizione
        weapon.consume_charge()

        # Controllo penalità per peso dell'arma a distanza (es. balestra pesante)
        if weapon.weight > player.str_stat:
            overweight = weapon.weight - player.str_stat
            miss_chance = min(0.75, 0.50 + overweight * 0.05)
            if random.random() < miss_chance:
                self.log(f"Penalità peso! Il tiro con {weapon.name} è goffo e finisce fuori bersaglio!")
                return True, None

        # Propagazione lineare casella per casella
        max_range = 15
        for step in range(1, max_range + 1):
            target_x = player.x + dx * step
            target_y = player.y + dy * step

            if not dungeon.in_bounds(target_x, target_y):
                self.log(f"Scagli un colpo con {weapon.name}, ma svanisce nel buio oltre i confini del dungeon.")
                return True, None

            tile = dungeon.get_tile(target_x, target_y)
            if not tile.transparent:
                self.log(f"Il colpo di {weapon.name} si infrange contro {tile.name.lower()}!")
                return True, None

            # Rilevamento impatto con un mostro presente sulla casella
            for monster in dungeon.monsters:
                if monster.x == target_x and monster.y == target_y and monster.is_alive:
                    damage = weapon.roll_damage()
                    monster.take_damage(damage)
                    ammo_info = f"[{weapon.charges} colpi]" if weapon.charges >= 0 else ""
                    if monster.is_alive:
                        self.log(f"Colpisci a distanza {monster.name} con {weapon.name} per {damage} danni! [HP: {monster.hp}/{monster.max_hp}] {ammo_info}".strip())
                    else:
                        self.log(f"Colpisci a distanza {monster.name} con {weapon.name} per {damage} danni! [HP: 0/{monster.max_hp}] {ammo_info}".strip())
                        self.log(f"--> Hai eliminato {monster.name} con un colpo a distanza!")
                    return True, monster

        self.log(f"Scagli una freccia con {weapon.name}, ma si perde nel buio senza incontrare nemici.")
        return True, None

    def monster_attack_player(self, monster: Monster, player: Player) -> bool:
        """
        Risolve l'attacco di un mostro contro l'eroe in mischia.
        Restituisce True se il giocatore è stato sconfitto (Game Over).
        """
        damage = monster.roll_damage()
        player.take_damage(damage)
        self.log(f"{monster.name} ti attacca infliggendoti {damage} danni!")

        if not player.is_alive:
            self.log("--> SEI STATO SCONFITTO! FINE DELLA PARTITA.")
            return True
        return False

    def cast_spell(self, spell: Spell, player: Player, target_monster: Optional[Monster] = None) -> bool:
        """
        Esegue il lancio di un incantesimo selezionato dal grimorio.

        Verifica preliminarmente la disponibilità di Punti Magia (MP).
        - Se è un incantesimo di guarigione ('heal'), applica la cura all'eroe.
        - Se è un incantesimo offensivo ('damage' o 'fire_damage'), danneggia il mostro bersaglio
          e applica l'effetto continuo di Bruciatura per 3 turni se previsto.
        """
        if player.mp < spell.mp_cost:
            self.log(f"Mana insufficiente! {spell.name} richiede {spell.mp_cost} MP (ne possiedi solo {player.mp}).")
            return False

        player.consume_mp(spell.mp_cost)

        # Caso 1: Incantesimo di Cura
        if spell.spell_type == "heal":
            amount = random.randint(spell.min_effect, spell.max_effect)
            player.heal(amount)
            self.log(f"Lanci {spell.name} recuperando {amount} HP! (HP: {player.hp}/{player.max_hp})")
            return True

        # Caso 2: Incantesimi Offensivi su bersaglio nemico
        if not target_monster or not target_monster.is_alive:
            self.log(f"Nessun bersaglio valido in vista per {spell.name}!")
            return False

        damage = random.randint(spell.min_effect, spell.max_effect)
        target_monster.take_damage(damage)
        if target_monster.is_alive:
            self.log(f"Scagli {spell.name} su {target_monster.name} per {damage} danni! [HP: {target_monster.hp}/{target_monster.max_hp}]")
        else:
            self.log(f"Scagli {spell.name} su {target_monster.name} per {damage} danni! [HP: 0/{target_monster.max_hp}]")

        # Applicazione dello stato Bruciato (Damage-over-Time)
        if spell.spell_type == "fire_damage" and target_monster.is_alive:
            target_monster.fire_turns = 3
            self.log(f"{target_monster.name} viene avvolto dalle fiamme! (Bruciato)")

        if not target_monster.is_alive:
            self.log(f"--> {target_monster.name} è stato distrutto dalla tua magia!")

        return True

    def process_traps_and_status(self, entity: Entity, tile: Tile) -> bool:
        """
        Valuta le interazioni ambientali tra l'entità (giocatore o mostro) e la casella calpestata.

        - Pozza d'acqua (~): estingue le fiamme attive sull'entità.
        - Fiamme (*): infligge combustione e applica 3 turni di bruciatura.
        - Spuntoni (^): infligge un danno fisico immediato di 5 HP.
        - Bruciatura residua: se `fire_turns > 0`, infligge 3 danni da fuoco al termine del turno.

        Restituisce True se l'entità è morta a seguito delle insidie ambientali.
        """
        # L'acqua estingue il fuoco
        if tile.char == CHAR_WATER and entity.fire_turns > 0:
            entity.fire_turns = 0
            name = "Ti" if isinstance(entity, Player) else entity.name
            self.log(f"{name} sei immerso nell'acqua! Le fiamme sono state estinte.")

        # La trappola di fuoco incendia l'entità
        if tile.char == CHAR_FIRE:
            entity.fire_turns = 3
            name = "Ti" if isinstance(entity, Player) else entity.name
            self.log(f"{name} hai calpestato fiamme ardenti prendendo fuoco! (3 turni di bruciatura)")

        # Gli spuntoni infliggono danno fisico istantaneo
        if tile.char == CHAR_SPIKES:
            spike_dmg = 5
            entity.take_damage(spike_dmg)
            name = "Ricevi" if isinstance(entity, Player) else f"{entity.name} subisce"
            self.log(f"Ahi! {name} {spike_dmg} danni dalle punte aguzze degli spuntoni!")

        # Danno periodico da combustione (Damage over Time)
        if entity.fire_turns > 0:
            burn_dmg = 3
            entity.take_damage(burn_dmg)
            name = "Stai" if isinstance(entity, Player) else f"{entity.name} sta"
            self.log(f"🔥 {name} bruciando! (-{burn_dmg} HP, {entity.fire_turns} turni rimasti)")
            entity.fire_turns -= 1

        return not entity.is_alive
