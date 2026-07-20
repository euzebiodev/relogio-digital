# Relógio Digital

A lightweight, always-on-top digital clock widget for Windows built with PyQt6. Features a retro terminal aesthetic with neon colors, animated fire effects, system tray integration, and full configuration persistence.

## Features

- **Multiple visual themes** — Green Neon, Amber, Red LED, Cyan/Holographic, "The Three-Body Problem" (animated fire) and more
- **Multiple display fonts** — custom-rendered 7-segment LED, DSEG7 Classic/Mini/Modern, DSEG14, Bebas Neue, Orbitron, and common monospace fonts
- **Animated fire effect** — multi-layer Bézier strand animation for the "Three-Body Problem" theme
- **Hover-to-reveal controls** — buttons appear only when the mouse is over the clock
- **System tray icon** — minimize to tray, restore with a click, right-click menu to quit
- **Windows autostart** — optional launch on Windows startup via registry (`HKCU\...\Run`)
- **Persistent settings** — font, size, theme, opacity, and always-on-top saved across restarts (`%APPDATA%\relogio-digital\settings.ini`)
- **Always on top** — toggleable, so the clock stays visible over other windows
- **Adjustable opacity** — background transparency slider
- **Standalone** — distributed as a single installer, no Python required on the target machine

## Screenshots

> _Add screenshots here_

## Requirements

### To run from source

- Python 3.10+
- PyQt6

```bash
pip install -r requirements.txt
```

### To run the installed version

No requirements — use the installer from the [Releases](../../releases) page.

## Running from source

```bash
# With terminal (shows logs)
python main.py

# Without terminal window
pythonw main.py
```

## Building the installer

1. Install [PyInstaller](https://pyinstaller.org):
   ```bash
   pip install pyinstaller
   ```
2. Build the standalone executable:
   ```bash
   pyinstaller --onedir --windowed --name RelogioDigital --collect-all PyQt6 main.py
   ```
3. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) and compile the installer:
   ```bash
   ISCC.exe installer.iss
   ```
   The output will be at `installer_output\RelogioDigital-Setup.exe`.

## Usage

| Action | Result |
|---|---|
| Hover over the clock | Control buttons appear |
| Move mouse away | Controls hide after 500 ms |
| Left-click + drag | Move the window |
| Right-click | Open context menu |
| Tray icon left-click | Show / hide the clock |
| Tray icon right-click | Context menu with Quit |

### Controls

| Button | Description |
|---|---|
| `F` | Change font |
| `−` / `+` | Decrease / increase font size |
| `T` | Cycle through color themes |
| Opacity slider | Adjust background transparency |
| `⊤` | Toggle always-on-top |
| `✕` | Hide to system tray |

## Color themes

| Theme | Description |
|---|---|
| Verde neon | Classic green terminal |
| Verde escuro | Darker green |
| Âmbar | Amber LCD |
| Vermelho LED | Red LED |
| Branco | White |
| Preto | Black |
| Ciano / Holográfico | Cyan with glow and scan-line effect |
| O Problema dos 3 Corpos | Animated fire effect (Bebas Neue recommended) |

## Font presets

| Font | Style |
|---|---|
| 7 Segmentos LED | Custom-rendered seven-segment display (default) |
| DSEG7 Classic | Retro LCD |
| DSEG7 Classic Mini | Compact LCD |
| DSEG7 Modern | Modern LCD |
| DSEG14 Classic | 14-segment display |
| Bebas Neue | Cinematic / fire |
| Orbitron | Sci-fi / futuristic |
| Consolas / Courier New / Lucida Console / OCR A Extended | Monospace system fonts |

## Settings file

Settings are stored at:

```
%APPDATA%\relogio-digital\settings.ini
```

Fonts are cached at:

```
%APPDATA%\relogio-digital\fonts\
```

## Autostart

Toggle autostart from the right-click context menu. The app writes to:

```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

It is removed automatically on uninstall.

## Project structure

```
relogio-digital/
├── main.py            # Application source (single file)
├── installer.iss      # Inno Setup script
├── requirements.txt   # Python dependencies
└── instalar_e_rodar.bat  # Helper script for first-time source run
```

## License

MIT
