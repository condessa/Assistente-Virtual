#!/bin/bash
echo "=========================================="
echo "🎙️  Instalação do Assistente Virtual"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado. Instala o Python 3.8 ou superior.${NC}"
    exit 1
fi

PY_VERSION=$(python3 --version)
echo -e "${GREEN}✅ ${PY_VERSION} encontrado${NC}"

# Cria ambiente virtual (opcional)
echo ""
echo -e "${YELLOW}Desejas criar um ambiente virtual? (recomendado) [s/N]:${NC} "
read -r criar_venv

if [[ "$criar_venv" =~ ^[Ss]$ ]]; then
    echo "📦 A criar ambiente virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"
fi

# Atualiza pip
echo ""
echo "📦 A atualizar pip..."
python3 -m pip install --upgrade pip

# Instala dependências
echo ""
echo "📦 A instalar dependências..."
echo ""

# Dependências principais
DEPS=(
    "customtkinter"
    "pygame"
    "yt-dlp"
    "paho-mqtt"
    "SpeechRecognition"
    "gTTS"
    "pydub"
    "pillow"
)

for dep in "${DEPS[@]}"; do
    echo -n "📥 $dep ... "
    if python3 -m pip install --quiet "$dep"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FALHOU${NC}"
    fi
done

# PyAudio (pode precisar de dependências de sistema)
echo ""
echo "📦 A instalar PyAudio (pode pedir senha)..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get install -y portaudio19-dev python3-pyaudio
    python3 -m pip install pyaudio
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install portaudio
    python3 -m pip install pyaudio
else
    python3 -m pip install pyaudio
fi

# FFmpeg
echo ""
echo "📦 A verificar FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  FFmpeg não encontrado. A tentar instalar...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y ffmpeg
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    else
        echo "⚠️  Por favor, instala o FFmpeg manualmente: https://ffmpeg.org/download.html"
    fi
else
    echo -e "${GREEN}✅ FFmpeg encontrado${NC}"
fi

# Cria pastas necessárias
echo ""
echo "📁 A criar pastas..."
mkdir -p Download imagens
mkdir -p ffmpeg/bin  # Para ffmpeg local (opcional)

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "Para executar o assistente:"
echo "  python3 main.py"
echo ""

if [[ "$criar_venv" =~ ^[Ss]$ ]]; then
    echo "Nota: O ambiente virtual está ativo. Para reativar no futuro:"
    echo "  source venv/bin/activate"
    echo "  python main.py"
fi
