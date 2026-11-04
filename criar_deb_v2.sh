#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 📦 Criar pacote .deb — Assistente Virtual v2.0.2
# HCsoftware — Herculano
# ═══════════════════════════════════════════════════════════════
#
# Alterações na 2.0.2:
#  - limpeza interna do código (sem alterações de funcionalidade):
#    comandos ligar/desligar/alternar unificados, helpers MQTT partilhados,
#    cores da interface em constantes, imagens carregadas uma só vez,
#    espera pelo MP3 partilhada entre os dois modos de download
#
# Alterações na 2.0.1:
#  - yt-dlp instalado sempre na versão mais recente, com yt-dlp-ejs ([default])
#  - erro na instalação do yt-dlp pára o build (antes era engolido por "|| true")
#  - launcher garante o deno no PATH (o lançador gráfico não herda o PATH do terminal)
#  - launcher usa o yt-dlp do utilizador se existir (atualizável sem sudo)
#  - novo comando: assistente-virtual-atualizar
#  - removido o bloco do "link simbólico" que nunca funcionou; as músicas ficam em
#    ~/.local/share/assistente-virtual/Download (definido no constants.py)
#  - postinst já não cria pastas em /root e avisa se o deno não estiver instalado

set -e

NOME="assistente-virtual"
VERSAO="2.1.2"
ARCH="all"
MAINTAINER="HCsoftware <herculano@hcsoftware.pt>"
DESCRICAO="Assistente Virtual HCsoftware — Controlo por voz, música e IoT"
DIR_PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
    "hc_theme.json"
    "ollama_client.py"
    "tuya_client.py"
    "dispositivos.json"
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

# Dependências gerais. Se esta instalação falhar, o pacote sai sem as
# bibliotecas gráficas e não abre — por isso a falha agora para o build.
pip3 install --quiet --target="$DEPS_DIR" \
    customtkinter \
    pygame \
    paho-mqtt \
    SpeechRecognition \
    gTTS \
    pydub \
    pillow \
    mutagen \
    tinytuya

# pyaudio é opcional aqui: o pacote já depende de python3-pyaudio (apt).
# Só entra se houver cabeçalhos portaudio na máquina de build.
pip3 install --quiet --target="$DEPS_DIR" pyaudio 2>/dev/null || true

# Rede de segurança: sem estas pastas o programa não arranca.
for dep in customtkinter pygame paho gtts mutagen pydub; do
    if [ ! -d "$DEPS_DIR/$dep" ]; then
        echo -e "  ${RED}❌ Dependência em falta no pacote: $dep${NC}"
        exit 1
    fi
done
echo "  ✅ Dependências essenciais presentes"

# yt-dlp: sempre a versão mais recente, com yt-dlp-ejs ([default]).
# SEM "|| true": se falhar, o build pára em vez de gerar um pacote que não descarrega.
# (--target dispensa --break-system-packages; se o pip se queixar, acrescenta a flag.)
echo "  ⬇️  yt-dlp (última versão)..."
pip3 install --quiet --upgrade --target="$DEPS_DIR" "yt-dlp[default]"

YTDLP_VER=$(PYTHONPATH="$DEPS_DIR" python3 -c "import yt_dlp; print(yt_dlp.version.__version__)")
echo -e "${GREEN}✅ Dependências instaladas (yt-dlp ${YTDLP_VER})${NC}"

# ── Criar wrapper de lançamento ──────────────────────────────────
echo ""
echo "🚀 A criar launcher..."

cat > "$BIN_DIR/assistente-virtual" << 'LAUNCHER'
#!/bin/bash
# Launcher do Assistente Virtual HCsoftware
INSTALL_DIR="/usr/share/assistente-virtual"
USER_DATA="$HOME/.local/share/assistente-virtual"

# O lançador gráfico não herda o PATH do terminal: garantir o deno,
# que o yt-dlp precisa para resolver os desafios JavaScript do YouTube.
export PATH="$HOME/.deno/bin:/usr/local/bin:$PATH"

# Pasta de músicas do utilizador (é a que o constants.py usa)
mkdir -p "$USER_DATA/Download"

exec python3 -c "
import sys, os
sys.path.insert(0, '$INSTALL_DIR/deps')
sys.path.insert(0, '$INSTALL_DIR')
# yt-dlp do utilizador (atualizável sem sudo) tem prioridade sobre o do pacote
ytdlp = os.path.expanduser('~/.local/share/assistente-virtual/ytdlp')
if os.path.isdir(ytdlp):
    sys.path.insert(0, ytdlp)
os.chdir('$INSTALL_DIR')
import main
main.main()
"
LAUNCHER

chmod +x "$BIN_DIR/assistente-virtual"

# ── Comando para atualizar o yt-dlp sem sudo ─────────────────────
cat > "$BIN_DIR/assistente-virtual-atualizar" << 'UPDATER'
#!/bin/bash
# Atualiza o yt-dlp do Assistente Virtual (sem sudo).
# Usar quando aparecer "Falha no download" sem motivo aparente.
DEST="$HOME/.local/share/assistente-virtual/ytdlp"
mkdir -p "$DEST"
python3 -m pip install --upgrade --target "$DEST" "yt-dlp[default]" || exit 1
python3 -c "import sys; sys.path.insert(0, '$DEST'); import yt_dlp; print('yt-dlp', yt_dlp.version.__version__)"
echo "Fecha o Assistente Virtual por completo e abre-o de novo."
UPDATER

chmod +x "$BIN_DIR/assistente-virtual-atualizar"
echo -e "${GREEN}✅ Launcher e atualizador criados${NC}"

# ── Ficheiro .desktop ────────────────────────────────────────────
echo ""
echo "🖥️  A criar entrada no menu..."

# Copiar ícone
if [ -f "$DIR_PROJETO/imagens/chatbot.png" ]; then
    cp "$DIR_PROJETO/imagens/chatbot.png" "$ICON_DIR/assistente-virtual.png"
fi

cat > "$DESKTOP_DIR/assistente-virtual.desktop" << DESKTOP
[Desktop Entry]
Version=2.1.2
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
# (corre como root: não cria pastas do utilizador; a pasta de configuração
#  e a de músicas são criadas pelo próprio programa/launcher, na conta de cada utilizador)
cat > "$DEBIAN_DIR/postinst" << 'POSTINST'
#!/bin/bash
set -e

# Actualizar cache de ícones e menu
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache /usr/share/pixmaps/ 2>/dev/null || true
fi

echo "✅ Assistente Virtual instalado com sucesso!"
echo "   Para iniciar: assistente-virtual"
echo "   Ou procura em: Aplicações → Utilitários"

if ! command -v deno &>/dev/null; then
    echo ""
    echo "⚠️  Nota: o deno é necessário para descarregar música do YouTube."
    echo "   Se ainda não o tens, instala-o com o teu utilizador (sem sudo):"
    echo "   curl -fsSL https://deno.land/install.sh | sh"
fi
echo ""
echo "   Se aparecer 'Falha no download', corre: assistente-virtual-atualizar"
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

# Restaurar permissão de execução nos binários internos do speech_recognition
# (o chmod 644 acima retira-a, e o SpeechRecognition precisa de os executar)
find "$DIR_BUILD" -path "*/speech_recognition/*" -type f \( -name "flac-*" -o -name "*.exe" \) -exec chmod 755 {} \;
chmod 755 "$BIN_DIR/assistente-virtual"
chmod 755 "$BIN_DIR/assistente-virtual-atualizar"
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
echo "  ⬇️  yt-dlp   : $YTDLP_VER"
echo ""
echo "  Para instalar:"
echo "  sudo dpkg -i $DEB_FILE"
echo "  sudo apt-get install -f"
echo ""
echo "  Para iniciar após instalação:"
echo "  assistente-virtual"
echo ""
echo "  Se aparecer 'Falha no download':"
echo "  assistente-virtual-atualizar"
echo "═══════════════════════════════════════════════"
echo ""
