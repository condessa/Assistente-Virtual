#!/bin/bash
echo "📦 A instalar dependências do Assistente Virtual..."

# Lista de pacotes necessários
PACOTES=(
    "customtkinter"
    "pygame"
    "yt-dlp"
    "paho-mqtt"
    "SpeechRecognition"
    "gTTS"
    "pydub"
    "pillow"
    "pyaudio"
)

# Instalar cada pacote
for pacote in "${PACOTES[@]}"; do
    echo -n "📥 $pacote ... "
    if pip3 install --quiet "$pacote"; then
        echo "✅ OK"
    else
        echo "❌ FALHOU"
    fi
done

# Verificar instalação do customtkinter
echo ""
echo "🔍 A verificar instalação..."
python3 -c "import customtkinter; print('✅ customtkinter:', customtkinter.__version__)" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "🎉 Todas as dependências instaladas com sucesso!"
    echo ""
    echo "Para executar o assistente:"
    echo "  cd ~/Assistente\ Virtual"
    echo "  python3 main.py"
else
    echo "❌ Problema na instalação do customtkinter"
    echo "Tenta instalar manualmente:"
    echo "  pip3 install customtkinter --upgrade"
fi
