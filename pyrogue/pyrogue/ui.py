"""
Motore di rendering e interfaccia utente grafica in Curses (View) per PyRogue.

Questo modulo costituisce la componente View del pattern MVC:
- Inizializza 18 coppie cromatiche ANSI (`init_colors`) per elementi scenici, mostri, barre e menu.
- Gestisce la grafica a caratteri con double buffering (`erase()` -> composizione -> `refresh()`).
- Esegue il rendering della mappa sotterranea (muri, pavimenti, porte, trappole, scale, forzieri).
- Disegna il pannello di stato laterale (HUD) con statistiche vitali e barre grafiche percentuali.
- Visualizza finestre modali di popup sovrapposte (Overlay per Inventario [I], Grimorio [M], Aiuto [?], Vittoria e Game Over).
"""
import curses
import textwrap
from typing import Optional, Any
from pyrogue.constants import (
    CHAR_PLAYER, CHAR_WALL, CHAR_FLOOR, CHAR_DOOR_CLOSED, CHAR_DOOR_OPEN,
    CHAR_WATER, CHAR_SPIKES, CHAR_FIRE, CHAR_CHEST, CHAR_STAIRS,
    CHAR_GOBLIN, CHAR_ORC, CHAR_DEMON, CHAR_BOSS,
    COLOR_DEFAULT, COLOR_PLAYER, COLOR_WALL, COLOR_FLOOR, COLOR_DOOR,
    COLOR_WATER, COLOR_SPIKES, COLOR_FIRE, COLOR_CHEST, COLOR_STAIRS,
    COLOR_GOBLIN, COLOR_ORC, COLOR_DEMON, COLOR_BOSS,
    COLOR_UI_HEALTH, COLOR_UI_MANA, COLOR_UI_WARN, COLOR_UI_TITLE
)
from pyrogue.engine import GameEngine
from pyrogue.items import Weapon


def init_colors() -> None:
    """Inizializza la tavolozza a colori ANSI e registra le coppie cromatiche usate nel gioco."""
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()

    # Mappatura coppie colore per il mondo e le entità
    curses.init_pair(COLOR_DEFAULT, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_PLAYER, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_WALL, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_FLOOR, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_DOOR, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_WATER, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_SPIKES, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_FIRE, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_CHEST, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_STAIRS, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_GOBLIN, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_ORC, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_DEMON, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_BOSS, curses.COLOR_RED, -1)
    # Coppie colore per l'interfaccia HUD
    curses.init_pair(COLOR_UI_HEALTH, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_UI_MANA, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_UI_WARN, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_UI_TITLE, curses.COLOR_CYAN, -1)


class CursesUI:
    """
    Gestore dell'interfaccia grafica terminale basata su Curses.
    Traduce lo stato del GameEngine in caratteri ed elementi visivi a video.
    """

    def __init__(self, stdscr: Any) -> None:
        self.stdscr = stdscr
        init_colors()
        curses.curs_set(0)          # Nasconde il cursore lampeggiante del terminale
        self.stdscr.nodelay(False)  # Gioco a turni puro: getch() attende la mossa del giocatore
        self.stdscr.keypad(True)    # Abilita la decodifica dei tasti freccia e speciali
        self.active_overlay: Optional[str] = None  # Dialogo modale attivo: None, 'inventory', 'spellbook', 'help'

    def render(self, engine: GameEngine) -> None:
        """
        Ciclo principale di disegno: pulisce il buffer video (`erase`),
        compone tutti gli elementi visivi e applica `refresh` per un aggiornamento atomico.
        """
        self.stdscr.erase()
        max_y, max_x = self.stdscr.getmaxyx()

        if max_y < 24 or max_x < 80:
            try:
                self.stdscr.addstr(0, 0, "Terminal window too small! Resize to at least 80x24.")
            except curses.error:
                pass
            self.stdscr.refresh()
            return

        # 1. Render Header
        self._render_header(engine, max_x)

        # 2. Render Map Viewport
        self._render_map(engine)

        # 3. Render Status Side Panel
        self._render_status_panel(engine)

        # 4. Render Message Log at Bottom
        self._render_log(engine, max_y)

        # 5. Render active overlay dialog if open
        if self.active_overlay == 'inventory':
            self._render_inventory_overlay(engine)
        elif self.active_overlay == 'spellbook':
            self._render_spellbook_overlay(engine)
        elif self.active_overlay == 'help':
            self._render_help_overlay()
        elif engine.victory:
            self._render_victory_overlay(engine)
        elif engine.game_over:
            self._render_game_over_overlay(engine)

        self.stdscr.refresh()

    def _render_header(self, engine: GameEngine, max_x: int):
        title = " PYROGUE - PYTHON TERMINAL ROGUELIKE "
        controls_hint = "[WASD/HJKL]:Move  [F]:Fire  [1/2]:Pots  [I]:Bag  [M]:Magic  [?]:Help  [Q]:Quit"
        try:
            self.stdscr.attron(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(0, 2, title)
            self.stdscr.attroff(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            
            if max_x >= len(title) + len(controls_hint) + 6:
                self.stdscr.addstr(0, max_x - len(controls_hint) - 2, controls_hint)
            else:
                self.stdscr.addstr(1, 2, controls_hint[:max_x - 3])
        except curses.error:
            pass

    def _render_map(self, engine: GameEngine):
        dungeon = engine.dungeon
        offset_y = 2
        offset_x = 2

        # Draw map grid
        for y in range(dungeon.height):
            for x in range(dungeon.width):
                tile = dungeon.get_tile(x, y)
                char = tile.char
                color_pair = COLOR_DEFAULT

                if char == CHAR_WALL:
                    color_pair = COLOR_WALL
                elif char == CHAR_FLOOR:
                    color_pair = COLOR_FLOOR
                elif char in (CHAR_DOOR_CLOSED, CHAR_DOOR_OPEN):
                    color_pair = COLOR_DOOR
                elif char == CHAR_WATER:
                    color_pair = COLOR_WATER
                elif char == CHAR_SPIKES:
                    color_pair = COLOR_SPIKES
                elif char == CHAR_FIRE:
                    color_pair = COLOR_FIRE
                elif char == CHAR_CHEST:
                    color_pair = COLOR_CHEST
                elif char == CHAR_STAIRS:
                    color_pair = COLOR_STAIRS

                try:
                    self.stdscr.attron(curses.color_pair(color_pair))
                    self.stdscr.addch(offset_y + y, offset_x + x, char)
                    self.stdscr.attroff(curses.color_pair(color_pair))
                except curses.error:
                    pass

        # Draw monsters
        for monster in dungeon.monsters:
            if monster.is_alive:
                try:
                    self.stdscr.attron(curses.color_pair(monster.color) | curses.A_BOLD)
                    self.stdscr.addch(offset_y + monster.y, offset_x + monster.x, monster.char)
                    self.stdscr.attroff(curses.color_pair(monster.color) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw player
        player = engine.player
        try:
            self.stdscr.attron(curses.color_pair(COLOR_PLAYER) | curses.A_BOLD)
            self.stdscr.addch(offset_y + player.y, offset_x + player.x, player.char)
            self.stdscr.attroff(curses.color_pair(COLOR_PLAYER) | curses.A_BOLD)
        except curses.error:
            pass

    def _render_status_panel(self, engine: GameEngine):
        max_y, max_x = self.stdscr.getmaxyx()
        offset_x = 63
        offset_y = 2
        p = engine.player
        avail_w = max(14, max_x - offset_x - 1)

        lines = []
        lines.append(("=== PLAYER ===", COLOR_UI_TITLE, True))
        
        # HP Bar
        hp_pct = max(0, p.hp) / p.max_hp
        bar_len = 6 if avail_w < 20 else 10
        filled = int(hp_pct * bar_len)
        hp_bar = f"HP:[{'█'*filled}{'░'*(bar_len-filled)}]{p.hp}/{p.max_hp}"
        lines.append((hp_bar, COLOR_UI_HEALTH, True))

        # MP Bar
        mp_pct = max(0, p.mp) / p.max_mp
        filled_mp = int(mp_pct * bar_len)
        mp_bar = f"MP:[{'█'*filled_mp}{'░'*(bar_len-filled_mp)}]{p.mp}/{p.max_mp}"
        lines.append((mp_bar, COLOR_UI_MANA, True))

        lines.append((f"STR:{p.str_stat} SPD:{p.spd}", COLOR_DEFAULT, False))
        lines.append(("", COLOR_DEFAULT, False))

        # Equipment
        lines.append(("=== WEAPONS ===", COLOR_UI_TITLE, True))
        
        melee_str = "None"
        is_heavy = False
        if p.equipped_melee:
            melee_str = f"{p.equipped_melee.name} (W:{p.equipped_melee.weight})"
            if p.equipped_melee.weight > p.str_stat:
                is_heavy = True
        
        lines.append((f"M: {melee_str}" if avail_w > 18 else f"M:{melee_str}", COLOR_UI_WARN if is_heavy else COLOR_DEFAULT, is_heavy))
        if is_heavy and avail_w >= 18:
            lines.append(("  ⚠️ HEAVY PENALTY!", COLOR_UI_WARN, True))

        ranged_str = "None"
        is_ranged_heavy = False
        if p.equipped_ranged:
            ranged_str = f"{p.equipped_ranged.name} ({p.equipped_ranged.charges})"
            if p.equipped_ranged.weight > p.str_stat:
                is_ranged_heavy = True
        lines.append((f"R: {ranged_str}" if avail_w > 18 else f"R:{ranged_str}", COLOR_UI_WARN if is_ranged_heavy else COLOR_DEFAULT, is_ranged_heavy))

        # Facing / Ranged fire direction [F]
        facing_map = {
            (0, -1): "↑ North",
            (0, 1): "↓ South",
            (1, 0): "→ East",
            (-1, 0): "← West",
            (1, -1): "↗ NE",
            (-1, -1): "↖ NW",
            (1, 1): "↘ SE",
            (-1, 1): "↙ SW",
        }
        dir_text = facing_map.get((p.last_dx, p.last_dy), "→ East")
        lines.append((f"[F] Shoot: {dir_text}", COLOR_UI_TITLE, True))
        lines.append(("", COLOR_DEFAULT, False))

        # Items
        lines.append(("=== POTIONS ===", COLOR_UI_TITLE, True))
        lines.append((f"[1] HP Pot: {p.hp_potions}", COLOR_DEFAULT, False))
        lines.append((f"[2] MP Pot: {p.mp_potions}", COLOR_DEFAULT, False))
        lines.append(("", COLOR_DEFAULT, False))

        # Status & Level
        lines.append(("=== PROGRESS ===", COLOR_UI_TITLE, True))
        lines.append((f"Depth: {engine.current_depth}", COLOR_DEFAULT, False))
        if engine.is_boss_level:
            lines.append(("🔥 BOSS LEVEL! 🔥", COLOR_UI_WARN, True))
            boss = next((m for m in engine.dungeon.monsters if m.monster_type == "boss"), None)
            if boss and boss.is_alive:
                b_pct = max(0.0, boss.hp / boss.max_hp)
                b_filled = int(b_pct * bar_len)
                b_bar = f"B:[{'█'*b_filled}{'░'*(bar_len-b_filled)}]{boss.hp}/{boss.max_hp}"
                lines.append((b_bar, COLOR_UI_WARN, True))
        else:
            lines.append((f"To Boss: {engine.remaining_dungeons}", COLOR_DEFAULT, False))

        if p.fire_turns > 0:
            lines.append((f"🔥 BURNING ({p.fire_turns})", COLOR_UI_WARN, True))

        for idx, (text, color, bold) in enumerate(lines):
            try:
                attr = curses.color_pair(color)
                if bold:
                    attr |= curses.A_BOLD
                self.stdscr.attron(attr)
                self.stdscr.addstr(offset_y + idx, offset_x, text[:avail_w])
                self.stdscr.attroff(attr)
            except curses.error:
                pass

    def _render_log(self, engine: GameEngine, max_y: int):
        log_y = 22
        log_h = max(2, max_y - log_y - 1)
        
        try:
            self.stdscr.attron(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(log_y - 1, 2, "--- LOG ---")
            self.stdscr.attroff(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
        except curses.error:
            pass

        recent_msgs = engine.combat.message_log[-log_h:]
        for idx, msg in enumerate(recent_msgs):
            try:
                self.stdscr.addstr(log_y + idx, 2, msg[:76])
            except curses.error:
                pass

    def _render_inventory_overlay(self, engine: GameEngine):
        p = engine.player
        max_y, max_x = self.stdscr.getmaxyx()
        win_w = min(78, max_x - 2) if max_x >= 80 else max(40, max_x - 2)
        win_h = min(19, max_y - 2) if max_y >= 21 else max(14, max_y - 2)
        sy = max(1, (max_y - win_h) // 2)
        sx = max(1, (max_x - win_w) // 2)

        self._draw_box(sy, sx, win_h, win_w, " INVENTORY / WEAPONS BAG ")
        
        try:
            # 1. Player Stats Header
            stats_str = f"PLAYER STATS:  HP: {p.hp}/{p.max_hp}  |  MP: {p.mp}/{p.max_mp}  |  STR (Forza): {p.str_stat}  |  SPD: {p.spd}"
            self.stdscr.attron(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(sy + 2, sx + 2, stats_str[:win_w - 4])
            self.stdscr.attroff(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)

            weight_info = f"Limite Peso senza malus: {p.str_stat} STR (Armi con Peso > STR subiscono miss 50%+)"
            self.stdscr.addstr(sy + 3, sx + 2, weight_info[:win_w - 4])
            self.stdscr.addstr(sy + 4, sx + 2, "-" * (win_w - 4))

            # 2. Equipped Weapons
            if p.equipped_melee:
                m_heavy = p.equipped_melee.weight > p.str_stat
                m_tag = " ⚠️[PESANTE]" if m_heavy else ""
                melee_info = f"Mischia : {p.equipped_melee.name} (Danno:{p.equipped_melee.min_dmg}-{p.equipped_melee.max_dmg} | Peso:{p.equipped_melee.weight}){m_tag}"
            else:
                m_heavy = False
                melee_info = "Mischia : (Nessuna)"

            if m_heavy:
                self.stdscr.attron(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
                self.stdscr.addstr(sy + 5, sx + 2, melee_info[:win_w - 4])
                self.stdscr.attroff(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
            else:
                self.stdscr.addstr(sy + 5, sx + 2, melee_info[:win_w - 4])

            if p.equipped_ranged:
                r_heavy = p.equipped_ranged.weight > p.str_stat
                r_tag = " ⚠️[PESANTE]" if r_heavy else ""
                ranged_info = f"A Dist. : {p.equipped_ranged.name} (Munizioni:{p.equipped_ranged.charges} | Danno:{p.equipped_ranged.min_dmg}-{p.equipped_ranged.max_dmg} | Peso:{p.equipped_ranged.weight}){r_tag}"
            else:
                r_heavy = False
                ranged_info = "A Dist. : (Nessuna)"

            if r_heavy:
                self.stdscr.attron(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
                self.stdscr.addstr(sy + 6, sx + 2, ranged_info[:win_w - 4])
                self.stdscr.attroff(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
            else:
                self.stdscr.addstr(sy + 6, sx + 2, ranged_info[:win_w - 4])

            self.stdscr.addstr(sy + 7, sx + 2, "-" * (win_w - 4))
            self.stdscr.addstr(sy + 8, sx + 2, "Weapons in Bag (Press number key [1]-[6] to equip):")

            # 3. Weapons in Bag with Weight check
            if not p.weapons_bag:
                self.stdscr.addstr(sy + 10, sx + 4, "(No extra weapons in bag - find chests in the dungeon)")
            else:
                for idx, w in enumerate(p.weapons_bag[:6]):
                    is_heavy = w.weight > p.str_stat
                    tag = " ⚠️[PESANTE]" if is_heavy else " [OK]"
                    w_str = f"[{idx+1}] {w}{tag}"
                    
                    if is_heavy:
                        self.stdscr.attron(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
                        self.stdscr.addstr(sy + 10 + idx, sx + 2, w_str[:win_w - 4])
                        self.stdscr.attroff(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(sy + 10 + idx, sx + 2, w_str[:win_w - 4])

            self.stdscr.addstr(sy + win_h - 2, sx + 2, "Premi [I] o [ESC] per chiudere")
        except curses.error:
            pass

    def _render_spellbook_overlay(self, engine: GameEngine):
        p = engine.player
        max_y, max_x = self.stdscr.getmaxyx()
        win_w = min(78, max_x - 2) if max_x >= 80 else max(40, max_x - 2)
        win_h = min(17, max_y - 2) if max_y >= 19 else max(13, max_y - 2)
        sy = max(1, (max_y - win_h) // 2)
        sx = max(1, (max_x - win_w) // 2)

        self._draw_box(sy, sx, win_h, win_w, " SPELLBOOK / MAGIC ")
        
        try:
            self.stdscr.attron(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(sy + 2, sx + 2, f"MAGIKA DISPONIBILE: {p.mp}/{p.max_mp} MP   (Premi [3]-[5] per lanciare):"[:win_w - 4])
            self.stdscr.attroff(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(sy + 3, sx + 2, "-" * (win_w - 4))

            cur_y = sy + 4
            for idx, spell in enumerate(p.known_spells):
                if cur_y >= sy + win_h - 3:
                    break
                has_mana = p.mp >= spell.mp_cost
                mana_tag = "" if has_mana else " ⚠️[SENZA MANA]"
                
                if spell.spell_type == 'heal':
                    eff_str = f"Cura: {spell.min_effect}-{spell.max_effect} HP"
                elif spell.spell_type == 'fire_damage':
                    eff_str = f"Danno: {spell.min_effect}-{spell.max_effect} (Fuoco)"
                else:
                    eff_str = f"Danno: {spell.min_effect}-{spell.max_effect}"

                spell_str = f"[{idx+3}] {spell.name} (Costo MP: {spell.mp_cost} | {eff_str}){mana_tag}"
                
                if not has_mana:
                    self.stdscr.attron(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
                    self.stdscr.addstr(cur_y, sx + 3, spell_str[:win_w - 5])
                    self.stdscr.attroff(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
                else:
                    self.stdscr.attron(curses.color_pair(COLOR_UI_MANA) | curses.A_BOLD)
                    self.stdscr.addstr(cur_y, sx + 3, spell_str[:win_w - 5])
                    self.stdscr.attroff(curses.color_pair(COLOR_UI_MANA) | curses.A_BOLD)
                cur_y += 1

                wrapped = textwrap.wrap(f"-> {spell.description}", width=win_w - 8)
                for w_line in wrapped:
                    if cur_y >= sy + win_h - 2:
                        break
                    self.stdscr.addstr(cur_y, sx + 5, w_line[:win_w - 7])
                    cur_y += 1
                cur_y += 1

            self.stdscr.addstr(sy + win_h - 2, sx + 2, "Premi [M] o [ESC] per chiudere")
        except curses.error:
            pass

    def _render_help_overlay(self):
        max_y, max_x = self.stdscr.getmaxyx()
        win_w = min(68, max_x - 2) if max_x >= 70 else max(40, max_x - 2)
        win_h = min(19, max_y - 2) if max_y >= 21 else max(14, max_y - 2)
        sy = max(1, (max_y - win_h) // 2)
        sx = max(1, (max_x - win_w) // 2)

        self._draw_box(sy, sx, win_h, win_w, " GAME HELP & LEGEND ")
        
        help_text = [
            "Controls:",
            "  Move/Melee Attack: Arrow Keys / WASD / HJKL",
            "  [F] Fire Ranged Weapon (Straight in facing dir)",
            "  [1] Drink HP Potion    [2] Drink MP Potion",
            "  [I] Open Inventory Bag [M] Open Spellbook",
            "  [?] Toggle Help        [Q] Quit Game",
            "",
            "Map Legend:",
            "  @ Player   # Wall   . Floor   + Door   > Stairs",
            "  ~ Water (cleanses Fire)   ^ Spikes (instant dmg)",
            "  * Fire Trap (burns 3 turns)   $ Chest (weapons/potions)",
            "",
            "Monsters & Weapon Weight:",
            "  g Goblin (Fast)  O Orc (Strong)  D Demon  B Boss",
            "  Weight > STR: Weapon hit penalty!"
        ]
        
        for idx, line in enumerate(help_text):
            try:
                self.stdscr.addstr(sy + 2 + idx, sx + 3, line[:win_w - 5])
            except curses.error:
                pass

        try:
            self.stdscr.addstr(sy + win_h - 2, sx + 2, "Premi [H] o [ESC] per chiudere")
        except curses.error:
            pass

    def _render_game_over_overlay(self, engine: GameEngine):
        max_y, max_x = self.stdscr.getmaxyx()
        win_w, win_h = 46, 10
        sy = max(1, (max_y - win_h) // 2)
        sx = max(1, (max_x - win_w) // 2)

        self._draw_box(sy, sx, win_h, win_w, " GAME OVER ")
        try:
            self.stdscr.attron(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
            self.stdscr.addstr(sy + 3, sx + 6, "YOU WERE SLAIN IN THE DUNGEON!")
            self.stdscr.attroff(curses.color_pair(COLOR_UI_WARN) | curses.A_BOLD)
            self.stdscr.addstr(sy + 5, sx + 6, f"Reached Depth: {engine.current_depth}")
            self.stdscr.addstr(sy + 7, sx + 6, "Premi [Q] o [ENTER] per uscire")
        except curses.error:
            pass

    def _render_victory_overlay(self, engine: GameEngine):
        max_y, max_x = self.stdscr.getmaxyx()
        win_w, win_h = 50, 10
        sy = max(1, (max_y - win_h) // 2)
        sx = max(1, (max_x - win_w) // 2)

        self._draw_box(sy, sx, win_h, win_w, " VICTORY! ")
        try:
            self.stdscr.attron(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(sy + 3, sx + 4, "👑 YOU DEFEATED THE INFERNAL DEMON LORD!")
            self.stdscr.attroff(curses.color_pair(COLOR_UI_TITLE) | curses.A_BOLD)
            self.stdscr.addstr(sy + 5, sx + 6, "You conquered the dungeon!")
            self.stdscr.addstr(sy + 7, sx + 6, "Premi [Q] o [ENTER] per uscire")
        except curses.error:
            pass

    def _draw_box(self, y: int, x: int, h: int, w: int, title: str):
        try:
            # Clear interior
            for i in range(h):
                self.stdscr.addstr(y + i, x, " " * w)

            # Border
            self.stdscr.attron(curses.color_pair(COLOR_UI_TITLE))
            self.stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
            for i in range(1, h - 1):
                self.stdscr.addstr(y + i, x, "|")
                self.stdscr.addstr(y + i, x + w - 1, "|")
            self.stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")

            # Title
            if title:
                t_str = f" {title} "
                self.stdscr.addstr(y, x + (w - len(t_str)) // 2, t_str, curses.A_BOLD)
            self.stdscr.attroff(curses.color_pair(COLOR_UI_TITLE))
        except curses.error:
            pass
