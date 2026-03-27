#!/bin/bash
# Script para criar pacote .deb do Assistente Virtual

set -e  # Parar em caso de erro

echo "=========================================="
echo "📦 CRIAR PACOTE DEB - ASSISTENTE VIRTUAL"
echo "=========================================="
echo

# Definições
NOME="assistente-virtual"
VERSAO="1.0.0"
ARQUITETURA="all"
PACOTE="${NOME}_${VERSAO}_${ARQUITETURA}.deb"
PASTA_TEMP="/tmp/${NOME}_deb"

# Limpar builds anteriores
echo "🧹 A limpar builds anteriores..."
rm -rf "$PASTA_TEMP"
rm -f "$HOME/$PACOTE"

# Criar estrutura de diretórios
echo "📁 A criar estrutura de diretórios..."
mkdir -p "$PASTA_TEMP/DEBIAN"
mkdir -p "$PASTA_TEMP/usr/local/bin"
mkdir -p "$PASTA_TEMP/usr/share/$NOME"
mkdir -p "$PASTA_TEMP/usr/share/applications"
mkdir -p "$PASTA_TEMP/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PASTA_TEMP/usr/share/doc/$NOME"
mkdir -p "$PASTA_TEMP/usr/share/man/man1"
mkdir -p "$PASTA_TEMP/etc/$NOME"

# Verificar se a pasta do projeto existe
if [ ! -d "$HOME/Assistente Virtual" ]; then
    echo "❌ Erro: Pasta '$HOME/Assistente Virtual' não encontrada!"
    exit 1
fi

# Copiar ficheiros do projeto
echo "📂 A copiar ficheiros do projeto..."
cp -v "$HOME/Assistente Virtual"/*.py "$PASTA_TEMP/usr/share/$NOME/" 2>/dev/null || echo "⚠️  Nenhum ficheiro .py encontrado"
cp -v "$HOME/Assistente Virtual"/*.json "$PASTA_TEMP/usr/share/$NOME/" 2>/dev/null || echo "⚠️  Nenhum ficheiro .json encontrado"

# Copiar pastas se existirem
if [ -d "$HOME/Assistente Virtual/Download" ]; then
    cp -r "$HOME/Assistente Virtual/Download" "$PASTA_TEMP/usr/share/$NOME/"
fi

if [ -d "$HOME/Assistente Virtual/imagens" ]; then
    cp -r "$HOME/Assistente Virtual/imagens" "$PASTA_TEMP/usr/share/$NOME/"
fi

if [ -d "$HOME/Assistente Virtual/ffmpeg" ]; then
    cp -r "$HOME/Assistente Virtual/ffmpeg" "$PASTA_TEMP/usr/share/$NOME/"
fi

# Criar ficheiro de configuração padrão
echo "⚙️  A criar configuração padrão..."
cat > "$PASTA_TEMP/etc/$NOME/config.ini" << 'CFG'
[MQTT]
host = localhost
port = 1883
username = 
password = 
CFG

# Criar script de execução
echo "🚀 A criar executável..."
cat > "$PASTA_TEMP/usr/local/bin/$NOME" << 'BIN'
#!/bin/bash
cd /usr/share/assistente-virtual
python3 main.py
BIN
chmod 755 "$PASTA_TEMP/usr/local/bin/$NOME"

# Criar ficheiro de controlo
echo "📝 A criar ficheiro de controlo..."
cat > "$PASTA_TEMP/DEBIAN/control" << CTRL
Package: $NOME
Version: $VERSAO
Section: utils
Priority: optional
Architecture: $ARQUITETURA
Depends: python3 (>= 3.8), python3-pip, python3-venv, python3-pil, python3-tk, python3-pyaudio, python3-paho-mqtt, python3-pygame, ffmpeg, alsa-utils, pulseaudio, python3-requests
Recommends: python3-yt-dlp, python3-gtts, python3-speechrecognition, python3-customtkinter
Maintainer: Herculano <herculano@local>
Homepage: https://github.com/herculano/assistente-virtual
Description: Assistente Virtual com comando de voz, música e controlo IoT
 Um assistente virtual completo que permite:
  - Controlo por voz de dispositivos (walkie-talkie)
  - Reprodução de música do YouTube
  - Controlo de dispositivos IoT via MQTT
  - Pesquisa na web
  - Informações de data e hora
  - Interface gráfica moderna com CustomTkinter
 .
 Modo walkie-talkie: clica no botão para falar, larga para parar.
 Sem eco, sem feedback de áudio durante comando de voz.
CTRL

# Criar script pós-instalação
echo "🔧 A criar script pós-instalação..."
cat > "$PASTA_TEMP/DEBIAN/postinst" << 'POST'
#!/bin/bash
set -e

echo "📦 A configurar Assistente Virtual..."

# Criar ambiente virtual
cd /usr/share/assistente-virtual
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || true

# Instalar dependências Python
pip install --upgrade pip 2>/dev/null || true
pip install customtkinter pygame yt-dlp paho-mqtt SpeechRecognition gTTS pydub pillow pyaudio requests 2>/dev/null || true

# Copiar configuração para cada utilizador
for user in /home/*; do
    if [ -d "$user" ]; then
        username=$(basename "$user")
        mkdir -p "$user/.config/assistente-virtual"
        if [ ! -f "$user/.config/assistente-virtual/config.ini" ]; then
            cp /etc/assistente-virtual/config.ini "$user/.config/assistente-virtual/" 2>/dev/null || true
        fi
        chown -R "$username:$username" "$user/.config/assistente-virtual" 2>/dev/null || true
        
        # Adicionar ao grupo audio
        usermod -a -G audio "$username" 2>/dev/null || true
    fi
done

echo "✅ Assistente Virtual configurado com sucesso!"
echo "🎤 Para iniciar, executa: assistente-virtual"
echo "📖 Manual: man assistente-virtual"
POST
chmod 755 "$PASTA_TEMP/DEBIAN/postinst"

# Criar script pós-remoção
echo "🗑️  A criar script pós-remoção..."
cat > "$PASTA_TEMP/DEBIAN/postrm" << 'POSTRM'
#!/bin/bash
set -e

if [ "$1" = "remove" ]; then
    echo "🗑️  A remover Assistente Virtual..."
    # Perguntar se quer manter configurações
    for user in /home/*; do
        if [ -d "$user" ]; then
            rm -rf "$user/.config/assistente-virtual" 2>/dev/null || true
        fi
    done
    echo "✅ Assistente Virtual removido."
fi
POSTRM
chmod 755 "$PASTA_TEMP/DEBIAN/postrm"

# Criar atalho no menu
echo "🖥️  A criar atalho no menu..."
cat > "$PASTA_TEMP/usr/share/applications/$NOME.desktop" << DESKTOP
[Desktop Entry]
Name=Assistente Virtual
Comment=Assistente Virtual com comando de voz
Exec=$NOME
Icon=$NOME
Terminal=false
Type=Application
Categories=Utility;AudioVideo;IoT;
Keywords=voice;assistant;iot;mqtt;music;
StartupNotify=true
DESKTOP

# Criar ícone (se existir)
if [ -f "$HOME/Assistente Virtual/imagens/chatbot.png" ]; then
    cp "$HOME/Assistente Virtual/imagens/chatbot.png" "$PASTA_TEMP/usr/share/icons/hicolor/256x256/apps/$NOME.png"
else
    # Criar ícone simples com texto
    echo "🤖" > "$PASTA_TEMP/usr/share/icons/hicolor/256x256/apps/$NOME"
fi

# Criar página de manual
echo "📖 A criar página de manual..."
cat > "$PASTA_TEMP/usr/share/man/man1/$NOME.1" << MAN
.TH ASSISTENTE-VIRTUAL 1 "Fevereiro 2026" "1.0.0" "Comandos do Utilizador"

.SH NOME
assistente\-virtual \- Assistente Virtual com comando de voz

.SH SINOPSE
.B assistente\-virtual

.SH DESCRIÇÃO
Assistente Virtual com reconhecimento de voz (modo walkie\-talkie), 
reprodução de música do YouTube e controlo de dispositivos IoT via MQTT.

.SH MODO DE VOZ
O assistente usa modo walkie\-talkie para evitar eco:
- Clique no botão "VOZ" para ativar o microfone
- Fale o comando (tem 3 segundos)
- O microfone desativa automaticamente após o comando

.SH COMANDOS DE VOZ
.TP
.B Música
tocar <nome>, pausar, continuar, parar
.TP
.B Dispositivos
ligar <dispositivo>, desligar <dispositivo>
.TP
.B Utilitários
que horas são, que dia é hoje
.TP
.B Web
youtube <termo>, pesquisar <termo>

.SH FICHEIROS
.TP
.I ~/.config/assistente-virtual/config.ini
Configuração do MQTT

.SH EXEMPLOS
.TP
.B Ligar dispositivo
ligar varanda
.TP
.B Tocar música
tocar my way - frank sinatra

.SH AUTOR
Herculano <herculano@local>

.SH BUGS
Reportar bugs para: herculano@local
MAN

gzip -9 "$PASTA_TEMP/usr/share/man/man1/$NOME.1"

# Criar documentação
echo "📚 A criar documentação..."
cat > "$PASTA_TEMP/usr/share/doc/$NOME/README" << README
ASSISTENTE VIRTUAL
==================
Versão: $VERSAO

DESCRIÇÃO
---------
Um assistente virtual completo com:
- Reconhecimento de voz (modo walkie-talkie, sem eco)
- Reprodução de música do YouTube
- Controlo de dispositivos IoT (MQTT)
- Pesquisa na web
- Informações de data/hora
- Interface gráfica moderna

INSTALAÇÃO
----------
sudo dpkg -i assistente-virtual_${VERSAO}_all.deb
sudo apt-get install -f

COMO USAR
---------
1. Iniciar: assistente-virtual
2. Ativar voz: clique no botão "VOZ"
3. Fale o comando (tem 3 segundos)
4. O microfone desativa automaticamente

EXEMPLOS DE COMANDOS
--------------------
- "ligar varanda"
- "desligar quarto 3"
- "tocar my way - frank sinatra"
- "que horas são"
- "youtube teste"

CONFIGURAÇÃO
------------
Ficheiro: ~/.config/assistente-virtual/config.ini

MQTT:
host = 192.168.1.54
port = 1883
username = 
password = 

DEPENDÊNCIAS
------------
- Python 3.8+
- Pygame, yt-dlp, paho-mqtt
- customtkinter, speechrecognition
- gTTS, pyaudio

RELATAR PROBLEMAS
-----------------
Email: herculano@local

LICENÇA
-------
GPL v3
README

# Comprimir documentação
gzip -9 "$PASTA_TEMP/usr/share/doc/$NOME/README"

# Criar ficheiro de licença
cat > "$PASTA_TEMP/usr/share/doc/$NOME/copyright" << COPY
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: assistente-virtual
Source: https://github.com/herculano/assistente-virtual

Files: *
Copyright: 2026 Herculano <herculano@local>
License: GPL-3+
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 .
 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
COPY

# Calcular tamanho e criar md5sums
echo "🔍 A calcular checksums..."
cd "$PASTA_TEMP"
find usr -type f -exec md5sum {} \; > DEBIAN/md5sums 2>/dev/null || true
find etc -type f -exec md5sum {} \; >> DEBIAN/md5sums 2>/dev/null || true
cd - > /dev/null

# Ajustar permissões
echo "🔧 A ajustar permissões..."
find "$PASTA_TEMP" -type d -exec chmod 755 {} \;
find "$PASTA_TEMP" -type f -exec chmod 644 {} \;
chmod 755 "$PASTA_TEMP/DEBIAN/postinst"
chmod 755 "$PASTA_TEMP/DEBIAN/postrm"
chmod 755 "$PASTA_TEMP/usr/local/bin/$NOME"

# Listar conteúdo para verificar
echo "📋 Conteúdo do pacote:"
ls -la "$PASTA_TEMP/usr/share/$NOME/"

# Construir pacote
echo "📦 A construir pacote..."
cd "$PASTA_TEMP/.."
dpkg-deb --build "$(basename "$PASTA_TEMP")"
if [ -f "$(basename "$PASTA_TEMP").deb" ]; then
    mv "$(basename "$PASTA_TEMP").deb" "$HOME/$PACOTE"
    echo "✅ Pacote movido para: $HOME/$PACOTE"
else
    echo "❌ Erro: Pacote não foi criado!"
    exit 1
fi
cd - > /dev/null

# Limpar
echo "🧹 A limpar ficheiros temporários..."
rm -rf "$PASTA_TEMP"

echo "=========================================="
echo "✅ PACOTE CRIADO COM SUCESSO!"
echo "=========================================="
echo
echo "📦 Ficheiro: $HOME/$PACOTE"
echo "📦 Tamanho: $(du -h $HOME/$PACOTE | cut -f1)"
echo
echo "📥 Para instalar:"
echo "   sudo dpkg -i $HOME/$PACOTE"
echo "   sudo apt-get install -f"
echo
echo "🚀 Para executar:"
echo "   assistente-virtual"
echo
echo "📖 Manual:"
echo "   man assistente-virtual"
echo
echo "=========================================="
