#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Publicar Assistente Virtual v2.0.0 no GitHub
# HCsoftware — Herculano
# ═══════════════════════════════════════════════════════════════

set -e

VERSAO="2.0.0"
DIR="$HOME/Programas/Assistente Virtual"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════"
echo "  🎙️  Assistente Virtual — Publicar v${VERSAO}"
echo "═══════════════════════════════════════════════"
echo ""

cd "$DIR"

# ── Verificar git ────────────────────────────────────────────────
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Não é um repositório git${NC}"
    exit 1
fi

# ── Verificar autenticação GitHub ────────────────────────────────
if ! gh auth status &>/dev/null; then
    echo -e "${RED}❌ Não autenticado no GitHub. Corre: gh auth login${NC}"
    exit 1
fi

# ── Ficheiros a excluir do commit ────────────────────────────────
echo "🧹 A verificar .gitignore..."
cat > .gitignore << 'GITIGNORE'
venv/
__pycache__/
*.pyc
*.pyo
config.ini
Download/
*.log
.DS_Store
*.bak
guiCerto.py
guiMulti.py
gui_v2.py
gui1.py
guiWin.py
music_playerOriginal.py
music_playerWin.py
playlist_windowOriginal.py
ffmpeg/
GITIGNORE
echo -e "${GREEN}✅ .gitignore actualizado${NC}"

# ── Actualizar README ────────────────────────────────────────────
echo ""
echo "📝 A actualizar README.md..."
cat > README.md << 'README'
# 🎙️ Assistente Virtual HCsoftware

**v2.0.0** — Interface redesenhada com estilo profissional

---

## ✨ Novidades v2.0.0

- 🎨 **Interface redesenhada** — sidebar escura + cabeçalho laranja, inspirada no AluminioManager
- 🌗 **Tema claro/escuro** — alternância completa com re-coloração de todos os widgets
- 🖼️ **Branding visual** — logótipo chatbot.png + "by HCsoftware" na sidebar
- 📐 **Janelas centralizadas** — principal e todas as auxiliares
- 🔤 **Fontes optimizadas** — reduzidas nas janelas Playlist, Dispositivos e Ajuda
- 🚪 **Botão Enviar** laranja no painel de entrada
- 💡 **Tooltips** em todos os botões

---

## ✨ Funcionalidades

- 🎤 **Reconhecimento de voz** — modo walkie-talkie, sem eco
- 🎵 **Player de música** — pesquisa e descarrega do YouTube automaticamente
- ✂️ **Extrator de faixas** — extrai faixas individuais de álbuns via ffmpeg
- 🏠 **Controlo IoT** — liga/desliga dispositivos Tasmota via MQTT
- 🚪 **Controlo de porta** — abre a porta com comando de voz
- 🌐 **Pesquisa na web** — Google e YouTube directamente por voz
- 🕒 **Utilitários** — horas, data, ajuda
- 🔊 **Volume ajustável** — slider com valor em percentagem
- 📊 **Progresso da música** — slider de seek em tempo real

---

## 📥 Instalação (Debian/Ubuntu)

```bash
git clone https://github.com/condessa/Assistente-Virtual.git
cd Assistente-Virtual
bash instalar_dependencias.sh
python3 main.py
```

### Dependências de sistema

```bash
sudo apt install python3 python3-pip python3-venv \
    portaudio19-dev python3-pyaudio ffmpeg
```

### Dependências Python

```bash
pip install customtkinter pygame yt-dlp paho-mqtt \
    SpeechRecognition gTTS pydub pillow pyaudio mutagen
```

---

## ⚙️ Configuração MQTT

Na primeira execução é pedida a configuração MQTT. Podes também editar:

```
~/.config/assistente-virtual/config.ini
```

---

## 🎤 Comandos de voz disponíveis

| Categoria | Exemplos |
|-----------|---------|
| **Música** | `toca o melhor de Luiz Góis`, `pausar`, `continuar`, `parar` |
| **Volume** | `volume 80` |
| **Porta** | `abre a porta` |
| **Luzes** | `liga varanda`, `desliga quarto 3` |
| **Web** | `pesquisa na web Python`, `abre no youtube Luiz Góis` |
| **Utilitários** | `que horas são`, `que dia é hoje`, `ajuda` |

---

## 🏗️ Estrutura do projecto

```
Assistente Virtual/
├── main.py                 # Ponto de entrada
├── gui.py                  # Interface gráfica (CustomTkinter) — v2.0
├── command_processor.py    # Motor de comandos
├── music_player.py         # Player + download YouTube
├── playlist_window.py      # Janela de playlist
├── devices_window.py       # Janela de dispositivos MQTT
├── help_window.py          # Janela de ajuda
├── mqtt_handler.py         # Comunicação MQTT
├── voice.py                # Reconhecimento de voz
├── tts.py                  # Text-to-Speech (gTTS)
├── extrator_faixas.py      # Extractor de faixas de álbuns
├── commands.json           # Definição de comandos
├── constants.py            # Paths e constantes
├── tooltip.py              # Tooltips personalizados
└── instalar_dependencias.sh
```

---

## 🛠️ Desenvolvido por

**HCsoftware** — Herculano  
GitHub: [@condessa](https://github.com/condessa)

---

## 📄 Licença

GPL v3 — vê [LICENSE](LICENSE) para detalhes.
README
echo -e "${GREEN}✅ README.md actualizado${NC}"

# ── Commit e push ────────────────────────────────────────────────
echo ""
echo "📦 A preparar commit v${VERSAO}..."

git add -A

# Verificar se há alterações
if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  Sem alterações para fazer commit${NC}"
else
    git commit -m "🎨 Assistente Virtual v${VERSAO} — Interface redesenhada

✨ Novidades:
- Interface redesenhada: sidebar escura + cabeçalho laranja (estilo AluminioManager)
- Tema claro/escuro funcional com re-coloração completa de todos os widgets
- Logótipo chatbot.png + branding 'by HCsoftware' na sidebar
- Janelas principal e auxiliares sempre centradas no ecrã
- Fontes optimizadas nas janelas Playlist, Dispositivos e Ajuda
- Botão Enviar laranja no painel de entrada
- Tooltips em todos os botões
- Botão Sair discreto na secção INTERAÇÃO da sidebar"

    echo -e "${GREEN}✅ Commit criado${NC}"
fi

# ── Push ─────────────────────────────────────────────────────────
echo ""
echo "⬆️  A fazer push para GitHub..."

GITHUB_TOKEN=$(gh auth token 2>/dev/null)
if [ -n "$GITHUB_TOKEN" ]; then
    git remote set-url origin "https://${GITHUB_TOKEN}@github.com/condessa/Assistente-Virtual.git"
fi

git push origin main
echo -e "${GREEN}✅ Push efectuado${NC}"

# ── Criar tag v2.0.0 ─────────────────────────────────────────────
echo ""
echo "🏷️  A criar tag v${VERSAO}..."

git tag -d "v${VERSAO}" 2>/dev/null || true
git tag -a "v${VERSAO}" -m "🎙️ Assistente Virtual v${VERSAO} — Interface redesenhada"
git push origin "v${VERSAO}" --force
echo -e "${GREEN}✅ Tag v${VERSAO} publicada${NC}"

# ── Criar Release no GitHub ──────────────────────────────────────
echo ""
echo "🚀 A criar Release no GitHub..."

gh release delete "v${VERSAO}" --yes 2>/dev/null || true

gh release create "v${VERSAO}" \
    --title "🎙️ Assistente Virtual v${VERSAO}" \
    --notes "## 🎨 Interface redesenhada — v${VERSAO}

### ✨ Novidades
- Interface com sidebar escura + cabeçalho laranja (estilo AluminioManager)
- Tema claro/escuro funcional com re-coloração completa
- Logótipo chatbot.png + branding na sidebar
- Janelas sempre centradas no ecrã
- Fontes optimizadas em todas as janelas auxiliares
- Botão Enviar em destaque laranja
- Tooltips em todos os controlos

### 📥 Instalação
\`\`\`bash
git clone https://github.com/condessa/Assistente-Virtual.git
cd Assistente-Virtual
bash instalar_dependencias.sh
python3 main.py
\`\`\`"

echo -e "${GREEN}✅ Release v${VERSAO} publicada${NC}"

# ── Restaurar URL sem token ──────────────────────────────────────
git remote set-url origin "https://github.com/condessa/Assistente-Virtual.git"

echo ""
echo "═══════════════════════════════════════════════"
echo -e "${GREEN}  ✅ v${VERSAO} publicada com sucesso!${NC}"
echo "  🔗 https://github.com/condessa/Assistente-Virtual"
echo "═══════════════════════════════════════════════"
echo ""
