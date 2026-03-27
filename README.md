# 🎙️ Assistente Virtual

**Versão:** 1.0.0  
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

```bash
sudo dpkg -i assistente-virtual_1.0.0_all.deb
sudo apt-get install -f
```

### Opção 2 — A partir do código fonte

```bash
git clone https://github.com/condessa/Assistente-Virtual.git
cd Assistente-Virtual
bash instalar_dependencias.sh
python3 main.py
```

### Dependências de sistema

```bash
sudo apt install python3 python3-pip python3-venv portaudio19-dev python3-pyaudio ffmpeg
```

### Dependências Python

```bash
pip install customtkinter pygame yt-dlp paho-mqtt SpeechRecognition gTTS pydub pillow pyaudio
```

---

## ⚙️ Configuração MQTT

Na primeira execução é pedida a configuração MQTT. Podes também editar manualmente:

```ini
[MQTT]
host = 192.168.1.x
port = 1883
username = 
password = 
```

---

## 🎤 Comandos de voz disponíveis

| Categoria | Exemplos |
|-----------|---------|
| **Música** | `toca o melhor de Luiz Góis`, `pausar`, `continuar`, `parar` |
| **Volume** | `volume 80` |
| **Porta** | `abre a porta`, `abrir porta`, `abre porta da sala` |
| **Luzes** | `liga varanda`, `desliga quarto 3`, `acende fluorescente` |
| **Web** | `pesquisa na web Python`, `abre no youtube Luiz Góis` |
| **Utilitários** | `que horas são`, `que dia é hoje`, `ajuda` |

---

## 🏗️ Estrutura do projeto

```
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
```

---

## 📦 Criar pacote .deb

```bash
bash criar_pacote_deb.sh
```

---

## 🛠️ Desenvolvido por

**HCsoftware** — Herculano  
GitHub: [@condessa](https://github.com/condessa)

---

## 📄 Licença

GPL v3 — vê [LICENSE](LICENSE) para detalhes.
