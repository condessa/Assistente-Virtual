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
