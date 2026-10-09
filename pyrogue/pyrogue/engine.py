"""
Game Engine e macchina a stati del mondo di gioco in PyRogue.

Questo modulo orchestra l'intera logica di gioco (Controller/Model):
- Gestione della progressione attraverso i 5 piani del dungeon e transizione all'arena del Boss.
- Meccanica di movimento dell'eroe, apertura porte, saccheggio forzieri e discesa scale.
- Ciclo a turni asincrono basato su accumulatore di velocità (Action Points).
- Intelligenza Artificiale (AI) dei mostri con inseguimento a 8 direzioni e abilità speciale del Boss.
- Tracciamento della linea di vista ottica (Bresenham LOS) e autotargeting magico tramite prodotto scalare.
"""
import math
import random
from typing import List, Tuple, Optional
from pyrogue.constants import (
    INITIAL_DUNGEONS, CHAR_CHEST, CHAR_DOOR_CLOSED, CHAR_STAIRS, CHAR_FLOOR
)
from pyrogue.entities import Player, Monster
from pyrogue.dungeon_map import DungeonMap, generate_dungeon
from pyrogue.combat import CombatEngine
from pyrogue.items import generate_random_weapon
from pyrogue.tile import make_floor, make_door
from pyrogue.magic import Spell


class GameEngine:
    """
    Motore centrale del gioco: gestisce lo stato del dungeon, dell'eroe e dei mostri.

    Attributi principali:
    - `remaining_dungeons`: Piani normali residui prima di accedere al livello del Boss finale.
    - `current_depth`: Indice di profondità attuale (da 1 a 5).
    - `player`: L'istanza dell'eroe.
    - `combat`: Il motore di risoluzione scontri, magie e registro messaggi.
    - `dungeon`: La mappa del piano sotterraneo correntemente esplorato.
    - `game_over`: Flag impostato a True quando i Punti Vita dell'eroe si azzerano.
    - `victory`: Flag impostato a True quando il Boss infernale viene sconfitto.
    """

    def __init__(self):
        self.remaining_dungeons: int = INITIAL_DUNGEONS
        self.current_depth: int = 1
        self.player: Player = Player()
        self.combat: CombatEngine = CombatEngine()
        self.game_over: bool = False
        self.victory: bool = False
        
        # Carica il primo livello procedurale del dungeon
        self.dungeon: DungeonMap = generate_dungeon(
            depth=self.current_depth,
            is_boss_level=False
        )
        self.player.x, self.player.y = self.dungeon.player_start
        self.combat.log("Benvenuto in PyRogue! Esplora il dungeon e sconfiggi il Boss infernale!")
        self.combat.log(f"Livelli mancanti prima del Boss: {self.remaining_dungeons}")

    @property
    def is_boss_level(self) -> bool:
        """Restituisce True se l'eroe ha raggiunto il quinto e ultimo piano (livello Boss)."""
        return self.remaining_dungeons == 0

    def move_player(self, dx: int, dy: int) -> bool:
        """
        Elabora il movimento o l'interazione dell'eroe nella direzione (dx, dy).

        Sequenza di controllo:
        1. Se c'è un mostro nella cella di destinazione -> esegue un attacco in mischia.
        2. Se c'è una porta chiusa (+) -> la apre trasformandola in porta aperta (/).
        3. Se c'è un muro o ostacolo intransitabile -> blocca il passo e notifica l'impatto.
        4. Se la cella è calpestabile -> sposta l'eroe alle nuove coordinate.
        5. Se la cella contiene un forziere ($) -> ne preleva il tesoro.
        6. Se la cella contiene trappole o fiamme -> applica i danni ambientali.
        7. Se la cella contiene le scale (>) -> scende al piano successivo.
        8. Consuma il turno dell'eroe e avvia il ciclo di azione dei mostri (`_end_player_turn`).
        """
        if self.game_over or self.victory:
            return False

        # Memorizza l'orientamento dello sguardo dell'eroe per il tiro a distanza e le magie
        if dx != 0 or dy != 0:
            self.player.last_dx = dx
            self.player.last_dy = dy

        target_x = self.player.x + dx
        target_y = self.player.y + dy

        if not self.dungeon.in_bounds(target_x, target_y):
            return False

        # 1. Collisione con un Mostro -> Attacco in mischia
        monster = self._get_monster_at(target_x, target_y)
        if monster:
            died = self.combat.player_attack_monster(self.player, monster)
            if died:
                self.dungeon.monsters.remove(monster)
                if monster.monster_type == "boss":
                    self.victory = True
                    self.combat.log("👑 HAI SCONFITTO IL SIGNORE DEI DEMONI! LA VITTORIA È TUA!")
            self._end_player_turn()
            return True

        # 2. Interazione con Porta Chiusa -> Apertura porta
        target_tile = self.dungeon.get_tile(target_x, target_y)
        if target_tile.char == CHAR_DOOR_CLOSED:
            self.dungeon.set_tile(target_x, target_y, make_door(opened=True))
            self.combat.log("Hai aperto una porta in legno.")
            self._end_player_turn()
            return True

        # 3. Controllo transitabilità fisica (muri, ostacoli)
        if not target_tile.walkable:
            self.combat.log("Ahi! Sbatti contro una parete di pietra grezza.")
            return False

        # 4. Spostamento dell'eroe sulla nuova tessera
        self.player.x = target_x
        self.player.y = target_y

        # 5. Saccheggio forzieri
        if target_tile.char == CHAR_CHEST:
            self._loot_chest(target_x, target_y)

        # 6. Attivazione trappole e terreno sul giocatore
        player_died = self.combat.process_traps_and_status(self.player, target_tile)
        if player_died:
            self.game_over = True
            return True

        # 7. Discesa scale verso il piano successivo
        if target_tile.char == CHAR_STAIRS:
            self.descend_stairs()
            return True

        self._end_player_turn()
        return True

    def fire_ranged(self) -> bool:
        """
        Scaglia un colpo con l'arma a distanza equipaggiata nella direzione dell'ultimo passo compiuto.
        Se l'eroe non si è ancora mosso, spara verso Est (dx=1, dy=0).
        """
        if self.game_over or self.victory:
            return False

        if not self.player.equipped_ranged:
            self.combat.log("Nessuna arma a distanza equipaggiata!")
            return False

        if not self.player.equipped_ranged.is_usable():
            self.combat.log(f"Il tuo {self.player.equipped_ranged.name} ha esaurito i colpi!")
            return False

        dx, dy = self.player.last_dx, self.player.last_dy
        if dx == 0 and dy == 0:
            dx, dy = 1, 0

        action_taken, target_monster = self.combat.player_fire_ranged(
            self.player, self.dungeon, dx, dy
        )

        if action_taken:
            if target_monster and not target_monster.is_alive:
                if target_monster in self.dungeon.monsters:
                    self.dungeon.monsters.remove(target_monster)
                if target_monster.monster_type == "boss":
                    self.victory = True
                    self.combat.log("👑 HAI SCONFITTO IL SIGNORE DEI DEMONI CON UN TIRO A DISTANZA! VITTORIA!")
            self._end_player_turn()
            return True
        return False

    def use_hp_potion(self) -> bool:
        """Beve una pozione curativa ripristinando 15 Punti Ferita e consuma il turno."""
        if self.player.hp_potions <= 0:
            self.combat.log("Nessuna pozione di guarigione rimasta!")
            return False
        if self.player.hp >= self.player.max_hp:
            self.combat.log("I tuoi Punti Ferita sono già al massimo!")
            return False
        self.player.hp_potions -= 1
        self.player.heal(15)
        self.combat.log(f"Bevi una Pozione Curativa! (+15 HP, Salute: {self.player.hp}/{self.player.max_hp})")
        self._end_player_turn()
        return True

    def use_mp_potion(self) -> bool:
        """Beve una pozione di mana ripristinando 10 Punti Magia e consuma il turno."""
        if self.player.mp_potions <= 0:
            self.combat.log("Nessuna pozione di mana rimasta!")
            return False
        if self.player.mp >= self.player.max_mp:
            self.combat.log("La tua riserva di Mana è già al massimo!")
            return False
        self.player.mp_potions -= 1
        self.player.restore_mp(10)
        self.combat.log(f"Bevi una Pozione di Mana! (+10 MP, Magia: {self.player.mp}/{self.player.max_mp})")
        self._end_player_turn()
        return True

    def cast_player_spell(self, spell_idx: int) -> bool:
        """
        Lancia un incantesimo dall'elenco delle magie note dell'eroe.
        Se l'incantesimo è offensivo, seleziona automaticamente il bersaglio ottimale con `_find_nearest_monster()`.
        """
        if spell_idx < 0 or spell_idx >= len(self.player.known_spells):
            return False
        spell = self.player.known_spells[spell_idx]
        
        target_monster = None
        if spell.spell_type in ("damage", "fire_damage"):
            target_monster = self._find_nearest_monster()
            if not target_monster:
                self.combat.log(f"Nessun nemico in vista a tiro per {spell.name}!")
                return False

        cast_success = self.combat.cast_spell(spell, self.player, target_monster)
        if cast_success:
            if target_monster and not target_monster.is_alive:
                self.dungeon.monsters.remove(target_monster)
                if target_monster.monster_type == "boss":
                    self.victory = True
                    self.combat.log("👑 HAI SCONFITTO IL SIGNORE DEI DEMONI CON LA MAGIA! VITTORIA!")
            self._end_player_turn()
            return True
        return False

    def descend_stairs(self):
        """
        Gestisce la discesa al piano successivo o all'arena del Boss finale.

        Ricompense di progressione per il giocatore:
        - +2 Forza permanente (STR)
        - +1 Mana massimo (Max MP)
        - +5 Punti Ferita massimi (Max HP) con parziale recupero di salute e mana.
        """
        if self.remaining_dungeons > 0:
            self.remaining_dungeons -= 1
        
        self.current_depth += 1
        self.player.max_mp += 1
        self.player.str_stat += 2
        self.player.max_hp += 5
        self.player.hp = min(self.player.max_hp, self.player.hp + 10)
        self.player.mp = min(self.player.max_mp, self.player.mp + 2)

        boss_room = (self.remaining_dungeons == 0)
        self.dungeon = generate_dungeon(
            depth=self.current_depth,
            is_boss_level=boss_room
        )
        self.player.x, self.player.y = self.dungeon.player_start

        if boss_room:
            self.combat.log("⚠️ SEI ENTRATO NELL'ARENA DEL BOSS FINALE! SCONFIGGI IL SIGNORE DEI DEMONI!")
        else:
            self.combat.log(f"Sei sceso alla profondità {self.current_depth}! (+2 FOR, +1 Max MP, +5 Max HP)")
            self.combat.log(f"Piani rimanenti prima del Boss: {self.remaining_dungeons}")

    def _loot_chest(self, x: int, y: int):
        """Apre un forziere presente alle coordinate (x, y) e ne estrae il contenuto casuale."""
        self.dungeon.set_tile(x, y, make_floor())
        if random.random() < 0.6:
            weapon = generate_random_weapon(self.current_depth)
            self.player.weapons_bag.append(weapon)
            self.combat.log(f"🎁 Hai aperto un forziere e trovato: {weapon.name}!")
        else:
            p_type = random.choice(["hp", "mp", "both", "str"])
            if p_type == "str":
                self.player.str_stat += 2
                self.combat.log(f"💪 Hai aperto un forziere e bevuto un Elisir di Forza! (+2 FOR! Forza: {self.player.str_stat})")
            elif p_type == "hp":
                self.player.hp_potions += 1
                self.combat.log("🎁 Hai aperto un forziere e trovato una Pozione Curativa!")
            elif p_type == "mp":
                self.player.mp_potions += 1
                self.combat.log("🎁 Hai aperto un forziere e trovato una Pozione di Mana!")
            else:
                self.player.hp_potions += 1
                self.player.mp_potions += 1
                self.combat.log("🎁 Hai aperto un forziere e trovato Pozioni di Cura e Mana!")

    def _check_boss_victory(self):
        """Verifica se il Boss finale è stato sconfitto nel livello della cittadella."""
        if self.is_boss_level and not self.victory:
            boss_alive = any(m.monster_type == "boss" and m.is_alive for m in self.dungeon.monsters)
            if not boss_alive:
                self.victory = True
                self.combat.log("👑 HAI SCONFITTO IL SIGNORE DEI DEMONI! LA VITTORIA È TUA!")

    def _end_player_turn(self):
        """
        Ciclo dei turni dei mostri con sistema ad accumulatore di velocità (Action Points).

        Funzionamento matematico:
        - A ogni azione del giocatore, ciascun mostro accumula energia pari al suo valore di SPD (`energy += spd`).
        - La soglia per compiere un'azione autonoma è fissata a 10 punti energia.
        - Se un mostro accumula 12 punti energia (es. Goblin), ne spende 10 per agire (`energy -= 10`)
          e conserva i 2 punti residui per il turno successivo: ogni 5 turni dell'eroe, il Goblin agirà 6 volte!
        - Se un mostro è lento (es. Orco con SPD 7), agirà solo 7 volte ogni 10 turni del giocatore.
        """
        if self.game_over or self.victory:
            return

        for monster in list(self.dungeon.monsters):
            if not monster.is_alive:
                continue

            monster.energy += monster.spd
            while monster.energy >= 10:
                monster.energy -= 10
                self._update_monster_ai(monster)
                if not self.player.is_alive:
                    self.game_over = True
                    break
                if self.victory:
                    break

        self._check_boss_victory()

    def _update_monster_ai(self, monster: Monster):
        """
        Logica decisionale dell'AI per un singolo mostro:
        1. Se adiacente all'eroe (distanza <= 1.5 caselle) -> esegue un attacco in mischia.
        2. Abilità speciale del Boss finale -> scaglia un Dardo Infernale a distanza con linea di vista libera.
        3. Inseguimento tattico (*Best-First Search*): calcola la distanza euclidea per ciascuna
           delle 8 direzioni adiacenti, ordinandole dalla più vicina all'eroe alla più lontana,
           e compie il primo passo calpestabile libero.
        4. Risolve eventuali trappole calpestate dal mostro.
        """
        dist = math.hypot(self.player.x - monster.x, self.player.y - monster.y)
        
        # 1. Attacco in mischia se adiacente all'eroe
        if dist <= 1.5:
            self.combat.monster_attack_player(monster, self.player)
            return

        # 2. Abilità speciale a distanza del Boss (Dardo di Fuoco Infernale)
        if (monster.monster_type == "boss" and 
            dist <= 12.0 and 
            self._has_line_of_sight(monster.x, monster.y, self.player.x, self.player.y) and 
            random.random() < 0.25):
            boss_spell_dmg = random.randint(4, 7)
            self.player.take_damage(boss_spell_dmg)
            self.combat.log(f"🔥 Il Signore dei Demoni scaglia un Dardo Infernale per {boss_spell_dmg} danni! (HP: {self.player.hp}/{self.player.max_hp})")
            if not self.player.is_alive:
                self.game_over = True
                self.combat.log("☠️ Sei stato incenerito dalle fiamme del Signore dei Demoni! FINE PARTITA.")
            return

        # 3. Raggio di avvistamento: l'intera arena (60 caselle) nel livello Boss, altrimenti 12 caselle
        detection_range = 60.0 if (self.is_boss_level or getattr(monster, 'is_alert', False)) else 12.0

        if dist <= detection_range:
            monster.is_alert = True

            # Inseguimento Best-First: ordina le 8 direzioni cardinali/diagonali per distanza euclidea minima dall'eroe
            directions = [
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1)
            ]
            directions.sort(key=lambda d: math.hypot((monster.x + d[0]) - self.player.x, (monster.y + d[1]) - self.player.y))

            for mx, my in directions:
                nx, ny = monster.x + mx, monster.y + my
                # Verifica che la casella sia calpestabile e non occupata da altri mostri o dall'eroe
                if (self.dungeon.is_walkable(nx, ny) and 
                    not (nx == self.player.x and ny == self.player.y) and
                    not any(m.x == nx and m.y == ny for m in self.dungeon.monsters if m is not monster and m.is_alive)):
                    monster.x = nx
                    monster.y = ny
                    
                    # Interazione del mostro con trappole sul terreno
                    tile = self.dungeon.get_tile(nx, ny)
                    m_died = self.combat.process_traps_and_status(monster, tile)
                    if m_died and monster in self.dungeon.monsters:
                        self.dungeon.monsters.remove(monster)
                        self._check_boss_victory()
                    break

    def _get_monster_at(self, x: int, y: int) -> Optional[Monster]:
        """Restituisce il mostro vivo presente alle coordinate (x, y) oppure None."""
        for monster in self.dungeon.monsters:
            if monster.x == x and monster.y == y and monster.is_alive:
                return monster
        return None

    def _has_line_of_sight(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        """
        Verifica se esiste una linea di vista libera (Line of Sight) tra (x0, y0) e (x1, y1)
        tramite l'algoritmo di tracciamento lineare di Bresenham.
        Restituisce False se la linea retta incontra una tessera opaca (muro, porta chiusa).
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2

        for _ in range(n):
            if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                if not self.dungeon.in_bounds(x, y):
                    return False
                tile = self.dungeon.get_tile(x, y)
                if not tile.transparent:
                    return False

            if (x, y) == (x1, y1):
                break

            if error > 0:
                x += x_inc
                error -= dy
            elif error < 0:
                y += y_inc
                error += dx
            else:
                x += x_inc
                y += y_inc
                error += dx - dy

        return True

    def _find_nearest_monster(self) -> Optional[Monster]:
        """
        Seleziona il bersaglio nemico ottimale per il lancio degli incantesimi:
        1. Deve essere vivo e trovarsi entro il raggio massimo dell'incantesimo (15 caselle, 30 nel Boss).
        2. Deve avere linea di vista ottica libera (non schermato da muri o porte chiuse).
        3. Priorità direzionale con Prodotto Scalare (Dot Product): privilegia i mostri allineati
           al cono visivo frontale dell'eroe (`dot > 0.25`).
        4. In assenza di mostri frontali, sceglie il bersaglio visibile più vicino in assoluto.
        """
        p_dx, p_dy = self.player.last_dx, self.player.last_dy
        max_spell_range = 30.0 if self.is_boss_level else 15.0

        visible_candidates = []
        for monster in self.dungeon.monsters:
            if not monster.is_alive:
                continue
            dist = math.hypot(self.player.x - monster.x, self.player.y - monster.y)
            if dist <= max_spell_range and self._has_line_of_sight(self.player.x, self.player.y, monster.x, monster.y):
                # Calcolo del prodotto scalare normalizzato con il vettore di sguardo dell'eroe
                v_x = (monster.x - self.player.x) / dist
                v_y = (monster.y - self.player.y) / dist
                f_dist = math.hypot(p_dx, p_dy)
                dot = (v_x * (p_dx / f_dist)) + (v_y * (p_dy / f_dist)) if f_dist > 0 else 0.0
                visible_candidates.append((monster, dist, dot))

        if not visible_candidates:
            return None

        # Filtra i mostri nel cono visivo frontale (dot product > 0.25)
        in_front = [m for m in visible_candidates if m[2] > 0.25]
        if in_front:
            # Seleziona il mostro frontale più vicino
            in_front.sort(key=lambda item: item[1])
            return in_front[0][0]

        # Altrimenti seleziona il mostro visibile più vicino in assoluto a 360°
        visible_candidates.sort(key=lambda item: item[1])
        return visible_candidates[0][0]
