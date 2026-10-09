# Python per Nerds 🎮
### *Videogiochi, Simulazioni e Grafica ASCII nel Terminale*
**Autore:** Francesco Clementoni  
**Licenza Codice:** MIT  

---

Questo repository contiene il **codice sorgente completo e funzionante** dei 7 progetti sviluppati nel libro **"Python per Nerds"**.

Tutti i progetti sono realizzati utilizzando **esclusivamente la libreria standard di Python 3** (in particolare `curses`, `time`, `random`, `math`, `threading`, `struct`, `dataclasses`), senza alcuna dipendenza esterna da installare via `pip`.

---

## 🕹️ I Progetti nel Repository

| Cartella | Progetto | Concetti Chiave & Tecniche | Come Eseguire |
| :--- | :--- | :--- | :--- |
| **`matrix/`** | **La Pioggia Digitale di Matrix** | Griglia 2D Curses, velocità frazionarie, gradienti di fosforo, glitch stocastico, Easter Egg con flash a centro schermo | `python3 matrix/matrix.py` |
| **`dino run/`** | **Endless Runner (Dino Run)** | Cinematica del salto discreto (`v_y += g`), scorrimento ostacoli procedurali, sprite ASCII multiriga, hitbox AABB | `python3 "dino run/dino_run.py"` |
| **`gameoflife/`** | **Automa Cellulare di Conway** | Matrici 2D, intorno di Moore a 8 vicini, topologia toroidale (`%`), tracciamento età biologica e rilevamento stasi/cicli | `python3 gameoflife/game_of_life.py` |
| **`fireworks/`** | **Spettacolo Pirotecnico OOP** | Programmazione a Oggetti, Macchina a Stati Finiti (`Enum`), vettori trigonometrici a 360°, correzione aspect ratio 2:1 | `python3 fireworks/fireworks.py` |
| **`equalizzatore/`** | **Equalizzatore Audio DSP** | Fast Fourier Transform (FFT Cooley-Tukey Radix-2), finestratura di Hann, multithreading sincronizzato audio/UI, VU-meter | `python3 equalizzatore/equalizzatore.py` |
| **`asciivideo/`** | **ASCII Video Player & 3D Donut** | Streaming binario via Pipe Unix (`subprocess.PIPE`), quantizzazione colore a 256 colori ANSI, formula ITU-R BT.601, motore 3D Donut con Z-Buffer | `python3 asciivideo/asciivideo.py` |
| **`pyrogue/`** | **PyRogue (Progetto Conclusivo)** | Package modulare, generazione procedurale di dungeon BSP, Field of View (FOV Shadowcasting), pathfinding AI, sistema RPG a turni | `python3 pyrogue/main.py` |

---

## 🚀 Requisiti e Come Iniziare

### Prerequisiti
- **Python 3.10** o superiore.
- **Terminale:**
  - **Linux / macOS:** Qualsiasi terminale standard (GNOME Terminal, Konsole, Alacritty, iTerm2, Kitty). Il modulo `curses` è già incluso di serie nell'installazione standard di Python su Unix.
  - **Windows:** Si consiglia vivamente l'uso di **WSL (Windows Subsystem for Linux)** o **Windows Terminal** con il package `windows-curses` (`pip install windows-curses`).

### Clonare il Repository ed Eseguire
```bash
git clone https://github.com/ArturoDente/python-per-nerd.git
cd python-per-nerd

# Esempio: esegui la pioggia di Matrix
python3 matrix/matrix.py

# Esempio: gioca al roguelike PyRogue
python3 pyrogue/main.py
```

---

## 📖 Il Libro Completo

Questo repository include il codice sorgente pronto all'uso. Il libro completo **"Python per Nerds"** offre:
- Trattazione teorica e retrocomputing (la nascita dei particle systems, la demoscene, la storia di Rogue, l'invenzione di Curses);
- Spiegazione didattica riga per riga di ogni algoritmo e scelta architetturale;
- Formule fisiche e matematiche (cinematica, trigonometria, FFT, raycasting su griglia);
- Diagrammi architetturali e schemi di sequenza del Game Loop;
- Esercizi guidati di espansione per ogni progetto.

Disponibile nei formati **EPUB** (ottimizzato per e-reader) e **PDF** (impaginazione editoriale ad alta risoluzione con Typst).

---

## ⚖️ Licenza

Il codice sorgente contenuto in questo repository è distribuito sotto licenza **MIT** (vedi file [`LICENSE`](LICENSE)).  
Sei libero di studiarlo, modificarlo, riutilizzarlo ed estenderlo nei tuoi progetti personali o commerciali.
