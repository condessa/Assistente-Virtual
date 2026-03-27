#!/bin/bash
# ==========================================
# 🚀 PUBLICAR ASSISTENTE VIRTUAL NO GITHUB
# ==========================================

set -e

# ── Configuração ───────────────────────────────────────────────
REPO_NOME="Assistente-Virtual"
GITHUB_USER="condessa"
VERSAO="1.0.0"
DESCRICAO="Assistente Virtual com comando de voz, música e controlo IoT via MQTT"
DIR_PROJETO=~/Programas/Assistente\ Virtual
PACOTE_DEB="$HOME/assistente-virtual_${VERSAO}_all.deb"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🚀 PUBLICAR ASSISTENTE VIRTUAL NO GITHUB${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# ── Verificações iniciais ──────────────────────────────────────

# Verificar git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ git não encontrado. Instala com: sudo apt install git${NC}"
    exit 1
fi

# Verificar gh CLI
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) não encontrado.${NC}"
    echo "   Instala com:"
    echo "   sudo apt install gh"
    echo "   ou: https://cli.github.com/"
    exit 1
fi

# Verificar autenticação
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Não estás autenticado no GitHub CLI.${NC}"
    echo "   Executa: gh auth login"
    exit 1
fi

echo -e "${GREEN}✅ git e gh CLI encontrados${NC}"

# ── Verificar/criar pacote .deb ────────────────────────────────
echo ""
echo "📦 A verificar pacote .deb..."

if [ ! -f "$PACOTE_DEB" ]; then
    echo -e "${YELLOW}⚠️  Pacote .deb não encontrado. A criar...${NC}"
    cd "$DIR_PROJETO"
    bash criar_pacote_deb.sh
    if [ ! -f "$PACOTE_DEB" ]; then
        echo -e "${RED}❌ Falhou a criar o pacote .deb${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Pacote encontrado: $(basename $PACOTE_DEB) ($(du -h "$PACOTE_DEB" | cut -f1))${NC}"

# ── Ir para pasta do projeto ───────────────────────────────────
cd "$DIR_PROJETO"
echo ""
echo "📂 Pasta: $(pwd)"

# ── Inicializar repositório git se necessário ──────────────────
if [ ! -d ".git" ]; then
    echo ""
    echo "🔧 A inicializar repositório git..."
    git init
    git branch -M main
    echo -e "${GREEN}✅ Repositório git inicializado${NC}"
fi

# ── Criar/atualizar .gitignore ─────────────────────────────────
echo ""
echo "📝 A criar .gitignore..."
cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
venv/
.venv/
env/
*.egg-info/

# Configuração local (contém passwords MQTT)
config.ini

# Downloads de música
Download/

# Ficheiros temporários
*.tmp
*.log
*.bak

# Build
build/
dist/
*.spec

# IDE
.vscode/
.idea/
*.swp
*~

# Sistema
.DS_Store
Thumbs.db
GITIGNORE

echo -e "${GREEN}✅ .gitignore criado${NC}"

# ── Criar README.md ────────────────────────────────────────────
echo ""
echo "📖 A criar README.md..."
cat > README.md << README
# 🎙️ Assistente Virtual

**Versão:** ${VERSAO}  
**Plataforma:** Linux (Debian/Ubuntu) | Windows  
**Linguagem:** Python 3 + CustomTkinter

Um assistente virtual completo com reconhecimento de voz, reprodução de música do YouTube e controlo de dispositivos IoT via MQTT (Tasmota).

---

## ✨ Funcionalidades

- 🎤 **Reconhecimento de voz** — modo walkie-talkie, sem eco
- 🎵 **Player de música** — pesquisa e descarrega do YouTube automaticamente
- 🏠 **Controlo IoT** — liga/desliga dispositivos Tasmota via MQTT
- 🚪 **Controlo de porta** — abre a porta com comando de voz
- 🌐 **Pesquisa na web** — Google e YouTube diretamente por voz
- 🕒 **Utilitários** — horas, data
- 🌙 **Tema claro/escuro** — alternável em tempo real
- 🔊 **Volume ajustável** — slider com valor em percentagem

---

## 📥 Instalação (Debian/Ubuntu)

### Opção 1 — Pacote .deb (recomendado)

\`\`\`bash
sudo dpkg -i assistente-virtual_${VERSAO}_all.deb
sudo apt-get install -f
\`\`\`

### Opção 2 — A partir do código fonte

\`\`\`bash
git clone https://github.com/${GITHUB_USER}/${REPO_NOME}.git
cd ${REPO_NOME}
bash instalar_dependencias.sh
python3 main.py
\`\`\`

### Dependências de sistema

\`\`\`bash
sudo apt install python3 python3-pip python3-venv portaudio19-dev python3-pyaudio ffmpeg
\`\`\`

### Dependências Python

\`\`\`bash
pip install customtkinter pygame yt-dlp paho-mqtt SpeechRecognition gTTS pydub pillow pyaudio
\`\`\`

---

## ⚙️ Configuração MQTT

Na primeira execução é pedida a configuração MQTT. Podes também editar manualmente:

\`\`\`ini
[MQTT]
host = 192.168.1.x
port = 1883
username = 
password = 
\`\`\`

---

## 🎤 Comandos de voz disponíveis

| Categoria | Exemplos |
|-----------|---------|
| **Música** | \`toca o melhor de Luiz Góis\`, \`pausar\`, \`continuar\`, \`parar\` |
| **Volume** | \`volume 80\` |
| **Porta** | \`abre a porta\`, \`abrir porta\`, \`abre porta da sala\` |
| **Luzes** | \`liga varanda\`, \`desliga quarto 3\`, \`acende fluorescente\` |
| **Web** | \`pesquisa na web Python\`, \`abre no youtube Luiz Góis\` |
| **Utilitários** | \`que horas são\`, \`que dia é hoje\`, \`ajuda\` |

---

## 🏗️ Estrutura do projeto

\`\`\`
Assistente Virtual/
├── main.py                 # Ponto de entrada
├── gui.py                  # Interface gráfica (CustomTkinter)
├── command_processor.py    # Motor de comandos
├── music_player.py         # Player + download YouTube
├── mqtt_handler.py         # Comunicação MQTT
├── voice.py                # Reconhecimento de voz
├── tts.py                  # Text-to-Speech (gTTS)
├── commands.json           # Definição de comandos
├── config.ini              # Configuração MQTT (não incluído no git)
├── instalar_dependencias.sh
└── criar_pacote_deb.sh
\`\`\`

---

## 📦 Criar pacote .deb

\`\`\`bash
bash criar_pacote_deb.sh
\`\`\`

---

## 🛠️ Desenvolvido por

**HCsoftware** — Herculano  
GitHub: [@${GITHUB_USER}](https://github.com/${GITHUB_USER})

---

## 📄 Licença

GPL v3 — vê [LICENSE](LICENSE) para detalhes.
README

echo -e "${GREEN}✅ README.md criado${NC}"

# ── Criar LICENSE ──────────────────────────────────────────────
if [ ! -f "LICENSE" ]; then
    echo ""
    echo "📄 A criar LICENSE (GPL v3)..."
    cat > LICENSE << 'LICENSE'
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2026 Herculano (HCsoftware)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
LICENSE
    echo -e "${GREEN}✅ LICENSE criado${NC}"
fi

# ── Criar repositório no GitHub se não existir ─────────────────
echo ""
echo "🌐 A verificar repositório no GitHub..."

if gh repo view "${GITHUB_USER}/${REPO_NOME}" &> /dev/null; then
    echo -e "${GREEN}✅ Repositório já existe${NC}"
else
    echo "🆕 A criar repositório ${REPO_NOME}..."
    gh repo create "${REPO_NOME}" \
        --public \
        --description "${DESCRICAO}" \
        --source . \
        --remote origin \
        --push 2>/dev/null || true
    echo -e "${GREEN}✅ Repositório criado${NC}"
fi

# ── Configurar remote se necessário ───────────────────────────
if ! git remote get-url origin &> /dev/null; then
    git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NOME}.git"
    echo -e "${GREEN}✅ Remote origin configurado${NC}"
fi

# ── Commit e push ──────────────────────────────────────────────
echo ""
echo "📤 A fazer commit e push..."

git add -A

# Verificar se há algo para fazer commit
if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  Nada para fazer commit (repositório já atualizado)${NC}"
else
    git commit -m "🎙️ Assistente Virtual v${VERSAO}

- Reconhecimento de voz modo walkie-talkie
- Player de música com download automático do YouTube
- Controlo de dispositivos IoT via MQTT (Tasmota)
- Controlo de porta (POWER2)
- Interface gráfica CustomTkinter com tema claro/escuro
- Pesquisa na web por voz"

    git push -u origin main 2>/dev/null || git push --force-with-lease origin main
    echo -e "${GREEN}✅ Push efetuado${NC}"
fi

# ── Criar Release com o .deb ───────────────────────────────────
echo ""
echo "🏷️  A criar release v${VERSAO} com pacote .deb..."

# Apagar release anterior com a mesma tag se existir
gh release delete "v${VERSAO}" --yes 2>/dev/null || true
git tag -d "v${VERSAO}" 2>/dev/null || true
git push origin --delete "v${VERSAO}" 2>/dev/null || true

# Criar nova release com o .deb como asset
gh release create "v${VERSAO}" \
    "$PACOTE_DEB" \
    --title "Assistente Virtual v${VERSAO}" \
    --notes "## 🎙️ Assistente Virtual v${VERSAO}

### Instalação rápida (Debian/Ubuntu)
\`\`\`bash
sudo dpkg -i assistente-virtual_${VERSAO}_all.deb
sudo apt-get install -f
\`\`\`

### ✨ Funcionalidades
- 🎤 Reconhecimento de voz (modo walkie-talkie, sem eco)
- 🎵 Player de música com download automático do YouTube
- 🏠 Controlo de dispositivos IoT via MQTT (Tasmota)
- 🚪 Abertura de porta por voz (\`abre a porta\`)
- 🌐 Pesquisa na web e YouTube por voz
- 🌙 Tema claro/escuro
- 🔊 Controlo de volume com slider

### 📋 Comandos de voz
| Categoria | Exemplos |
|-----------|---------|
| Música | \`toca o melhor de Luiz Góis\`, \`pausar\`, \`parar\` |
| Porta | \`abre a porta\`, \`abrir porta da sala\` |
| Luzes | \`liga varanda\`, \`desliga quarto 3\` |
| Web | \`pesquisa na web Python\` |
" \
    --latest

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ PUBLICAÇÃO CONCLUÍDA!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "🌐 Repositório: https://github.com/${GITHUB_USER}/${REPO_NOME}"
echo -e "📦 Release:     https://github.com/${GITHUB_USER}/${REPO_NOME}/releases/tag/v${VERSAO}"
echo -e "⬇️  Download .deb direto:"
echo -e "   https://github.com/${GITHUB_USER}/${REPO_NOME}/releases/download/v${VERSAO}/assistente-virtual_${VERSAO}_all.deb"
echo ""
