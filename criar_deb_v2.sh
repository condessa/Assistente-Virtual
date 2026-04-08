#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 📦 Criar pacote .deb — Assistente Virtual v2.0.0
# HCsoftware — Herculano
# ═══════════════════════════════════════════════════════════════

set -e

NOME="assistente-virtual"
VERSAO="2.0.0"
ARCH="all"
MAINTAINER="HCsoftware <herculano@hcsoftware.pt>"
DESCRICAO="Assistente Virtual HCsoftware — Controlo por voz, música e IoT"
DIR_PROJETO="$HOME/Programas/Assistente Virtual"
DIR_BUILD="/tmp/${NOME}_${VERSAO}"
DIR_DIST="$DIR_PROJETO/dist"
DEB_FILE="${DIR_DIST}/${NOME}_${VERSAO}_${ARCH}.deb"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════"
echo "  📦  Assistente Virtual — Criar .deb v${VERSAO}"
echo "═══════════════════════════════════════════════"
echo ""

# ── Verificar dependências ───────────────────────────────────────
for cmd in python3 pip3 dpkg-deb; do
    if ! command -v $cmd &>/dev/null; then
        echo -e "${RED}❌ $cmd não encontrado${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ Dependências OK${NC}"

# ── Limpar build anterior ────────────────────────────────────────
rm -rf "$DIR_BUILD"
mkdir -p "$DIR_DIST"

# ── Estrutura de directorias do pacote ──────────────────────────
echo ""
echo "📁 A criar estrutura do pacote..."

INSTALL_DIR="$DIR_BUILD/usr/share/assistente-virtual"
BIN_DIR="$DIR_BUILD/usr/local/bin"
DESKTOP_DIR="$DIR_BUILD/usr/share/applications"
ICON_DIR="$DIR_BUILD/usr/share/pixmaps"
DOC_DIR="$DIR_BUILD/usr/share/doc/${NOME}"
DEBIAN_DIR="$DIR_BUILD/DEBIAN"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DOC_DIR"
mkdir -p "$DEBIAN_DIR"
mkdir -p "$INSTALL_DIR/Download"
mkdir -p "$INSTALL_DIR/imagens"

echo -e "${GREEN}✅ Estrutura criada${NC}"

# ── Copiar ficheiros do projecto ─────────────────────────────────
echo ""
echo "📋 A copiar ficheiros..."

# Ficheiros Python principais
FICHEIROS_PY=(
    "main.py"
    "gui.py"
    "command_processor.py"
    "music_player.py"
    "playlist_window.py"
    "devices_window.py"
    "help_window.py"
    "mqtt_handler.py"
    "voice.py"
    "tts.py"
    "extrator_faixas.py"
    "config_window.py"
    "constants.py"
    "tooltip.py"
    "commands.json"
)

for f in "${FICHEIROS_PY[@]}"; do
    if [ -f "$DIR_PROJETO/$f" ]; then
        cp "$DIR_PROJETO/$f" "$INSTALL_DIR/"
        echo "  ✅ $f"
    else
        echo -e "  ${YELLOW}⚠️  $f não encontrado${NC}"
    fi
done

# Imagens
if [ -d "$DIR_PROJETO/imagens" ]; then
    cp -r "$DIR_PROJETO/imagens/." "$INSTALL_DIR/imagens/"
    echo "  ✅ imagens/"
fi

# README e LICENSE
for f in README.md LICENSE; do
    [ -f "$DIR_PROJETO/$f" ] && cp "$DIR_PROJETO/$f" "$DOC_DIR/"
done

echo -e "${GREEN}✅ Ficheiros copiados${NC}"

# ── Instalar dependências Python no pacote ───────────────────────
echo ""
echo "📦 A instalar dependências Python no pacote..."

DEPS_DIR="$INSTALL_DIR/deps"
mkdir -p "$DEPS_DIR"

pip3 install --quiet --target="$DEPS_DIR" \
    customtkinter \
    pygame \
    yt-dlp \
    paho-mqtt \
    SpeechRecognition \
    gTTS \
    pydub \
    pillow \
    mutagen \
    pyaudio 2>/dev/null || true

echo -e "${GREEN}✅ Dependências instaladas${NC}"

# ── Criar wrapper de lançamento ──────────────────────────────────
echo ""
echo "🚀 A criar launcher..."

cat > "$BIN_DIR/assistente-virtual" << 'LAUNCHER'
#!/bin/bash
# Launcher do Assistente Virtual HCsoftware
INSTALL_DIR="/usr/share/assistente-virtual"
PYTHONPATH="$INSTALL_DIR/deps:$INSTALL_DIR"

# Criar pasta Download do utilizador se não existir
mkdir -p "$HOME/.local/share/assistente-virtual/Download"

# Link simbólico para a pasta Download do utilizador
if [ ! -L "$INSTALL_DIR/Download" ]; then
    rm -rf "$INSTALL_DIR/Download" 2>/dev/null || true
fi

exec python3 -c "
import sys, os
sys.path.insert(0, '$INSTALL_DIR/deps')
sys.path.insert(0, '$INSTALL_DIR')
os.chdir('$INSTALL_DIR')
import main
main.main()
"
LAUNCHER

chmod +x "$BIN_DIR/assistente-virtual"
echo -e "${GREEN}✅ Launcher criado${NC}"

# ── Ficheiro .desktop ────────────────────────────────────────────
echo ""
echo "🖥️  A criar entrada no menu..."

# Copiar ícone
if [ -f "$DIR_PROJETO/imagens/chatbot.png" ]; then
    cp "$DIR_PROJETO/imagens/chatbot.png" "$ICON_DIR/assistente-virtual.png"
fi

cat > "$DESKTOP_DIR/assistente-virtual.desktop" << DESKTOP
[Desktop Entry]
Version=2.0.0
Type=Application
Name=Assistente Virtual
Name[pt]=Assistente Virtual
Comment=Assistente virtual com controlo por voz, música e IoT
Comment[pt]=Assistente virtual com controlo por voz, música e dispositivos IoT
Exec=assistente-virtual
Icon=assistente-virtual
Terminal=false
Categories=Utility;AudioVideo;
Keywords=assistente;voz;música;iot;mqtt;
StartupNotify=true
DESKTOP

echo -e "${GREEN}✅ Ficheiro .desktop criado${NC}"

# ── DEBIAN/control ───────────────────────────────────────────────
echo ""
echo "📄 A criar metadados do pacote..."

cat > "$DEBIAN_DIR/control" << CONTROL
Package: ${NOME}
Version: ${VERSAO}
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Depends: python3 (>= 3.10), python3-pip, ffmpeg, portaudio19-dev, python3-pyaudio
Recommends: pulseaudio
Section: utils
Priority: optional
Homepage: https://github.com/condessa/Assistente-Virtual
Description: ${DESCRICAO}
 Assistente Virtual HCsoftware v${VERSAO}
 .
 Funcionalidades:
  - Reconhecimento de voz (modo walkie-talkie)
  - Player de música com download automático do YouTube
  - Controlo de dispositivos IoT via MQTT (Tasmota)
  - Extractor de faixas de álbuns via ffmpeg
  - Interface gráfica moderna (CustomTkinter)
  - Tema claro/escuro
CONTROL

# ── DEBIAN/postinst ──────────────────────────────────────────────
cat > "$DEBIAN_DIR/postinst" << 'POSTINST'
#!/bin/bash
set -e

# Criar pasta de configuração do utilizador
CONFIG_DIR="$HOME/.config/assistente-virtual"
mkdir -p "$CONFIG_DIR"

# Actualizar cache de ícones e menu
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache /usr/share/pixmaps/ 2>/dev/null || true
fi

echo "✅ Assistente Virtual v2.0.0 instalado com sucesso!"
echo "   Para iniciar: assistente-virtual"
echo "   Ou procura em: Aplicações → Utilitários"
POSTINST
chmod +x "$DEBIAN_DIR/postinst"

# ── DEBIAN/prerm ─────────────────────────────────────────────────
cat > "$DEBIAN_DIR/prerm" << 'PRERM'
#!/bin/bash
set -e
echo "A remover Assistente Virtual..."
PRERM
chmod +x "$DEBIAN_DIR/prerm"

echo -e "${GREEN}✅ Metadados criados${NC}"

# ── Calcular tamanho instalado ───────────────────────────────────
INSTALLED_SIZE=$(du -sk "$DIR_BUILD" | cut -f1)
echo "Installed-Size: ${INSTALLED_SIZE}" >> "$DEBIAN_DIR/control"

# ── Definir permissões ───────────────────────────────────────────
echo ""
echo "🔒 A definir permissões..."
find "$DIR_BUILD" -type d -exec chmod 755 {} \;
find "$DIR_BUILD" -type f -exec chmod 644 {} \;
chmod 755 "$BIN_DIR/assistente-virtual"
chmod 755 "$DEBIAN_DIR/postinst"
chmod 755 "$DEBIAN_DIR/prerm"
echo -e "${GREEN}✅ Permissões definidas${NC}"

# ── Construir o .deb ─────────────────────────────────────────────
echo ""
echo "🔨 A construir o pacote .deb..."
dpkg-deb --build --root-owner-group "$DIR_BUILD" "$DEB_FILE"
echo -e "${GREEN}✅ Pacote criado${NC}"

# ── Limpar build ─────────────────────────────────────────────────
rm -rf "$DIR_BUILD"

# ── Resultado ────────────────────────────────────────────────────
TAMANHO=$(du -sh "$DEB_FILE" | cut -f1)
echo ""
echo "═══════════════════════════════════════════════"
echo -e "${GREEN}  ✅ Pacote .deb criado com sucesso!${NC}"
echo "═══════════════════════════════════════════════"
echo "  📦 Ficheiro : $DEB_FILE"
echo "  📏 Tamanho  : $TAMANHO"
echo ""
echo "  Para instalar:"
echo "  sudo dpkg -i $DEB_FILE"
echo "  sudo apt-get install -f"
echo ""
echo "  Para iniciar após instalação:"
echo "  assistente-virtual"
echo "═══════════════════════════════════════════════"
echo ""
