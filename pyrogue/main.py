"""
Entrypoint e controller principale di PyRogue (Roguelike da terminale in Curses).

Questo modulo avvia l'applicazione e orchestra il ciclo a turni:
- Avvio sicuro dell'ambiente Curses tramite `curses.wrapper()`.
- Gestione del loop principale degli eventi con input sincrono a turni (`stdscr.getch()`).
- Instradamento dei comandi di movimento (WASD, frecce direzionali, HJKL, diagonali YUBN).
- Gestione degli overlay modali sovrapposti (Inventario [I], Grimorio [M], Guida rapida [?]).
- Attivazione dei tasti rapidi per armi a distanza ([F]), pozioni ([1], [2]) e magie ([3], [4], [5]).
"""
import curses
import sys
from typing import Any
from pyrogue.engine import GameEngine
from pyrogue.ui import CursesUI


def main(stdscr: Any) -> None:
    """
    Funzione principale eseguita all'interno del wrapper protetto di Curses.
    Inizializza il Model (GameEngine) e la View (CursesUI), quindi entra nel Game Loop a turni.
    """
    engine = GameEngine()
    ui = CursesUI(stdscr)

    while True:
        # 1. Fase di rendering grafico (View disegna lo stato attuale del Model)
        ui.render(engine)

        # 2. Lettura sincrona del tasto premuto dal giocatore (attesa dell'input a turni)
        key = stdscr.getch()

        if key == -1:
            continue

        # Uscita immediata dal gioco premendo 'Q'
        if key in (ord('q'), ord('Q')):
            break

        # Se la partita è terminata (Vittoria o Game Over), qualsiasi tasto di conferma chiude il gioco
        if engine.game_over or engine.victory:
            if key in (ord('\n'), ord('\r'), ord(' '), ord('q'), ord('Q')):
                break
            continue

        # 3. Gestione dell'interazione con i dialoghi modali sovrapposti (Overlay)
        if ui.active_overlay:
            # ESC o Q chiude qualsiasi finestra modale attiva
            if key in (27, ord('q'), ord('Q')):
                ui.active_overlay = None
                continue

            # Overlay Inventario: tasti numerici 1-6 per equipaggiare armi dallo zaino
            if ui.active_overlay == 'inventory':
                if key in (ord('i'), ord('I')):
                    ui.active_overlay = None
                    continue
                if ord('1') <= key <= ord('6'):
                    idx = key - ord('1')
                    if idx < len(engine.player.weapons_bag):
                        weapon = engine.player.weapons_bag[idx]
                        engine.player.equip_weapon(weapon)
                        engine.combat.log(f"Hai equipaggiato {weapon.name}!")
                        ui.active_overlay = None
                    continue

            # Overlay Grimorio Magico: tasti 3, 4, 5 per lanciare incantesimi
            elif ui.active_overlay == 'spellbook':
                if key in (ord('m'), ord('M'), ord('s'), ord('S')):
                    ui.active_overlay = None
                    continue
                if key in (ord('3'), ord('4'), ord('5')):
                    spell_idx = key - ord('3')
                    engine.cast_player_spell(spell_idx)
                    ui.active_overlay = None
                    continue

            # Overlay Guida Comandi
            elif ui.active_overlay == 'help':
                if key in (ord('?'), 27, ord(' ')):
                    ui.active_overlay = None
                    continue

        # 4. Attivazione / disattivazione finestre modali globali
        if key in (ord('i'), ord('I')):
            ui.active_overlay = 'inventory' if ui.active_overlay != 'inventory' else None
            continue
        elif key in (ord('m'), ord('M')):
            ui.active_overlay = 'spellbook' if ui.active_overlay != 'spellbook' else None
            continue
        elif key == ord('?'):
            ui.active_overlay = 'help' if ui.active_overlay != 'help' else None
            continue

        # 5. Comandi di Movimento ed Esplorazione a 8 direzioni
        # Supporta frecce Curses, WASD, tasti Vi (HJKL) e diagonali Roguelike (Y, U, B, N)
        dx, dy = 0, 0
        if key in (curses.KEY_UP, ord('w'), ord('W'), ord('k'), ord('K')):
            dy = -1
        elif key in (curses.KEY_DOWN, ord('s'), ord('S'), ord('j'), ord('J')):
            dy = 1
        elif key in (curses.KEY_LEFT, ord('a'), ord('A'), ord('h'), ord('H')):
            dx = -1
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D'), ord('l'), ord('L')):
            dx = 1
        elif key in (ord('y'), ord('Y')):
            dx, dy = -1, -1  # Nord-Ovest
        elif key in (ord('u'), ord('U')):
            dx, dy = 1, -1   # Nord-Est
        elif key in (ord('b'), ord('B')):
            dx, dy = -1, 1   # Sud-Ovest
        elif key in (ord('n'), ord('N')):
            dx, dy = 1, 1    # Sud-Est

        if dx != 0 or dy != 0:
            engine.move_player(dx, dy)
            continue

        # 6. Attacco a distanza con arco/fionda nella direzione di marcia
        if key in (ord('f'), ord('F')):
            engine.fire_ranged()
            continue

        # 7. Tasti rapidi di combattimento (pozioni e magie immediate)
        if key == ord('1'):
            engine.use_hp_potion()
        elif key == ord('2'):
            engine.use_mp_potion()
        elif key == ord('3'):
            engine.cast_player_spell(0)  # Dardo Magico
        elif key == ord('4'):
            engine.cast_player_spell(1)  # Cura
        elif key == ord('5'):
            engine.cast_player_spell(2)  # Palla di Fuoco


if __name__ == '__main__':
    # curses.wrapper garantisce il ripristino del terminale anche in caso di eccezioni o Ctrl+C
    curses.wrapper(main)
