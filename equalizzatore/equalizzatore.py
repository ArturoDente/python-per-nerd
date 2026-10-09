#!/usr/bin/env python3
"""
================================================================================
  EQUALIZZATORE A BARRE PER TERMINALE — PYTHON PER NERDS
  Real-Time Terminal Audio Visualizer, Spectrum Analyzer & Beat Detector
================================================================================
Autore: Francesco Clementoni (Python per Nerds)
Librerie: Esclusivamente libreria standard Python (curses, math, cmath,
          threading, subprocess, struct, time, random, collections, dataclasses)
Compatibilità Audio: MP3, WAV, FLAC, OGG o Modalità Sintetizzatore Integrato (--demo)
================================================================================
"""

import sys
import os
import time
import math
import cmath
import struct
import random
import threading
import subprocess
import shutil
import argparse
import signal
import curses
from enum import Enum, auto
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

# ==============================================================================
# 1. COSTANTI E CONFIGURAZIONE GLOBALE (PEP 8)
# ==============================================================================

CAMPIONAMENTO_HZ = 44100      # Frequenza standard CD Audio (44.1 kHz)
CANALI = 2                    # Audio Stereo (Left & Right)
BYTES_PER_CAMPIONE = 2        # 16-bit Signed Integer (S16LE, 2 bytes per canale)
DIMENSIONE_CHUNK = 1024       # Dimensione del frame audio per analisi FFT (2^10)
FPS_TARGET = 35               # Frame rate di rendering dell'interfaccia curses
COOLDOWN_BEAT = 0.22          # Secondi minimi tra un beat e il successivo (~270 BPM max)

# Simboli Unicode e ASCII per il disegno ad alta risoluzione delle barre
BLOCCHI_BARRA = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
CARATTERE_PICCO = "‾"
CARATTERE_PICCO_ASCII = "-"


class ModalitaVisualizzazione(Enum):
    """Modalità di rendering per l'analizzatore di spettro."""
    SPETTRO_BARRE = 0       # Classiche barre di frequenza con picchi cadenti
    SPETTRO_SPECCHIATO = 1  # Barre specchiate dal centro verso l'alto e il basso
    SPETTRO_STEREO = 2      # Due equalizzatori indipendenti per Canale SX e DX
    OSCILLOSCOPIO = 3       # Forma d'onda nel dominio del tempo (Time-Domain Waveform)
    VU_METERS = 4           # Indicatori ad ago VU vintage & matrice beat pulse


class TemaColore(Enum):
    """Tavolozze cromatiche per la visualizzazione a terminale."""
    CLASSICO_HIFI = 0   # Verde -> Giallo -> Rosso (Standard Hi-Fi professionale)
    CYBERPUNK = 1       # Ciano -> Magenta -> Blu elettrico
    MATRIX = 2          # Verde fosforo monocromatico e brillante
    SUNSET = 3          # Giallo caldo -> Arancione -> Rosso fuoco
    GLACIER = 4         # Blu polare -> Ciano -> Bianco


# ==============================================================================
# 2. MOTORE MATEMATICO DSP: FINESTRATURA, FFT E BEAT DETECTION
# ==============================================================================

class ElaboratoreDSP:
    """
    Motore di Digital Signal Processing (DSP) per l'analisi spettrale.
    Esegue finestratura di Hann, Trasformata Rapida di Fourier (FFT)
    e raggruppamento logaritmico delle frequenze udibili.
    """

    def __init__(self, dimensione_fft: int = DIMENSIONE_CHUNK):
        self.N = dimensione_fft
        # Pre-calcolo della Finestra di Hann per abbattere lo Spectral Leakage
        # w[n] = 0.5 * (1 - cos(2*pi*n / (N - 1)))
        self.finestra_hann = [
            0.5 * (1.0 - math.cos(2.0 * math.pi * i / (self.N - 1)))
            for i in range(self.N)
        ]
        # Pre-calcolo dei fattori di rotazione (Twiddle Factors) per la FFT Radix-2
        self.fattori_twiddle = [
            cmath.exp(-2j * math.pi * k / self.N)
            for k in range(self.N // 2)
        ]

    def _fft_cooley_tukey(self, x: List[complex]) -> List[complex]:
        """
        Implementazione didattica pura in Python dell'algoritmo
        Fast Fourier Transform (FFT) di Cooley-Tukey Radix-2 (Decimation-in-Time).
        Complessità algoritmica: O(N log N).
        """
        n = len(x)
        if n <= 1:
            return x

        pari = self._fft_cooley_tukey(x[0::2])
        dispari = self._fft_cooley_tukey(x[1::2])

        # Step di combinazione con moltiplicazione per i Twiddle Factors
        fattore_passo = self.N // n
        risultato = [complex(0, 0)] * n
        meta = n // 2
        for k in range(meta):
            twiddle = self.fattori_twiddle[k * fattore_passo] * dispari[k]
            risultato[k] = pari[k] + twiddle
            risultato[k + meta] = pari[k] - twiddle

        return risultato

    def calcola_spettro(self, campioni: List[float]) -> List[float]:
        """
        Applica la finestra di Hann, calcola la FFT e restituisce le ampiezze
        lineari dei bin di frequenza da 0 a Fs/2 (Nyquist).
        """
        # Assicura che la dimensione sia esattamente N campioni
        if len(campioni) < self.N:
            campioni = campioni + [0.0] * (self.N - len(campioni))
        else:
            campioni = campioni[:self.N]

        # 1. Applicazione della finestra di Hann
        finestrati = [
            complex(campioni[i] * self.finestra_hann[i], 0.0)
            for i in range(self.N)
        ]

        # 2. Calcolo FFT
        spettro_complesso = self._fft_cooley_tukey(finestrati)

        # 3. Calcolo modulo dell'ampiezza per le frequenze positive (0 .. N/2)
        meta_n = self.N // 2
        magnitudini = [
            abs(spettro_complesso[k]) / meta_n
            for k in range(meta_n)
        ]
        return magnitudini

    def mappa_su_bande_logaritmiche(
        self,
        magnitudini: List[float],
        num_bande: int,
        f_min: float = 25.0,
        f_max: float = 16000.0,
        guadagno_db: float = 1.0
    ) -> List[float]:
        """
        Raggruppa i bin lineari della FFT in bande di frequenza a scala logaritmica
        (ispirata alle curve isofoniche e alla percezione uditiva umana).
        Restituisce valori normalizzati nell'intervallo [0.0, 1.0].
        """
        meta_n = len(magnitudini)
        risoluzione_hz = (CAMPIONAMENTO_HZ / 2.0) / meta_n

        bande = []
        # Calcolo dei bordi di frequenza logaritmici: f(i) = f_min * (f_max / f_min)^(i / num_bande)
        rapporto = f_max / f_min

        for b in range(num_bande):
            f_start = f_min * (rapporto ** (b / num_bande))
            f_end = f_min * (rapporto ** ((b + 1) / num_bande))

            bin_start = max(0, min(meta_n - 1, int(f_start / risoluzione_hz)))
            bin_end = max(bin_start + 1, min(meta_n, int(f_end / risoluzione_hz)))

            # Calcolo dell'energia media nella banda (con enfasi sulle alte frequenze)
            somma = sum(magnitudini[bin_start:bin_end])
            conteggio = max(1, bin_end - bin_start)
            valore_medio = somma / conteggio

            # Equalizzazione percettiva (le alte frequenze hanno naturalmente meno ampiezza)
            compensazione_hf = 1.0 + math.log10(1.0 + (b / num_bande) * 9.0) * 1.6
            valore_compensato = valore_medio * compensazione_hf * guadagno_db

            # Conversione in scala simil-Decibel compressa
            # dB = 20 * log10(ampiezza + 1)
            valore_db = math.log10(1.0 + valore_compensato * 25.0)
            valore_norm = max(0.0, min(1.0, valore_db))
            bande.append(valore_norm)

        return bande


class RilevatoreBeat:
    """
    Rilevatore di Beat basato sulla varianza statistica dell'energia istantanea
    nella banda delle frequenze sub-bass (20 Hz - 140 Hz).
    """

    def __init__(self, storico_lunghezza: int = 40):
        self.storico_energia = deque(maxlen=storico_lunghezza)
        self.ultimo_beat_tempo = 0.0
        self.beat_attivo = False
        self.intensita_beat = 0.0
        self.bpm_stimato = 120.0
        self.intervalli_beat = deque(maxlen=8)

    def aggiorna(self, campioni: List[float], tempo_corrente: float) -> bool:
        """
        Analizza i campioni audio correnti e determina se si è verificato un Beat.
        """
        # Calcolo dell'energia istantanea (RMS o somma dei quadrati)
        if not campioni:
            return False

        energia_istantanea = sum(s * s for s in campioni) / len(campioni)
        self.storico_energia.append(energia_istantanea)

        self.beat_attivo = False
        self.intensita_beat = max(0.0, self.intensita_beat - 0.12)

        if len(self.storico_energia) < 15:
            return False

        # Calcolo media e varianza dell'energia passata
        media_energia = sum(self.storico_energia) / len(self.storico_energia)
        varianza = sum((e - media_energia) ** 2 for e in self.storico_energia) / len(self.storico_energia)

        # Coefficiente di soglia dinamica C = -0.0025714 * V + 1.5142857
        # Più la musica è dinamica (alta varianza), più la soglia si abbassa
        coeff_c = max(1.15, min(1.65, 1.5 - (varianza * 2.0)))
        soglia = coeff_c * media_energia

        # Verifica se l'energia corrente supera la soglia e rispetta il tempo di ricarica
        if energia_istantanea > soglia and (tempo_corrente - self.ultimo_beat_tempo) > COOLDOWN_BEAT:
            dt = tempo_corrente - self.ultimo_beat_tempo
            if 0.25 <= dt <= 1.5:
                self.intervalli_beat.append(dt)
                media_dt = sum(self.intervalli_beat) / len(self.intervalli_beat)
                self.bpm_stimato = round(60.0 / media_dt, 1)

            self.ultimo_beat_tempo = tempo_corrente
            self.beat_attivo = True
            # Intensità normalizzata del colpo
            rapporto = energia_istantanea / max(0.0001, soglia)
            self.intensita_beat = min(1.0, 0.5 + (rapporto - 1.0) * 0.5)
            return True

        return False


# ==============================================================================
# 3. SINTETIZZATORE INTEGRATO PER MODALITÀ DEMO
# ==============================================================================

class SintetizzatoreRetroSynth:
    """
    Generatore audio procedurale a 44.1 kHz in tempo reale.
    Produce una traccia Synthwave / Chiptune con Kick, Snare, Hi-Hat,
    linea di basso FM e arpeggi melodici a 124 BPM.
    """

    def __init__(self, bpm: float = 124.0):
        self.bpm = bpm
        self.tempo_campione = 0.0

    def genera_chunk(self, num_campioni: int) -> bytes:
        """Sintetizza matematicamente un blocco di campioni PCM stereo 16-bit."""
        beat_durata = 60.0 / self.bpm
        sedicesimo = beat_durata / 4.0
        buffer = bytearray()

        for _ in range(num_campioni):
            t = self.tempo_campione
            self.tempo_campione += 1.0 / CAMPIONAMENTO_HZ

            t_in_beat = t % beat_durata
            step_idx = int(t / sedicesimo)

            # 1. Cassa Elettronica (Kick Drum: Sine sweep 140 Hz -> 42 Hz)
            kick = 0.0
            if t_in_beat < 0.22:
                freq_kick = 140.0 * math.exp(-t_in_beat * 32.0) + 42.0
                kick = math.sin(2.0 * math.pi * freq_kick * t_in_beat) * math.exp(-t_in_beat * 14.0) * 0.95

            # 2. Rullante / Snare (Noise burst filtrato su battute 2 e 4)
            snare = 0.0
            beat_num = int(t / beat_durata) % 4
            if beat_num in (1, 3) and t_in_beat < 0.18:
                rumore = (random.random() * 2.0 - 1.0)
                corpo = math.sin(2.0 * math.pi * 185.0 * t_in_beat)
                snare = (rumore * 0.6 + corpo * 0.4) * math.exp(-t_in_beat * 20.0) * 0.65

            # 3. Charleston / Hi-Hat (Rumore metallico sui sedicesimi dispari)
            hihat = 0.0
            t_in_16th = t % sedicesimo
            if (step_idx % 2 == 1) and t_in_16th < 0.045:
                hihat = (random.random() * 2.0 - 1.0) * math.exp(-t_in_16th * 90.0) * 0.35

            # 4. Linea di Basso Retrò (Onda a dente di sega / quadra)
            note_basso = [65.41, 65.41, 77.78, 87.31, 65.41, 65.41, 98.00, 87.31]  # C2, C2, Eb2, F2...
            freq_b = note_basso[(step_idx // 2) % len(note_basso)]
            fase_b = (t * freq_b) % 1.0
            basso = (2.0 * fase_b - 1.0) * 0.28  # Sawtooth wave

            # 5. Arpeggio Melodico Chiptune
            scala = [261.63, 329.63, 392.00, 523.25, 659.25, 523.25, 392.00, 329.63]  # C Major Arp
            freq_m = scala[step_idx % len(scala)]
            lead = math.sin(2.0 * math.pi * freq_m * t) * 0.22

            # Mixaggio dei canali e clipping morbido
            mix_l = max(-1.0, min(1.0, kick * 0.9 + snare * 0.7 + hihat * 0.4 + basso * 0.8 + lead * 0.7))
            mix_r = max(-1.0, min(1.0, kick * 0.9 + snare * 0.7 + hihat * 0.6 + basso * 0.8 + lead * 0.5))

            # Quantizzazione a intero con segno 16-bit [-32768, 32767]
            val_l = int(mix_l * 28000)
            val_r = int(mix_r * 28000)
            buffer.extend(struct.pack("<hh", val_l, val_r))

        return bytes(buffer)


# ==============================================================================
# 4. PIPELINE DI DECODIFICA AUDIO E PLAYER MULTI-THREAD
# ==============================================================================

class MotoreAudio:
    """
    Gestisce lo streaming dell'audio tramite sottoprocessi di sistema
    (GStreamer, ffmpeg o wave), l'output sonoro (paplay, aplay, pw-cat)
    e l'alimentazione in tempo reale del buffer DSP.
    """

    def __init__(self, sorgente_file: Optional[str] = None, modalita_demo: bool = False):
        self.sorgente_file = sorgente_file
        self.modalita_demo = modalita_demo or (sorgente_file is None)
        self.in_riproduzione = True
        self.in_pausa = False
        self.volume_percentuale = 80
        self.tempo_trascorso = 0.0
        self.durata_totale = 0.0

        # Dati correnti accessibili dalla UI
        self.campioni_correnti_sx: List[float] = [0.0] * DIMENSIONE_CHUNK
        self.campioni_correnti_dx: List[float] = [0.0] * DIMENSIONE_CHUNK
        self.lock_dati = threading.Lock()

        # Riferimenti ai processi
        self.processo_decoder: Optional[subprocess.Popen] = None
        self.processo_player: Optional[subprocess.Popen] = None
        self.thread_audio: Optional[threading.Thread] = None
        self.sintetizzatore = SintetizzatoreRetroSynth() if self.modalita_demo else None

    def avvia(self) -> None:
        """Avvia il thread di riproduzione audio in background."""
        self.thread_audio = threading.Thread(target=self._ciclo_audio, daemon=True)
        self.thread_audio.start()

    def _trova_comando_player(self) -> List[str]:
        """Seleziona il player audio a bassa latenza disponibile nel sistema."""
        comandi = [
            ["paplay", "--raw", "--channels=2", "--rate=44100", "--format=s16le"],
            ["aplay", "-t", "raw", "-f", "cd", "-c", "2", "-r", "44100", "-q"],
            ["pw-cat", "--playback", "--raw", "--channels=2", "--rate=44100", "--format=s16"]
        ]
        for cmd in comandi:
            if shutil.which(cmd[0]):
                return cmd
        # Fallback aplay
        return ["aplay", "-t", "raw", "-f", "cd", "-c", "2", "-r", "44100", "-q"]

    def _avvia_decoder(self) -> Optional[subprocess.Popen]:
        """Crea il processo di decodifica da MP3/audio a flusso raw PCM S16LE."""
        if self.modalita_demo or not self.sorgente_file:
            return None

        percorso = os.path.abspath(self.sorgente_file)
        if not os.path.exists(percorso):
            return None

        # Tentativo 1: GStreamer (Preinstallato su tutte le distribuzioni Linux)
        pipeline_gst = [
            "gst-launch-1.0", "-q",
            "filesrc", f"location={percorso}",
            "!", "decodebin",
            "!", "audioconvert",
            "!", "audioresample",
            "!", "audio/x-raw,format=S16LE,channels=2,rate=44100",
            "!", "fdsink", "fd=1"
        ]

        # Tentativo 2: FFmpeg (se installato)
        pipeline_ffmpeg = [
            "ffmpeg", "-v", "quiet",
            "-i", percorso,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "2",
            "-ar", "44100",
            "-"
        ]

        for cmd in [pipeline_gst, pipeline_ffmpeg]:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
                # Verifica rapida se il processo si avvia
                time.sleep(0.05)
                if proc.poll() is None or proc.poll() == 0:
                    return proc
            except Exception:
                continue

        return None

    def _ciclo_audio(self) -> None:
        """Loop del thread di decodifica, processamento del volume e riproduzione."""
        comando_player = self._trova_comando_player()
        try:
            self.processo_player = subprocess.Popen(
                comando_player,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.processo_player = None

        self.processo_decoder = self._avvia_decoder()
        bytes_per_chunk = DIMENSIONE_CHUNK * CANALI * BYTES_PER_CAMPIONE
        durata_chunk = DIMENSIONE_CHUNK / CAMPIONAMENTO_HZ

        while self.in_riproduzione:
            if self.in_pausa:
                time.sleep(0.05)
                continue

            raw_chunk = b""
            if self.modalita_demo:
                raw_chunk = self.sintetizzatore.genera_chunk(DIMENSIONE_CHUNK)
            elif self.processo_decoder and self.processo_decoder.stdout:
                raw_chunk = self.processo_decoder.stdout.read(bytes_per_chunk)
                if not raw_chunk or len(raw_chunk) < bytes_per_chunk:
                    # Fine traccia: riavvolgi o esci
                    break
            else:
                # Fallback: silenzio cadenzato
                raw_chunk = b"\x00" * bytes_per_chunk

            # Decodifica dei campioni audio e applicazione del guadagno volume
            campioni_sx = []
            campioni_dx = []
            fattore_vol = self.volume_percentuale / 100.0

            dati_processati = bytearray()
            num_coppie = len(raw_chunk) // (CANALI * BYTES_PER_CAMPIONE)

            for i in range(num_coppie):
                offset = i * 4
                s_l, s_r = struct.unpack_from("<hh", raw_chunk, offset)

                # Scalatura volume e clamp a 16-bit signed
                out_l = max(-32768, min(32767, int(s_l * fattore_vol)))
                out_r = max(-32768, min(32767, int(s_r * fattore_vol)))

                campioni_sx.append(out_l / 32768.0)
                campioni_dx.append(out_r / 32768.0)
                dati_processati.extend(struct.pack("<hh", out_l, out_r))

            # Aggiornamento thread-safe dei campioni per la UI
            with self.lock_dati:
                self.campioni_correnti_sx = campioni_sx
                self.campioni_correnti_dx = campioni_dx
                self.tempo_trascorso += durata_chunk

            # Scrittura al sink audio di sistema
            if self.processo_player and self.processo_player.stdin:
                try:
                    self.processo_player.stdin.write(dati_processati)
                    self.processo_player.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass

            # Regolazione temporizzazione in modalità demo (senza player bloccante)
            if self.modalita_demo and not self.processo_player:
                time.sleep(durata_chunk)

        self.arresta()

    def toggle_pausa(self) -> None:
        """Mette in pausa o riprende l'audio e i sottoprocessi in tempo reale."""
        self.in_pausa = not self.in_pausa
        sig_stop = getattr(signal, "SIGSTOP", None)
        sig_cont = getattr(signal, "SIGCONT", None)
        sig = sig_stop if self.in_pausa else sig_cont

        if sig is not None:
            # Sospende / riprende immediatamente il processo audio a valle (paplay/aplay/pw-cat)
            if self.processo_player and self.processo_player.poll() is None:
                try:
                    self.processo_player.send_signal(sig)
                except Exception:
                    pass

            # Sospende / riprende il processo di decodifica (GStreamer/FFmpeg)
            if self.processo_decoder and self.processo_decoder.poll() is None:
                try:
                    self.processo_decoder.send_signal(sig)
                except Exception:
                    pass

    def arresta(self) -> None:
        """Termina tutti i processi e chiude i flussi in modo pulito."""
        self.in_riproduzione = False
        if self.processo_decoder:
            try:
                self.processo_decoder.terminate()
                self.processo_decoder.wait(timeout=0.2)
            except Exception:
                pass
        if self.processo_player:
            try:
                self.processo_player.terminate()
                self.processo_player.wait(timeout=0.2)
            except Exception:
                pass


# ==============================================================================
# 5. FISICA DEI PICCHI E VISUALIZZATORE CURSES (UI)
# ==============================================================================

@dataclass
class StatoPicco:
    """Modella la gravità e il decadimento del picco massimo di una colonna."""
    valore: float = 0.0
    timer_trattenuta: int = 0
    velocita_caduta: float = 0.0


class VisualizzatoreCurses:
    """
    Motore grafico basato su Curses: gestisce il rendering a video,
    le modalità di visualizzazione, i temi di colore e l'input asincrono.
    """

    def __init__(self, motore_audio: MotoreAudio, nome_traccia: str):
        self.audio = motore_audio
        self.nome_traccia = nome_traccia
        self.dsp = ElaboratoreDSP()
        self.rilevatore_beat = RilevatoreBeat()

        # Stato UI e animazioni
        self.modalita = ModalitaVisualizzazione.SPETTRO_BARRE
        self.tema = TemaColore.CLASSICO_HIFI
        self.stati_picco: Dict[int, StatoPicco] = {}
        self.valori_smooth: Dict[int, float] = {}

    def _inizializza_colori(self) -> None:
        """Configura le coppie di colori per i temi visivi supportati."""
        curses.start_color()
        curses.use_default_colors()

        # Definizione delle coppie di colore standard e avanzate
        # ID 1: Verde / Livello Basso
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        # ID 2: Giallo / Livello Medio
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        # ID 3: Rosso / Livello Alto - Picco
        curses.init_pair(3, curses.COLOR_RED, -1)
        # ID 4: Ciano / Cyberpunk
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        # ID 5: Magenta / Neon
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        # ID 6: Blu / Scuro
        curses.init_pair(6, curses.COLOR_BLUE, -1)
        # ID 7: Bianco Luminoso / HUD
        curses.init_pair(7, curses.COLOR_WHITE, -1)

    def _disegna_stringa_sicura(self, stdscr: Any, y: int, x: int, testo: str, attr: int = 0) -> None:
        """Scrive una stringa gestendo i limiti dello schermo per evitare crash."""
        max_y, max_x = stdscr.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            spazio = max_x - x
            if spazio > 0:
                try:
                    stdscr.addstr(y, x, testo[:spazio], attr)
                except Exception:
                    pass

    def _ottieni_colore_barra(self, frazione_altezza: float) -> int:
        """Restituisce l'attributo di colore in base al tema e all'altezza del segmento."""
        if self.tema == TemaColore.CLASSICO_HIFI:
            if frazione_altezza > 0.82:
                return curses.color_pair(3) | curses.A_BOLD  # Rosso
            elif frazione_altezza > 0.55:
                return curses.color_pair(2) | curses.A_BOLD  # Giallo
            return curses.color_pair(1)                      # Verde

        elif self.tema == TemaColore.CYBERPUNK:
            if frazione_altezza > 0.75:
                return curses.color_pair(5) | curses.A_BOLD  # Magenta
            elif frazione_altezza > 0.40:
                return curses.color_pair(4) | curses.A_BOLD  # Ciano
            return curses.color_pair(6)                      # Blu

        elif self.tema == TemaColore.MATRIX:
            if frazione_altezza > 0.85:
                return curses.color_pair(7) | curses.A_BOLD  # Bianco
            elif frazione_altezza > 0.50:
                return curses.color_pair(1) | curses.A_BOLD  # Verde brillante
            return curses.color_pair(1)                      # Verde

        elif self.tema == TemaColore.SUNSET:
            if frazione_altezza > 0.75:
                return curses.color_pair(3) | curses.A_BOLD  # Rosso
            elif frazione_altezza > 0.40:
                return curses.color_pair(2) | curses.A_BOLD  # Giallo
            return curses.color_pair(5)                      # Magenta

        return curses.color_pair(4)

    def _disegna_intestazione(self, stdscr: Any, max_y: int, max_x: int, beat: bool, intensita_beat: float) -> None:
        """Disegna il pannello superiore con titolo, stato, volume e indicatore beat."""
        # Cornice superiore decorativa
        bordo = "=" * (max_x - 1)
        self._disegna_stringa_sicura(stdscr, 0, 0, bordo, curses.color_pair(7) | curses.A_DIM)

        # Stato di riproduzione
        stato_str = "[PAUSA]" if self.audio.in_pausa else "[PLAY]"
        colore_stato = curses.color_pair(2) if self.audio.in_pausa else (curses.color_pair(1) | curses.A_BOLD)

        # Formattazione minuti e secondi
        secondi_totali = int(self.audio.tempo_trascorso)
        minuti = secondi_totali // 60
        secondi = secondi_totali % 60
        tempo_str = f"{minuti:02d}:{secondi:02d}"

        # Indicatore Beat Flash
        beat_str = "● BEAT" if beat or intensita_beat > 0.4 else "○      "
        attr_beat = (curses.color_pair(3) | curses.A_BOLD | curses.A_STANDOUT) if beat else (
            curses.color_pair(3) | curses.A_BOLD if intensita_beat > 0.4 else curses.color_pair(7) | curses.A_DIM
        )

        # Barra di volume grafica: [||||||||..] 80%
        tacche_totali = 10
        tacche_piene = int((self.audio.volume_percentuale / 100.0) * tacche_totali)
        barra_vol = "[" + "|" * tacche_piene + "." * (tacche_totali - tacche_piene) + "]"
        vol_str = f"VOL: {barra_vol} {self.audio.volume_percentuale:3d}%"

        # Stampa riga 1 dell'header
        self._disegna_stringa_sicura(stdscr, 1, 2, f"🎵 {self.nome_traccia[:28]}", curses.color_pair(7) | curses.A_BOLD)
        self._disegna_stringa_sicura(stdscr, 1, 34, stato_str, colore_stato)
        self._disegna_stringa_sicura(stdscr, 1, 44, f"TEMPO: {tempo_str}", curses.color_pair(7))
        self._disegna_stringa_sicura(stdscr, 1, 58, vol_str, curses.color_pair(4) | curses.A_BOLD)
        self._disegna_stringa_sicura(stdscr, 1, max_x - 14, beat_str, attr_beat)

        # Stampa riga 2 (Modalità e BPM)
        info_mod = f"MODALITÀ: [{self.modalita.name}]   TEMA: [{self.tema.name}]   BPM: ~{self.rilevatore_beat.bpm_stimato}"
        self._disegna_stringa_sicura(stdscr, 2, 2, info_mod, curses.color_pair(7) | curses.A_DIM)
        self._disegna_stringa_sicura(stdscr, 3, 0, "-" * (max_x - 1), curses.color_pair(7) | curses.A_DIM)

    def _disegna_footer(self, stdscr: Any, max_y: int, max_x: int) -> None:
        """Disegna la barra inferiore con i comandi da tastiera."""
        riga_f = max_y - 2
        guida = " [SPAZIO] Pausa/Play   [+/-] Volume   [M/TAB] Modalità   [C] Tema Colori   [ESC/Q] Esci "
        self._disegna_stringa_sicura(stdscr, riga_f, 0, "=" * (max_x - 1), curses.color_pair(7) | curses.A_DIM)
        self._disegna_stringa_sicura(stdscr, riga_f + 1, 1, guida, curses.color_pair(7) | curses.A_STANDOUT)

    def _aggiorna_fisica_picchi(self, indice: int, livello_attuale: float) -> Tuple[float, float]:
        """
        Applica filtro esponenziale di smoothing (EMA) al livello della colonna
        e aggiorna la gravità di caduta del picco superiore.
        """
        # 1. Smoothing del valore principale (EMA)
        val_prec = self.valori_smooth.get(indice, 0.0)
        alpha = 0.65  # Fattore di reattività
        val_smooth = (alpha * livello_attuale) + ((1.0 - alpha) * val_prec)
        self.valori_smooth[indice] = val_smooth

        # 2. Gestione del Picco Cadente
        stato = self.stati_picco.get(indice, StatoPicco())
        if val_smooth >= stato.valore:
            stato.valore = val_smooth
            stato.timer_trattenuta = 4      # Trattieni il picco per 4 frame
            stato.velocita_caduta = 0.0
        else:
            if stato.timer_trattenuta > 0:
                stato.timer_trattenuta -= 1
            else:
                # Accelerazione di gravità discreta verso il basso
                stato.velocita_caduta += 0.015
                stato.valore = max(0.0, stato.valore - stato.velocita_caduta)

        self.stati_picco[indice] = stato
        return val_smooth, stato.valore

    def _renderizza_spettro_barre(self, stdscr: Any, bande: List[float], max_y: int, max_x: int) -> None:
        """Disegna l'equalizzatore standard a barre verticali con picchi fluttuanti."""
        riga_base = max_y - 4
        altezza_max = max(4, riga_base - 5)
        num_bande = len(bande)
        larghezza_colonna = max(1, (max_x - 4) // max_bande_visibili(max_x))
        offset_x = max(2, (max_x - (num_bande * larghezza_colonna)) // 2)

        for i, val_grezzo in enumerate(bande):
            val_effettivo, val_picco = self._aggiorna_fisica_picchi(i, val_grezzo)
            col_x = offset_x + (i * larghezza_colonna)
            if col_x + larghezza_colonna >= max_x - 1:
                break

            # Calcolo altezza del blocco pieno e carattere sub-riga per la cima
            altezza_continua = val_effettivo * altezza_max
            blocchi_pieni = int(altezza_continua)
            frazione_cima = altezza_continua - blocchi_pieni
            indice_subriga = int(frazione_cima * 8)
            char_cima = BLOCCHI_BARRA[max(0, min(8, indice_subriga))]

            # Disegno dei blocchi verticali
            for y_offset in range(altezza_max):
                riga_cursore = riga_base - y_offset
                colore_segmento = self._ottieni_colore_barra(y_offset / altezza_max)

                if y_offset < blocchi_pieni:
                    # Segmento solido
                    self._disegna_stringa_sicura(stdscr, riga_cursore, col_x, "█" * (larghezza_colonna - 1), colore_segmento)
                elif y_offset == blocchi_pieni and indice_subriga > 0:
                    # Cima con risoluzione a sub-carattere
                    self._disegna_stringa_sicura(stdscr, riga_cursore, col_x, char_cima * (larghezza_colonna - 1), colore_segmento)
                else:
                    # Spazio vuoto
                    self._disegna_stringa_sicura(stdscr, riga_cursore, col_x, " " * (larghezza_colonna - 1))

            # Disegno del Picco Sospeso / Cadente
            riga_picco = riga_base - int(val_picco * altezza_max)
            if 4 <= riga_picco <= riga_base:
                self._disegna_stringa_sicura(
                    stdscr,
                    riga_picco,
                    col_x,
                    CARATTERE_PICCO * (larghezza_colonna - 1),
                    curses.color_pair(3) | curses.A_BOLD
                )

        # Etichette di frequenza sul fondo
        etichette = ["50", "120", "250", "500", "1k", "2k", "4k", "8k", "16k"]
        passo_et = max(1, num_bande // len(etichette))
        for idx_e, et in enumerate(etichette):
            b_idx = idx_e * passo_et
            if b_idx < num_bande:
                lx = offset_x + (b_idx * larghezza_colonna)
                self._disegna_stringa_sicura(stdscr, riga_base + 1, lx, et[:larghezza_colonna], curses.color_pair(7) | curses.A_DIM)

    def _renderizza_spettro_specchiato(self, stdscr: Any, bande: List[float], max_y: int, max_x: int) -> None:
        """Disegna un visualizzatore a spettro specchiato (Center-Out)."""
        riga_centro = (max_y - 2) // 2 + 1
        semi_altezza = max(3, (riga_centro - 5))
        num_bande = len(bande)
        larghezza_colonna = max(1, (max_x - 4) // max_bande_visibili(max_x))
        offset_x = max(2, (max_x - (num_bande * larghezza_colonna)) // 2)

        # Linea orizzontale centrale
        self._disegna_stringa_sicura(stdscr, riga_centro, 1, "─" * (max_x - 3), curses.color_pair(4) | curses.A_DIM)

        for i, val in enumerate(bande):
            val_eff, _ = self._aggiorna_fisica_picchi(i, val)
            col_x = offset_x + (i * larghezza_colonna)
            if col_x + larghezza_colonna >= max_x - 1:
                break

            estensione = int(val_eff * semi_altezza)
            attr = self._ottieni_colore_barra(val_eff)

            for h in range(1, estensione + 1):
                # Sopra il centro
                self._disegna_stringa_sicura(stdscr, riga_centro - h, col_x, "█" * (larghezza_colonna - 1), attr)
                # Sotto il centro (specchiato)
                self._disegna_stringa_sicura(stdscr, riga_centro + h, col_x, "█" * (larghezza_colonna - 1), attr)

    def _renderizza_oscilloscopio(self, stdscr: Any, campioni: List[float], max_y: int, max_x: int) -> None:
        """Disegna la forma d'onda del segnale nel dominio del tempo (Time-Domain Waveform)."""
        riga_centro = (max_y - 2) // 2 + 1
        ampiezza_max = max(3, (max_y - 8) // 2)
        punti_visibili = max_x - 4
        passo_campionamento = len(campioni) / punti_visibili if punti_visibili > 0 else 1.0

        # Linea centrale di zero
        self._disegna_stringa_sicura(stdscr, riga_centro, 2, "·" * (max_x - 4), curses.color_pair(7) | curses.A_DIM)

        for x in range(punti_visibili):
            idx = int(x * passo_campionamento)
            if idx < len(campioni):
                val = campioni[idx]
                offset_y = int(val * ampiezza_max)
                y_pos = riga_centro - offset_y
                attr = curses.color_pair(4) | curses.A_BOLD if abs(offset_y) > 2 else curses.color_pair(1)
                simbolo = "~" if abs(val) < 0.3 else ("=" if abs(val) < 0.7 else "█")
                self._disegna_stringa_sicura(stdscr, y_pos, 2 + x, simbolo, attr)

    def _renderizza_vu_meters(self, stdscr: Any, campioni_sx: List[float], campioni_dx: List[float], max_y: int, max_x: int) -> None:
        """Disegna doppi VU-Meter analogici per canale Sinistro e Destro."""
        rms_sx = math.sqrt(sum(s * s for s in campioni_sx) / max(1, len(campioni_sx))) * 2.5
        rms_dx = math.sqrt(sum(s * s for s in campioni_dx) / max(1, len(campioni_dx))) * 2.5

        riga_vu_sx = 6
        riga_vu_dx = 10
        larghezza_vu = max_x - 24

        for ch_nome, riga_y, rms_val in [("CH-LEFT (L)", riga_vu_sx, rms_sx), ("CH-RIGHT (R)", riga_vu_dx, rms_dx)]:
            self._disegna_stringa_sicura(stdscr, riga_y, 4, f"{ch_nome:12s}:", curses.color_pair(7) | curses.A_BOLD)
            tacche = int(min(1.0, rms_val) * larghezza_vu)

            for col in range(larghezza_vu):
                frazione = (col + 1) / larghezza_vu
                attr = self._ottieni_colore_barra(frazione)
                char = "█" if col < tacche else "░"
                self._disegna_stringa_sicura(stdscr, riga_y, 18 + col, char, attr if col < tacche else curses.color_pair(7) | curses.A_DIM)

            db_stima = int(20 * math.log10(max(0.001, rms_val)))
            self._disegna_stringa_sicura(stdscr, riga_y, 19 + larghezza_vu, f"{db_stima:3d} dB", curses.color_pair(7))

        # Matrice Pulsante Beat al centro
        if max_y > 18:
            riga_m = 14
            raggio_beat = int(self.rilevatore_beat.intensita_beat * 8)
            pattern_beat = "[ " + "★ " * raggio_beat + "]" if raggio_beat > 0 else "[           ]"
            cx = (max_x - len(pattern_beat)) // 2
            self._disegna_stringa_sicura(stdscr, riga_m, cx, pattern_beat, curses.color_pair(3) | curses.A_BOLD)

    def esegui(self, stdscr: Any) -> None:
        """Ciclo principale di visualizzazione e gestione eventi tastiera."""
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        self._inizializza_colori()

        periodo_frame = 1.0 / FPS_TARGET
        self.audio.avvia()

        while self.audio.in_riproduzione:
            t_inizio = time.perf_counter()
            max_y, max_x = stdscr.getmaxyx()

            if max_y < 12 or max_x < 45:
                stdscr.erase()
                self._disegna_stringa_sicura(stdscr, 1, 1, "Finestra troppo piccola! Ridimensiona il terminale.", curses.color_pair(3) | curses.A_BOLD)
                stdscr.refresh()
                time.sleep(0.1)
                continue

            # 1. Gestione Input Tastiera Asincrono
            try:
                tasto = stdscr.getch()
            except Exception:
                tasto = -1

            if tasto in (27, ord('q'), ord('Q')):       # ESC o Q per uscire
                self.audio.arresta()
                break
            elif tasto == ord(' '):                      # Spazio: Pausa/Riprendi
                self.audio.toggle_pausa()
            elif tasto in (ord('+'), ord('='), curses.KEY_UP):   # Volume +
                self.audio.volume_percentuale = min(100, self.audio.volume_percentuale + 5)
            elif tasto in (ord('-'), ord('_'), curses.KEY_DOWN): # Volume -
                self.audio.volume_percentuale = max(0, self.audio.volume_percentuale - 5)
            elif tasto in (ord('m'), ord('M'), 9):       # M o TAB: Cambia Modalità
                nuovo_id = (self.modalita.value + 1) % len(ModalitaVisualizzazione)
                self.modalita = ModalitaVisualizzazione(nuovo_id)
            elif tasto in (ord('c'), ord('C')):          # C: Cambia Tema Colori
                nuovo_tema_id = (self.tema.value + 1) % len(TemaColore)
                self.tema = TemaColore(nuovo_tema_id)

            # 2. Estrazione dati audio thread-safe
            with self.audio.lock_dati:
                sx = list(self.audio.campioni_correnti_sx)
                dx = list(self.audio.campioni_correnti_dx)
                t_audio = self.audio.tempo_trascorso

            num_bande = max_bande_visibili(max_x)

            if not self.audio.in_pausa:
                # Mix mono per l'analisi spettrale combinata
                mono = [(sx[i] + dx[i]) * 0.5 for i in range(min(len(sx), len(dx)))] if sx else []

                # 3. Calcolo DSP (FFT & Beat Detection)
                magnitudini = self.dsp.calcola_spettro(mono)
                bande_log = self.dsp.mappa_su_bande_logaritmiche(magnitudini, num_bande)
                is_beat = self.rilevatore_beat.aggiorna(mono, t_audio)
            else:
                # In stato di pausa: mantieni lo stato visivo con decadimento dolce
                bande_log = [max(0.0, self.valori_smooth.get(i, 0.0) * 0.94) for i in range(num_bande)]
                mono = [0.0] * DIMENSIONE_CHUNK
                is_beat = False

            # 4. Rendering Grafico
            stdscr.erase()
            self._disegna_intestazione(stdscr, max_y, max_x, is_beat, self.rilevatore_beat.intensita_beat)

            if self.modalita == ModalitaVisualizzazione.SPETTRO_BARRE:
                self._renderizza_spettro_barre(stdscr, bande_log, max_y, max_x)
            elif self.modalita == ModalitaVisualizzazione.SPETTRO_SPECCHIATO:
                self._renderizza_spettro_specchiato(stdscr, bande_log, max_y, max_x)
            elif self.modalita == ModalitaVisualizzazione.OSCILLOSCOPIO:
                self._renderizza_oscilloscopio(stdscr, mono, max_y, max_x)
            elif self.modalita == ModalitaVisualizzazione.VU_METERS:
                self._renderizza_vu_meters(stdscr, sx, dx, max_y, max_x)
            elif self.modalita == ModalitaVisualizzazione.SPETTRO_STEREO:
                # Metà superiore Canale Sinistro, Metà inferiore Canale Destro
                mag_sx = self.dsp.calcola_spettro(sx)
                mag_dx = self.dsp.calcola_spettro(dx)
                bande_sx = self.dsp.mappa_su_bande_logaritmiche(mag_sx, num_bande)
                bande_dx = self.dsp.mappa_su_bande_logaritmiche(mag_dx, num_bande)
                self._renderizza_spettro_barre(stdscr, bande_sx, (max_y // 2) + 2, max_x)
                self._renderizza_spettro_barre(stdscr, bande_dx, max_y, max_x)

            self._disegna_footer(stdscr, max_y, max_x)
            stdscr.refresh()

            # 5. Stabilizzazione FPS
            dt = time.perf_counter() - t_inizio
            tempo_attesa = periodo_frame - dt
            if tempo_attesa > 0:
                time.sleep(tempo_attesa)


def max_bande_visibili(larghezza_terminale: int) -> int:
    """Calcola il numero ottimale di colonne dell'equalizzatore in base alla larghezza del terminale."""
    spazio_utile = larghezza_terminale - 6
    # Ogni colonna occupa 2 o 3 caratteri (barra + spazio vuoto)
    num = max(8, min(64, spazio_utile // 3))
    return num


# ==============================================================================
# 6. ENTRY POINT E PARSING DEGLI ARGOMENTI CLI
# ==============================================================================

def main() -> None:
    """Funzione di avvio principale."""
    parser = argparse.ArgumentParser(
        description="Equalizzatore a barre in tempo reale nel Terminale (Python per Nerds)"
    )
    parser.add_argument(
        "file_audio",
        nargs="?",
        default=None,
        help="Percorso del file MP3, WAV, FLAC o OGG da riprodurre."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Avvia il sintetizzatore procedurale RetroSynth integrato a 124 BPM."
    )

    args = parser.parse_args()

    # Se non viene fornito un file e non è specificato --demo, avvia comunque la demo
    modalita_demo = args.demo or (args.file_audio is None)
    nome_traccia = "RetroSynth 124 BPM (Demo)" if modalita_demo else os.path.basename(args.file_audio)

    # Validazione file se specificato
    if not modalita_demo and not os.path.exists(args.file_audio):
        print(f"Errore: Il file audio '{args.file_audio}' non esiste.", file=sys.stderr)
        sys.exit(1)

    motore_audio = MotoreAudio(sorgente_file=args.file_audio, modalita_demo=modalita_demo)
    visualizzatore = VisualizzatoreCurses(motore_audio=motore_audio, nome_traccia=nome_traccia)

    try:
        curses.wrapper(visualizzatore.esegui)
    except KeyboardInterrupt:
        pass
    finally:
        motore_audio.arresta()
        print("\nEqualizzatore terminato. Buona programmazione con Python per Nerds!\n")


if __name__ == "__main__":
    main()
