"""
Processador de comandos baseado em commands.json e dispositivos.json
"""
import json
import os
import re
import sys
import datetime
import webbrowser
from urllib.parse import quote_plus
from typing import Dict, Any

from constants import COMMANDS_FILE, CONFIG_DIR
from mqtt_handler import enviar_mqtt
from playlist_window import PlaylistWindow
from devices_window import DevicesWindow
from ollama_client import perguntar as ollama_perguntar
from tuya_client import ligar_luz_sala, desligar_luz_sala

# dispositivos.json: em desenvolvimento vive ao lado do commands.json;
# num executável (.exe) ou numa instalação só de leitura (/usr/share) vive na
# pasta de configuração do utilizador, que é sempre escrevível.
_PASTA_PROJETO = os.path.dirname(COMMANDS_FILE)
if getattr(sys, "frozen", False) or not os.access(_PASTA_PROJETO, os.W_OK):
    DEVICES_FILE = os.path.join(CONFIG_DIR, "dispositivos.json")
else:
    DEVICES_FILE = os.path.join(_PASTA_PROJETO, "dispositivos.json")

# Usado apenas se dispositivos.json ainda não existir (é criado automaticamente)
DEFAULT_DEVICES: Dict[str, str] = {
    "fluorescente": "fluorescente",
    "varanda": "fluorescente",
    "luz da varanda": "fluorescente",
    "luz varanda": "fluorescente",
    "quarto 1": "quarto1",
    "quarto casal": "quarto1",
    "luz quarto 1": "quarto1",
    "luz quarto casal": "quarto1",
    "quarto 3": "quarto3",
    "quarto tres": "quarto3",
    "quarto três": "quarto3",
    "quarto jorge": "quarto3",
    "quarto do jorge": "quarto3",
    "luz quarto do jorge": "quarto3",
    "luz quarto 3": "quarto3",
    "quarto 4": "quarto4",
    "quarto quatro": "quarto4",
    "quarto convidados": "quarto4",
    "quarto convidades": "quarto4",
    "quarto dos convidados": "quarto4",
    "luz quarto dos convidados": "quarto4",
    "luz quarto 4": "quarto4",
    "ventilador": "ventilador",
    "ventoinha": "ventilador",
    "ventuinha": "ventilador",
    "vento": "ventilador",
    "porta": "porta",
    "porta da sala": "porta",
    "rua" : "rua",
    "luz da rua" : "rua",
    "cozinha" : "cozinha",
    "luz da cozinha" : "cozinha",
}

# Padrões aceites como nome de dispositivo, além das chaves de dispositivos.json
_PADROES_DISPOSITIVO = re.compile(r'quarto\s*\d|luz\s*\w+|fluorescente|varanda|ventilador|rua')

_PREFIXOS_LIGAR = ("ligar ", "liga ", "acender ", "acende ", "acenda ")
_PREFIXOS_DESLIGAR = ("desligar ", "desliga ", "apagar ", "apaga ", "apague ")
_PREFIXOS_ALTERNAR = ("alternar ", "toggle ", "inverter ",
                      "muda o estado de ", "muda o estado da ", "mudar estado ")


class CommandProcessor:
    """Processa comandos de texto usando commands.json e dispositivos.json"""

    def __init__(self, music_player, gui=None):
        self.music_player = music_player
        self.gui = gui
        self.commands = self._load_commands()

        # mapeamento_dispositivos: "o que dizes" -> "tópico MQTT real"
        self.mapeamento_dispositivos = self._load_devices()

        self.palavras_proibidas = [
            'para', 'ana', 'militar', 'grande', 'pequeno', 'amigo',
            'telefone', 'chamar', 'contacto', 'mensagem', 'sms'
        ]

    def _load_commands(self) -> Dict[str, Any]:
        try:
            with open(COMMANDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Não foi possível carregar commands.json: {e}")
            return {"musica": {}, "web": {}, "dispositivos": {}, "utilitarios": {}}

    def _load_devices(self) -> Dict[str, str]:
        """Carrega dispositivos.json; cria-o com os valores por omissão se não existir."""
        try:
            with open(DEVICES_FILE, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, dict) and dados:
                    print(f"[INFO] {len(dados)} dispositivo(s) carregado(s) de dispositivos.json")
                    return dados
                print("[AVISO] dispositivos.json vazio ou inválido, a usar valores por omissão")
                return dict(DEFAULT_DEVICES)
        except FileNotFoundError:
            print(f"[INFO] dispositivos.json não encontrado, a criar em: {DEVICES_FILE}")
            try:
                with open(DEVICES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(DEFAULT_DEVICES, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERRO] Não foi possível criar dispositivos.json: {e}")
            return dict(DEFAULT_DEVICES)
        except Exception as e:
            print(f"[ERRO] Não foi possível carregar dispositivos.json: {e}")
            return dict(DEFAULT_DEVICES)

    def _is_dispositivo_valido(self, texto: str) -> bool:
        texto_lower = texto.lower().strip()
        for palavra in self.palavras_proibidas:
            if palavra in texto_lower:
                return False
        if len(texto_lower.split()) > 4:
            return False
        if any(dispositivo in texto_lower for dispositivo in self.mapeamento_dispositivos):
            return True
        return bool(_PADROES_DISPOSITIVO.search(texto_lower))

    def process(self, comando: str) -> str:
        if not comando:
            return "Diz-me o que queres fazer. 😉"

        comando_original = comando
        comando_lower = comando.lower().strip().rstrip("?!.")
        print(f"[DEBUG] A processar: '{comando_lower}'")

        # URL do YouTube enviada directamente
        if comando_lower.startswith("http://") or comando_lower.startswith("https://"):
            url = comando.strip()
            self.music_player.tocar_url(url)
            return f"🔗 A carregar: {url[:60]}{'...' if len(url) > 60 else ''}"

        # Horas
        if re.search(r"\bhora[s]?\b", comando_lower):
            agora = datetime.datetime.now()
            h, m = agora.hour, agora.minute
            if m == 0:
                texto_hora = f"{h} horas"
            elif m == 1:
                texto_hora = f"{h} horas e um minuto"
            else:
                texto_hora = f"{h} horas e {m} minutos"
            return f"🕒 Agora são {texto_hora}."

        # Data
        if re.search(r"\b(dia|data)\b", comando_lower):
            hoje = datetime.datetime.now()
            dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                    "sexta-feira", "sábado", "domingo"]
            meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                     "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
            dia_semana = dias[hoje.weekday()]
            texto_data = f"{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}"
            return f"📅 Hoje é {dia_semana}, {texto_data}."

        # Música — tocar
        for _prefix in ["tocar ", "toca "]:
            if comando_lower.startswith(_prefix):
                musica = comando[len(_prefix):].strip()
                if musica:
                    self.music_player.tocar_musica(musica)
                    return f"🔍 A verificar playlist para: {musica}"
                else:
                    return "⚠️ Indica o nome da música a tocar."

        if comando_lower in ["pausa", "pausar"]:
            resultado = self.music_player.pausar_musica()
            return resultado if resultado else "⏸️ Música pausada."

        if comando_lower in ["continua", "continuar", "retomar", "resumir"]:
            resultado = self.music_player.resumir_musica()
            return resultado if resultado else "▶️ Música retomada."

        if comando_lower in ["para", "parar", "stop"]:
            resultado = self.music_player.parar_musica()
            return resultado if resultado else "⏹️ Música parada."

        if comando_lower in ["limpar playlist", "limpa a playlist", "limpa playlist"]:
            resultado = self.music_player.limpar_playlist()
            return resultado if resultado else "🧹 Playlist limpa."

        if comando_lower in ["mostrar playlist", "ver playlist", "abrir playlist", "ver musicas", "ver músicas"]:
            if self.music_player:
                PlaylistWindow.mostrar_playlist(self.music_player, self.gui)
                return "📜 Playlist aberta."
            else:
                return "❌ Player de música não disponível."

        # Volume
        match = re.search(r"^volume\s+(\d{1,3})$", comando_lower)
        if match:
            nivel = int(match.group(1))
            resultado = self.music_player.controlar_volume(nivel)
            return resultado if resultado else f"🔊 Volume ajustado para {nivel}%."

        # Web — YouTube
        for _prefix in ["abre no youtube ", "abrir no youtube ", "youtube "]:
            if comando_lower.startswith(_prefix):
                termo = comando[len(_prefix):].strip()
                if termo:
                    url = f"https://www.youtube.com/results?search_query={quote_plus(termo)}"
                    webbrowser.open(url, new=2)
                    return f"▶️ A abrir YouTube: {termo}"
                else:
                    return "⚠️ Diz-me o que queres ver no YouTube."

        # Web — pesquisa
        for _prefix in ["pesquisa na web ", "pesquisar na web ", "pesquisa por ", "google "]:
            if comando_lower.startswith(_prefix):
                termo = comando[len(_prefix):].strip()
                if termo:
                    url = f"https://www.google.com/search?q={quote_plus(termo)}"
                    webbrowser.open(url, new=2)
                    return f"🌐 A pesquisar: {termo}"
                else:
                    return "⚠️ Diz-me o que queres pesquisar."

        # Listar dispositivos
        if comando_lower in ["pesquisar dispositivos", "listar dispositivos",
                             "ver dispositivos", "dispositivos ativos", "dispositivos"]:
            if self.gui:
                self.gui.after(0, self.gui.mostrar_dispositivos)
                return "📱 A abrir janela de dispositivos."
            else:
                return "❌ Interface não disponível."

        # Porta
        if comando_lower in ["abrir porta", "abre porta", "abre a porta", "abrir a porta",
                              "abre porta da sala", "abrir porta da sala", "abre a porta da sala"]:
            return self._abrir_porta()

        # Luz da sala (Tuya)
        if comando_lower in ["ligar luz da sala", "liga luz da sala", "liga a luz da sala",
                              "acender luz da sala", "acende a luz da sala", "liga sala", "ligar sala"]:
            sucesso = ligar_luz_sala()
            return "💡 Luz da sala ligada." if sucesso else "❌ Erro ao ligar a luz da sala."

        if comando_lower in ["desligar luz da sala", "desliga luz da sala", "desliga a luz da sala",
                              "apagar luz da sala", "apaga a luz da sala", "desliga sala", "desligar sala"]:
            sucesso = desligar_luz_sala()
            return "💡 Luz da sala desligada." if sucesso else "❌ Erro ao desligar a luz da sala."

        # ── LIGAR / DESLIGAR / ALTERNAR ──────────────────────────────────────
        for prefixos, acao, verbo in (
            (_PREFIXOS_LIGAR, self._ligar_dispositivo, "ligar"),
            (_PREFIXOS_DESLIGAR, self._desligar_dispositivo, "desligar"),
            (_PREFIXOS_ALTERNAR, self._alternar_dispositivo, "alternar"),
        ):
            prefix = next((p for p in prefixos if comando_lower.startswith(p)), None)
            if prefix is None:
                continue
            dispositivo = comando[len(prefix):].strip()
            if not dispositivo:
                return f"⚠️ Indica o dispositivo a {verbo}."
            if not self._is_dispositivo_valido(dispositivo):
                return f"Desculpa, não entendi: '{comando_original}'"
            return acao(dispositivo)

        # Comando só com nome do dispositivo
        palavras = comando_lower.split()
        if len(palavras) == 1 and palavras[0] not in ['ajuda', 'help']:
            if self._is_dispositivo_valido(palavras[0]):
                return self._ligar_dispositivo(palavras[0])

        # Ajuda
        if comando_lower in ["ajuda", "help", "comandos"]:
            if self.gui:
                self.gui.mostrar_ajuda()
                return "📚 Janela de ajuda aberta."
            else:
                return "📚 Janela de ajuda aberta."

        # Fallback — nenhum comando reconhecido: tenta o Ollama (LLM local)
        return ollama_perguntar(comando_original)

    # ── Métodos de dispositivos ───────────────────────────────────────────────

    def _resolver_dispositivo(self, dispositivo: str) -> str:
        """Resolve o nome do dispositivo para o tópico MQTT, usando dispositivos.json"""
        dispositivo_mqtt = self.mapeamento_dispositivos.get(dispositivo)
        if dispositivo_mqtt:
            return dispositivo_mqtt
        for chave, valor in self.mapeamento_dispositivos.items():
            if chave in dispositivo:
                print(f"[DEBUG] Correspondência parcial: '{dispositivo}' -> '{valor}'")
                return valor
        return dispositivo.replace(' ', '_')

    def _topico_mqtt(self, dispositivo_mqtt: str) -> str:
        if dispositivo_mqtt in ["porta", "portao"]:
            return "cmnd/porta/POWER2"
        return f"cmnd/{dispositivo_mqtt}/POWER"

    def _emoji_dispositivo(self, dispositivo: str) -> str:
        if any(p in dispositivo for p in ['luz', 'fluorescente', 'varanda']):
            return "💡"
        elif any(p in dispositivo for p in ['ventilador', 'vento']):
            return "🌀"
        return "🔌"

    def _abrir_porta(self) -> str:
        topico = self._topico_mqtt("porta")
        print(f"[DEBUG] MQTT: {topico} -> ON")
        sucesso = enviar_mqtt(topico, "ON")
        if sucesso:
            return "🚪 A porta foi aberta."
        else:
            return "❌ Erro ao abrir a porta. Verifica a configuração MQTT."

    def _enviar_estado(self, dispositivo: str, payload: str, verbo: str,
                       participio: str, prefixo_ok: str = "") -> str:
        """Publica ON/OFF/TOGGLE no tópico do dispositivo, evitando reenviar o estado actual."""
        dispositivo = dispositivo.lower().strip()
        dispositivo_mqtt = self._resolver_dispositivo(dispositivo)
        topico = self._topico_mqtt(dispositivo_mqtt)
        emoji = self._emoji_dispositivo(dispositivo)

        if payload in ("ON", "OFF") and DevicesWindow._device_states.get(dispositivo_mqtt) == payload:
            return f"{emoji} {dispositivo} já está {participio}."

        print(f"[DEBUG] MQTT: {topico} -> {payload}")
        if enviar_mqtt(topico, payload):
            return f"{prefixo_ok}{emoji} {dispositivo} {participio}."
        return f"❌ Erro ao {verbo} {dispositivo}. Verifica a configuração MQTT."

    def _ligar_dispositivo(self, dispositivo: str) -> str:
        return self._enviar_estado(dispositivo, "ON", "ligar", "ligado")

    def _desligar_dispositivo(self, dispositivo: str) -> str:
        return self._enviar_estado(dispositivo, "OFF", "desligar", "desligado")

    def _alternar_dispositivo(self, dispositivo: str) -> str:
        """Alterna (TOGGLE) o estado de um dispositivo"""
        return self._enviar_estado(dispositivo, "TOGGLE", "alternar", "alternado", prefixo_ok="🔄 ")
