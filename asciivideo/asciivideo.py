#!/usr/bin/env python3
"""
================================================================================
  ASCII VIDEO PLAYER — PYTHON PER NERDS
  Convertitore e Riproduttore di Video & GIF in Grafica ASCII in Tempo Reale
================================================================================
Autore: Francesco Clementoni (Python per Nerds)
Librerie: Esclusivamente Libreria Standard Python (curses, time, math,
          subprocess, shutil, sys, os, argparse, typing)
Supporto Formati: GIF, MP4, MKV, WEBM, AVI o Motore Demo Procedurale 3D Integrato
================================================================================
"""

import os
import sys
import time
import math
import curses
import shutil
import argparse
import subprocess
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Any

# ==============================================================================
# 1. COSTANTI E SCALE DI DENSITÀ DEI CARATTERI ASCII
# ==============================================================================

# Rampa ASCII standard a 10 livelli di luminanza (dal più scuro al più luminoso)
RAMPA_ASCII_STANDARD = " .:-=+*#%@"

# Rampa ASCII ad alta densità a 70 livelli (massimo dettaglio fotografico)
RAMPA_ASCII_DETTAGLIATA = (
    " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
)

# Rampa ASCII a blocchi solidi (stile teletext / retro-gaming)
RAMPA_ASCII_BLOCCHI = " ░▒▓█"


class ModalitaColore(Enum):
    """Modalità di renderizzazione cromatica dei fotogrammi."""
    MONOCROMATICO = auto()  # Solo luminosità (caratteri bianchi su nero o fosfori)
    COLORE_RGB = auto()     # Colori della tavolozza a 256 colori ANSI/Curses


class TemaMonocromatico(Enum):
    """Temi di fosfori monocromatici per l'estetica retrò."""
    BIANCO_NERO = auto()    # Standard Monocromatico
    VERDE_MATRIX = auto()   # Fosfori verdi CRT (stile Matrix)
    AMBRA_CRT = auto()      # Fosfori caldi arancione/ambra
    CYBERPUNK = auto()      # Neon Ciano
    NEGATIVO = auto()       # Negativo / Invertito


# ==============================================================================
# 2. ELABORATORE DI FOTOGRAMMI & CONVERSIONE GRAFICA
# ==============================================================================

def calcola_luminanza(r: int, g: int, b: int) -> float:
    """
    Calcola la componente di luminanza (luma) secondo la convenzione ITU-R BT.601.
    La formula pesa le componenti RGB tenendo conto della curva di sensibilità spettrale
    del sistema visivo umano (58.7% verde, 29.9% rosso, 11.4% blu).
    Restituisce un valore in virgola mobile compreso tra 0.0 e 1.0.
    """
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def mappa_luminanza_a_carattere(luminanza: float, rampa: str, invertito: bool = False) -> str:
    """Mappa un valore di luminanza [0.0, 1.0] su un carattere della rampa ASCII."""
    val = max(0.0, min(1.0, luminanza))
    if invertito:
        val = 1.0 - val
    indice = int(val * (len(rampa) - 1))
    return rampa[indice]


def quantizza_rgb_in_coppia_curses(r: int, g: int, b: int, ha_256_colori: bool) -> int:
    """
    Mappa una terna RGB (0-255) sulla coppia di colori più adatta in Curses.
    Su terminali con tavolozza a 256 colori mappa sul cubo cromatico 6x6x6.
    Restituisce l'ID della coppia colore Curses pre-configurata (offset 10).
    """
    if not ha_256_colori:
        # Mappatura su 8 colori di base (coppie 1-7)
        lum = calcola_luminanza(r, g, b)
        if lum < 0.15:
            return 0
        elif r > 160 and g < 100 and b < 100:
            return 1  # Rosso
        elif g > 160 and r < 100:
            return 2  # Verde
        elif r > 160 and g > 160 and b < 100:
            return 3  # Giallo
        elif b > 160 and r < 100 and g < 100:
            return 4  # Blu
        elif r > 160 and b > 160:
            return 5  # Magenta
        elif g > 160 and b > 160:
            return 6  # Ciano
        return 7      # Bianco

    # Su terminali a 256 colori usiamo le coppie preconfigurate da 10 a 225.
    # Ciascun canale (R, G, B) viene quantizzato in 6 intervalli discreti (0..5).
    r_idx = min(5, r // 43)
    g_idx = min(5, g // 43)
    b_idx = min(5, b // 43)
    # L'ID della coppia colore Curses associata è:
    # 10 + (r_idx * 36 + g_idx * 6 + b_idx)
    # lasciando le coppie 1-7 per i colori primari di sistema.
    return 10 + (r_idx * 36 + g_idx * 6 + b_idx)


# ==============================================================================
# 3. DECODER VIDEO MULTI-BACKEND (GSTREAMER / IMAGEMAGICK / DEMO 3D)
# ==============================================================================

class DecodificatoreVideo:
    """
    Gestisce l'estrazione e lo streaming dei fotogrammi video in formato PPM grezzo o Raw RGB.
    Supporta in modo trasparente GStreamer, ImageMagick e un generatore Demo 3D.
    """

    def __init__(self, percorso_file: Optional[str], larghezza: int, altezza: int, fps: int = 24):
        self.percorso_file = os.path.abspath(percorso_file) if percorso_file else None
        self.larghezza = larghezza
        self.altezza = altezza
        self.fps = fps
        self.tipo_stream = "demo"  # "raw_rgb", "ppm" o "demo"
        self.processo: Optional[subprocess.Popen] = None
        self.e_demo = self.percorso_file is None or not os.path.exists(self.percorso_file)
        self.frame_index = 0
        self.t_inizio = time.perf_counter()

    def avvia(self) -> None:
        """Avvia la pipeline di decodifica video sottostante."""
        if self.e_demo or not self.percorso_file:
            self.tipo_stream = "demo"
            return

        estensione = os.path.splitext(self.percorso_file)[1].lower()

        # Rileva se ImageMagick è disponibile con il comando moderno 'magick' o legacy 'convert'
        cmd_im = "magick" if shutil.which("magick") else ("convert" if shutil.which("convert") else None)

        # 1. Se è una GIF animata, usiamo ImageMagick in formato PPM
        if estensione == ".gif" and cmd_im:
            comando_gif = [
                cmd_im,
                "-coalesce",
                self.percorso_file,
                "-resize", f"{self.larghezza}x{self.altezza}!",
                "ppm:-"
            ]
            try:
                self.processo = subprocess.Popen(comando_gif, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.tipo_stream = "ppm"
                return
            except Exception:
                pass

        # 2. Se è un file video (MP4, MKV, AVI, WEBM, MOV) o GIF, usiamo GStreamer ad alte prestazioni
        if shutil.which("gst-launch-1.0"):
            comando_gst = [
                "gst-launch-1.0", "-q",
                "filesrc", f"location={self.percorso_file}",
                "!", "decodebin",
                "!", "videoconvert",
                "!", "videoscale",
                "!", "videorate",
                "!", f"video/x-raw,format=RGB,width={self.larghezza},height={self.altezza},framerate={self.fps}/1",
                "!", "fdsink"
            ]
            try:
                self.processo = subprocess.Popen(comando_gst, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.tipo_stream = "raw_rgb"
                return
            except Exception:
                pass

        # 3. Fallback con ImageMagick per immagini/video
        if cmd_im:
            comando_conv = [
                cmd_im,
                self.percorso_file,
                "-resize", f"{self.larghezza}x{self.altezza}!",
                "ppm:-"
            ]
            try:
                self.processo = subprocess.Popen(comando_conv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.tipo_stream = "ppm"
                return
            except Exception:
                pass

        # Se nessun decoder è utilizzabile, attiva la demo 3D procedurale
        self.e_demo = True
        self.tipo_stream = "demo"

    def _leggi_blocco(self, n_bytes: int) -> Optional[bytes]:
        """
        Legge esattamente n_bytes dallo stream stdout del sottoprocesso.
        I canali pipe possono frammentare i flussi di dati: questo metodo
        accumula i byte ricevuti fino a raggiungere la dimensione richiesta,
        restituendo None solo al sopraggiungere dell'effettivo EOF.
        """
        if self.processo is None or self.processo.stdout is None:
            return None
        buffer = bytearray()
        while len(buffer) < n_bytes:
            chunk = self.processo.stdout.read(n_bytes - len(buffer))
            if not chunk:
                return None
            buffer.extend(chunk)
        return bytes(buffer)

    def leggi_prossimo_fotogramma(self) -> Optional[List[List[Tuple[int, int, int]]]]:
        """
        Estrae il prossimo fotogramma come matrice di pixel 2D [righe][colonne] -> (R, G, B).
        """
        if self.tipo_stream == "demo" or self.e_demo:
            self.frame_index += 1
            return self._genera_fotogramma_demo_3d(self.frame_index)

        if self.processo is None or self.processo.stdout is None:
            return None

        # 1. STREAMING RAW RGB (GStreamer)
        if self.tipo_stream == "raw_rgb":
            bytes_necessari = self.larghezza * self.altezza * 3
            dati_raw = self._leggi_blocco(bytes_necessari)
            if dati_raw is None:
                return None

            fotogramma = []
            idx = 0
            for _ in range(self.altezza):
                riga = []
                for _ in range(self.larghezza):
                    riga.append((dati_raw[idx], dati_raw[idx + 1], dati_raw[idx + 2]))
                    idx += 3
                fotogramma.append(riga)

            self.frame_index += 1
            return fotogramma

        # 2. STREAMING PPM P6 (ImageMagick)
        elif self.tipo_stream == "ppm":
            try:
                linea_magic = self.processo.stdout.readline()
                if not linea_magic:
                    return None
                while linea_magic.startswith(b"#") or linea_magic == b"\n":
                    linea_magic = self.processo.stdout.readline()
                if not linea_magic.startswith(b"P6"):
                    return None

                linea_dim = self.processo.stdout.readline()
                while linea_dim.startswith(b"#") or linea_dim == b"\n":
                    linea_dim = self.processo.stdout.readline()
                parti = linea_dim.strip().split()
                w, h = int(parti[0]), int(parti[1])

                linea_max = self.processo.stdout.readline()
                while linea_max.startswith(b"#") or linea_max == b"\n":
                    linea_max = self.processo.stdout.readline()

                bytes_necessari = w * h * 3
                dati_raw = self._leggi_blocco(bytes_necessari)
                if dati_raw is None:
                    return None

                fotogramma = []
                idx = 0
                for _ in range(h):
                    riga = []
                    for _ in range(w):
                        riga.append((dati_raw[idx], dati_raw[idx + 1], dati_raw[idx + 2]))
                        idx += 3
                    fotogramma.append(riga)

                self.frame_index += 1
                return fotogramma
            except Exception:
                return None

        return None

    def riavvolgi(self) -> None:
        """Riavvolge il video rieseguendo il decoder."""
        self.arresta()
        self.frame_index = 0
        self.avvia()

    def arresta(self) -> None:
        """Termina il sottoprocesso di decodifica."""
        if self.processo:
            try:
                self.processo.terminate()
                self.processo.wait(timeout=0.2)
            except Exception:
                try:
                    self.processo.kill()
                except Exception:
                    pass
            self.processo = None

    def _genera_fotogramma_demo_3d(self, frame: int) -> List[List[Tuple[int, int, int]]]:
        """
        Genera proceduralmente in tempo reale un fotogramma di una ciambella 3D (Torus)
        rotante con shading di Lambert, gradiente cromatico e Z-Buffer a profondità inversa (1/z).
        """
        w, h = self.larghezza, self.altezza
        matrice = [[(0, 0, 0) for _ in range(w)] for _ in range(h)]
        z_buffer = [[0.0 for _ in range(w)] for _ in range(h)]

        # Angoli di rotazione sui due assi in funzione del tempo
        a = frame * 0.045
        b = frame * 0.030

        cos_a, sin_a = math.cos(a), math.sin(a)
        cos_b, sin_b = math.cos(b), math.sin(b)

        r1 = 1.0   # Raggio della sezione del toro
        r2 = 2.0   # Distanza dal centro del toro
        k2 = 5.0   # Distanza del toro dalla telecamera
        k1 = w * k2 * 3.0 / (8.0 * (r1 + r2))  # Fattore di scala prospettica

        # Scansione angolare della ciambella (theta e phi)
        for theta_i in range(0, 628, 14):
            theta = theta_i / 100.0
            cos_th, sin_th = math.cos(theta), math.sin(theta)

            for phi_i in range(0, 628, 6):
                phi = phi_i / 100.0
                cos_ph, sin_ph = math.cos(phi), math.sin(phi)

                # Coordinate 3D prima della rotazione
                cerchio_x = r2 + r1 * cos_th
                cerchio_y = r1 * sin_th

                # Trasformazione di rotazione 3D
                x = cerchio_x * (cos_b * cos_ph + sin_a * sin_b * sin_ph) - cerchio_y * cos_a * sin_b
                y = cerchio_x * (sin_b * cos_ph - sin_a * cos_b * sin_ph) + cerchio_y * cos_a * cos_b
                z = k2 + cos_a * cerchio_x * sin_ph + cerchio_y * sin_a
                ooz = 1.0 / z  # One over Z (profondità inversa per z-buffer)

                # Proiezione 2D su schermo
                xp = int(w / 2 + k1 * ooz * x * 2.0)  # Moltiplicatore 2.0 per aspect ratio terminale
                yp = int(h / 2 - k1 * ooz * y)

                # Calcolo del vettore normale per l'illuminazione (shading di Lambert)
                luminanza = (
                    cos_ph * cos_th * sin_b
                    - cos_a * cos_th * sin_ph
                    - sin_a * sin_th
                    + cos_b * (cos_a * sin_th - cos_th * sin_a * sin_ph)
                )

                if 0 <= yp < h and 0 <= xp < w:
                    if ooz > z_buffer[yp][xp]:
                        z_buffer[yp][xp] = ooz
                        if luminanza > 0:
                            # Calcola gradiente di colore dinamico
                            r_col = int(min(255, max(40, 180 * luminanza + 60 * math.sin(a))))
                            g_col = int(min(255, max(40, 140 * luminanza + 80 * math.cos(b))))
                            b_col = int(min(255, max(60, 240 * luminanza)))
                            matrice[yp][xp] = (r_col, g_col, b_col)

        return matrice


# ==============================================================================
# 4. MOTORE DI RENDERING CURSES
# ==============================================================================

class RiproduttoreAscii:
    """
    Orchestra l'interfaccia Curses, la riproduzione video a fotogrammi,
    i controlli da tastiera e le modalità di colorazione.
    """

    def __init__(self, percorso_video: Optional[str]):
        self.percorso_video = percorso_video
        self.modalita_colore = ModalitaColore.COLORE_RGB
        self.tema = TemaMonocromatico.BIANCO_NERO
        self.rampa_idx = 0
        self.rampe = [RAMPA_ASCII_STANDARD, RAMPA_ASCII_DETTAGLIATA, RAMPA_ASCII_BLOCCHI]
        self.fps_target = 24
        self.in_pausa = False
        self.mostra_hud = True
        self.ha_256_colori = False
        self.decoder: Optional[DecodificatoreVideo] = None

    def _inizializza_colori(self) -> None:
        """Configura le coppie di colori Curses per i temi monocromatici e il cubo RGB."""
        curses.start_color()
        try:
            curses.use_default_colors()
        except Exception:
            pass

        self.ha_256_colori = curses.COLORS >= 256

        # Coppie 1-7: Colori Base
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)

        # Inizializza il Cubo di Colori 6x6x6 per la tavolozza a 256 colori (Coppie Curses da 10 a 225)
        # Nello standard ANSI i colori del cubo hanno indici da 16 a 231;
        # associamo ciascun colore a una color pair Curses a partire dall'indice 10.
        if self.ha_256_colori:
            for r in range(6):
                for g in range(6):
                    for b in range(6):
                        color_idx = 16 + (r * 36 + g * 6 + b)
                        pair_id = 10 + (r * 36 + g * 6 + b)
                        if pair_id < curses.COLOR_PAIRS:
                            try:
                                curses.init_pair(pair_id, color_idx, -1)
                            except Exception:
                                pass

    def _ottieni_attributo_tema_mono(self, lum: float) -> Tuple[int, bool]:
        """Restituisce l'attributo di colore e il flag di inversione per il tema monocromatico."""
        if self.tema == TemaMonocromatico.VERDE_MATRIX:
            attr = curses.color_pair(2)
            if lum > 0.75:
                attr |= curses.A_BOLD
            elif lum < 0.35:
                attr |= curses.A_DIM
            return attr, False

        elif self.tema == TemaMonocromatico.AMBRA_CRT:
            attr = curses.color_pair(3)
            if lum > 0.75:
                attr |= curses.A_BOLD
            elif lum < 0.35:
                attr |= curses.A_DIM
            return attr, False

        elif self.tema == TemaMonocromatico.CYBERPUNK:
            attr = curses.color_pair(6)
            if lum > 0.70:
                attr |= curses.A_BOLD
            elif lum < 0.35:
                attr = curses.color_pair(4) | curses.A_DIM
            return attr, False

        elif self.tema == TemaMonocromatico.NEGATIVO:
            return curses.color_pair(7) | curses.A_STANDOUT, True

        else:  # BIANCO_NERO standard
            attr = curses.color_pair(7)
            if lum > 0.75:
                attr |= curses.A_BOLD
            elif lum < 0.35:
                attr |= curses.A_DIM
            return attr, False

    def esegui(self, stdscr: Any) -> None:
        """Ciclo principale di renderizzazione dei fotogrammi e gestione input."""
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        self._inizializza_colori()

        max_y, max_x = stdscr.getmaxyx()
        h_video = max(10, max_y - (2 if self.mostra_hud else 0))
        w_video = max(10, max_x - 1)

        self.decoder = DecodificatoreVideo(self.percorso_video, w_video, h_video, self.fps_target)
        self.decoder.avvia()

        ultimo_fotogramma = None
        in_esecuzione = True

        while in_esecuzione:
            t_frame_inizio = time.perf_counter()

            # 1. Rilevamento ridimensionamento della finestra
            cur_y, cur_x = stdscr.getmaxyx()
            if cur_y != max_y or cur_x != max_x:
                max_y, max_x = cur_y, cur_x
                h_video = max(10, max_y - (2 if self.mostra_hud else 0))
                w_video = max(10, max_x - 1)
                self.decoder.larghezza = w_video
                self.decoder.altezza = h_video
                self.decoder.riavvolgi()

            # 2. Gestione Input Asincrono da Tastiera
            try:
                tasto = stdscr.getch()
            except Exception:
                tasto = -1

            if tasto in (27, ord('q'), ord('Q')):        # ESC o Q: Esci
                in_esecuzione = False
                break
            elif tasto == ord(' '):                       # SPAZIO: Pausa / Riprendi
                self.in_pausa = not self.in_pausa
            elif tasto in (ord('c'), ord('C')):           # C: Toggle Colore / Monocromatico
                self.modalita_colore = (
                    ModalitaColore.MONOCROMATICO
                    if self.modalita_colore == ModalitaColore.COLORE_RGB
                    else ModalitaColore.COLORE_RGB
                )
            elif tasto in (ord('t'), ord('T')):           # T: Cicla Temi Monocromatici
                temi = list(TemaMonocromatico)
                nuovo_idx = (temi.index(self.tema) + 1) % len(temi)
                self.tema = temi[nuovo_idx]
            elif tasto in (ord('d'), ord('D')):           # D: Cicla Rampa Caratteri ASCII
                self.rampa_idx = (self.rampa_idx + 1) % len(self.rampe)
            elif tasto in (ord('h'), ord('H')):           # H: Toggle Barra HUD
                self.mostra_hud = not self.mostra_hud
            elif tasto in (ord('r'), ord('R')):           # R: Riavvolgi Video
                self.decoder.riavvolgi()
            elif tasto in (ord('+'), ord('='), curses.KEY_UP):   # Aumenta FPS
                self.fps_target = min(60, self.fps_target + 2)
            elif tasto in (ord('-'), ord('_'), curses.KEY_DOWN): # Rallenta FPS
                self.fps_target = max(4, self.fps_target - 2)

            # 3. Estrazione del Prossimo Fotogramma (se non in pausa)
            if not self.in_pausa:
                pixel_mat = self.decoder.leggi_prossimo_fotogramma()
                if pixel_mat is None:
                    # Raggiunta la fine del filmato: riavvolgi in loop continuo
                    self.decoder.riavvolgi()
                    pixel_mat = self.decoder.leggi_prossimo_fotogramma()
                ultimo_fotogramma = pixel_mat
            else:
                pixel_mat = ultimo_fotogramma

            # 4. Rendering Grafico ASCII a Schermo
            stdscr.erase()
            rampa_corrente = self.rampe[self.rampa_idx]

            if pixel_mat:
                righe_disponibili = min(len(pixel_mat), max_y - (2 if self.mostra_hud else 0))
                for y in range(righe_disponibili):
                    riga_pixels = pixel_mat[y]
                    colonne_disponibili = min(len(riga_pixels), max_x - 1)

                    for x in range(colonne_disponibili):
                        r, g, b = riga_pixels[x]
                        lum = calcola_luminanza(r, g, b)

                        if self.modalita_colore == ModalitaColore.COLORE_RGB:
                            char = mappa_luminanza_a_carattere(lum, rampa_corrente)
                            coppia = quantizza_rgb_in_coppia_curses(r, g, b, self.ha_256_colori)
                            attr = curses.color_pair(coppia)
                            if lum > 0.65:
                                attr |= curses.A_BOLD
                        else:
                            attr_tema, invertito = self._ottieni_attributo_tema_mono(lum)
                            char = mappa_luminanza_a_carattere(lum, rampa_corrente, invertito)
                            attr = attr_tema

                        try:
                            stdscr.addch(y, x, char, attr)
                        except Exception:
                            pass

            # 5. Barra Superiore / Inferiore HUD
            if self.mostra_hud and max_y > 4 and max_x > 35:
                nome_sorgente = "Demo 3D Donut" if self.decoder.e_demo else os.path.basename(self.percorso_video or "")
                colore_str = "RGB Colore" if self.modalita_colore == ModalitaColore.COLORE_RGB else f"Mono ({self.tema.name})"
                stato_str = "[PAUSA]" if self.in_pausa else "[PLAY]"

                info_hud = (
                    f" ASCII CINEMA 🎬 │ {nome_sorgente[:20]} │ {colore_str} │ "
                    f"Frame: {self.decoder.frame_index:05d} │ {self.fps_target:02d} FPS │ {stato_str} "
                )
                comandi_hud = " [SPAZIO] Pausa  [C] Colore/Mono  [T] Tema  [D] Rampa ASCII  [+/-] FPS  [R] Riavvolgi  [Q] Esci "

                try:
                    stdscr.addstr(0, max(0, (max_x - len(info_hud)) // 2), info_hud[:max_x - 1], curses.color_pair(7) | curses.A_STANDOUT)
                    stdscr.addstr(max_y - 1, 1, comandi_hud[:max_x - 2], curses.color_pair(7) | curses.A_DIM)
                except Exception:
                    pass

            stdscr.refresh()

            # 6. Regolazione della Frequenza dei Fotogrammi (FPS)
            periodo_frame = 1.0 / self.fps_target
            tempo_trascorso = time.perf_counter() - t_frame_inizio
            tempo_attesa = periodo_frame - tempo_trascorso
            if tempo_attesa > 0:
                time.sleep(tempo_attesa)

        # Pulizia finale del decoder all'uscita
        if self.decoder:
            self.decoder.arresta()


# ==============================================================================
# 5. ENTRY POINT PRINCIPALE
# ==============================================================================

def main() -> None:
    """Entry point con parsing degli argomenti da riga di comando."""
    parser = argparse.ArgumentParser(
        description="ASCII Video Player — Riproduttore e convertitore di video e GIF in ASCII Art (Python per Nerds)"
    )
    parser.add_argument(
        "file_video",
        nargs="?",
        default=None,
        help="Percorso del file video (MP4, MKV, WEBM, AVI) o animazione GIF da riprodurre."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Esegue la simulazione 3D Donut Torus generata proceduralmente in tempo reale."
    )

    args = parser.parse_args()

    # Se non viene passato alcun file o è specificato --demo, avvia la demo 3D
    percorso = None if (args.demo or args.file_video is None) else args.file_video

    if percorso and not os.path.exists(percorso):
        print(f"Errore: Il file video o GIF specificato '{percorso}' non esiste.", file=sys.stderr)
        sys.exit(1)

    player = RiproduttoreAscii(percorso_video=percorso)

    try:
        curses.wrapper(player.esegui)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nRiproduzione ASCII terminata. Buona visione con Python per Nerds!\n")


if __name__ == "__main__":
    main()
