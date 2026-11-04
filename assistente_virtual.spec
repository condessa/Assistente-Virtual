# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller — Assistente Virtual (Windows)

Gera um único ficheiro: dist/AssistenteVirtual.exe

Uso local (Windows):
    pip install -r requirements.txt pyinstaller
    python -m PyInstaller assistente_virtual.spec --noconfirm --clean

No GitHub o build corre sozinho: .github/workflows/build-windows.yml
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_NAME = "AssistenteVirtual"

# ── Recursos que o programa lê em tempo de execução ─────────────────────────
datas = [
    ("commands.json", "."),      # comandos de voz/texto
    ("hc_theme.json", "."),      # tema do customtkinter
    ("imagens", "imagens"),      # logo, ícone
]
datas += collect_data_files("customtkinter")   # temas e fontes do customtkinter

# ── ffmpeg/ffprobe embutidos (descarregados pelo workflow para ffmpeg/bin) ──
binaries = []
_ffmpeg_dir = os.path.join("ffmpeg", "bin")
if os.path.isdir(_ffmpeg_dir):
    for _f in sorted(os.listdir(_ffmpeg_dir)):
        binaries.append((os.path.join(_ffmpeg_dir, _f), "ffmpeg/bin"))

# ── Módulos carregados dinamicamente (extratores do yt-dlp, etc.) ───────────
hiddenimports = [
    "paho.mqtt.client",
    "pydub",
    "mutagen",
    "mutagen.id3",
    "tinytuya",
    "requests",
    "speech_recognition",
    "speech_recognition.recognizers",
    "pyaudio",
    "gtts",
    "pygame",
    "PIL._tkinter_finder",
    "ollama_client",
    "tuya_client",
    "tooltip",
    "config_window",
    "help_window",
    "playlist_window",
    "devices_window",
]
# O yt-dlp carrega os extractores por import dinâmico.
# Nota: nada de emojis nem acentos nestas mensagens — o spec corre com a
# codepage cp1252 no Windows e um print() rebenta o build.
_modulos_ytdlp = collect_submodules("yt_dlp")
if not _modulos_ytdlp:
    raise SystemExit(
        "yt-dlp nao esta instalado no ambiente de build - sem ele a musica nao "
        "funcionaria no .exe. Corre: pip install -r requirements.txt"
    )
hiddenimports += _modulos_ytdlp
print("[build] yt-dlp: %d modulos incluidas" % len(_modulos_ytdlp))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "scipy", "librosa", "numba",
        "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
        "IPython", "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join("imagens", "chatbot.ico"),
)
