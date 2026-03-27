"""
Processador de comandos baseado em commands.json
"""
import json
import re
import datetime
import webbrowser
from urllib.parse import quote_plus
from typing import Dict, Any, Optional, Callable

from constants import COMMANDS_FILE
from mqtt_handler import enviar_mqtt
from playlist_window import PlaylistWindow


class CommandProcessor:
    """Processa comandos de texto usando o ficheiro commands.json"""
    
    def __init__(self, music_player, gui=None):
        self.music_player = music_player
        self.gui = gui
        self.commands = self._load_commands()
        self.handlers = self._register_handlers()
        
        # Lista de dispositivos conhecidos (para validação)
        self.dispositivos_conhecidos = [
            'fluorescente', 'varanda', 'quarto1', 'quarto3', 'quarto4',
            'quarto 1', 'quarto 3', 'quarto 4', 'ventilador',
            'quarto casal', 'quarto jorge', 'quarto convidados',
            'porta', 'porta da sala'
        ]
        
        # Palavras que NÃO devem ser interpretadas como dispositivos
        self.palavras_proibidas = [
            'para', 'ana', 'militar', 'grande', 'pequeno', 'amigo',
            'telefone', 'chamar', 'contacto', 'mensagem', 'sms'
        ]
    
    def _load_commands(self) -> Dict[str, Any]:
        """Carrega os comandos do ficheiro JSON"""
        try:
            with open(COMMANDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Não foi possível carregar commands.json: {e}")
            return {"musica": {}, "web": {}, "dispositivos": {}, "utilitarios": {}}
    
    def _register_handlers(self) -> Dict[str, Callable]:
        """Regista as funções que executam cada tipo de comando"""
        return {
            "musica": self._handle_music_command,
            "web": self._handle_web_command,
            "dispositivos": self._handle_device_command,
            "utilitarios": self._handle_utility_command
        }
    
    def _is_dispositivo_valido(self, texto: str) -> bool:
        """
        Verifica se o texto corresponde a um dispositivo válido
        """
        texto_lower = texto.lower().strip()
        
        # Verificar palavras proibidas
        for palavra in self.palavras_proibidas:
            if palavra in texto_lower:
                return False
        
        # Verificar se é muito longo (provavelmente é uma frase)
        if len(texto_lower.split()) > 4:
            return False
        
        # Verificar se corresponde a algum dispositivo conhecido
        for dispositivo in self.dispositivos_conhecidos:
            if dispositivo in texto_lower:
                return True
        
        # Verificar padrões comuns de dispositivos
        padroes_validos = [
            r'quarto\s*\d',
            r'luz\s*\w+',
            r'fluorescente',
            r'varanda',
            r'ventilador',
        ]
        
        for padrao in padroes_validos:
            if re.search(padrao, texto_lower):
                return True
        
        return False
    
    def process(self, comando: str) -> str:
        """Processa um comando de texto e retorna a resposta"""
        if not comando:
            return "Diz-me o que queres fazer. 😉"
        
        comando_original = comando
        comando_lower = comando.lower().strip()
        
        print(f"[DEBUG] A processar: '{comando_lower}'")
        
        # Comandos específicos primeiro
        if comando_lower in ["que horas são", "horas"]:
            agora = datetime.datetime.now().strftime("%H:%M")
            return f"🕒 Agora são {agora}."
        
        if comando_lower in ["que dia é hoje", "data"]:
            hoje = datetime.datetime.now()
            dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", 
                    "sexta-feira", "sábado", "domingo"]
            dia_semana = dias[hoje.weekday()]
            data = hoje.strftime("%d/%m/%Y")
            return f"📅 Hoje é {dia_semana}, {data}."
        
        # Comandos de música
        if comando_lower.startswith("tocar ") or comando_lower.startswith("toca "):
            if comando_lower.startswith("tocar "):
                musica = comando[6:].strip()
            else:
                musica = comando[5:].strip()
            
            if musica:
                self.music_player.tocar_musica(musica)
                return f"🎵 A tocar: {musica}"
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
        
        if comando_lower in ["limpar playlist", "limpa a playlist"]:
            resultado = self.music_player.limpar_playlist()
            return resultado if resultado else "🧹 Playlist limpa."
        
        if comando_lower in ["mostrar playlist", "ver playlist"]:
            if self.music_player:
                PlaylistWindow.mostrar_playlist(self.music_player, self.gui)
                return "📜 Playlist aberta."
            else:
                return "❌ Player de música não disponível."
        
        # Volume
        match = re.search(r'^volume\s+(\d{1,3})$', comando_lower)
        if match:
            nivel = int(match.group(1))
            resultado = self.music_player.controlar_volume(nivel)
            return resultado if resultado else f"🔊 Volume ajustado para {nivel}%."
        
        # Web
        if comando_lower.startswith("abre no youtube "):
            termo = comando[16:].strip()
            if termo:
                url = f"https://www.youtube.com/results?search_query={quote_plus(termo)}"
                webbrowser.open(url, new=2)
                return f"▶️ A abrir YouTube: {termo}"
            else:
                return "⚠️ Diz-me o que queres ver no YouTube."
        
        if comando_lower.startswith("pesquisa na web "):
            termo = comando[16:].strip()
            if termo:
                url = f"https://www.google.com/search?q={quote_plus(termo)}"
                webbrowser.open(url, new=2)
                return f"🌐 A pesquisar: {termo}"
            else:
                return "⚠️ Diz-me o que queres pesquisar."
        
        # Comandos de porta — padrão especial (só envia POWER2 ON)
        padroes_porta = [
            'abrir porta da rua', 'abrir a porta da rua', 'abre a porta da rua',
            'abrir porta da sala', 'abrir a porta da sala', 'abre porta da sala',
        ]
        if comando_lower in padroes_porta:
            return self._abrir_porta()

        # Comandos de dispositivos - VERSÃO COM VALIDAÇÃO
        # Verificar comandos de ligar
        if (comando_lower.startswith("ligar ") or 
            comando_lower.startswith("liga ") or
            comando_lower.startswith("acender ") or
            comando_lower.startswith("acende ") or
            comando_lower.startswith("acenda ")):
            
            # Extrair o dispositivo
            if comando_lower.startswith("ligar "):
                dispositivo = comando[6:].strip()
            elif comando_lower.startswith("liga "):
                dispositivo = comando[5:].strip()
            elif comando_lower.startswith("acender "):
                dispositivo = comando[8:].strip()
            elif comando_lower.startswith("acende "):
                dispositivo = comando[7:].strip()
            elif comando_lower.startswith("acenda "):
                dispositivo = comando[7:].strip()
            else:
                dispositivo = ""
            
            if dispositivo:
                # VALIDAÇÃO: verificar se é um dispositivo válido
                if self._is_dispositivo_valido(dispositivo):
                    return self._ligar_dispositivo(dispositivo)
                else:
                    # Não é um dispositivo reconhecido, tratar como comando não entendido
                    return f"Desculpa, não entendi: '{comando_original}'"
            else:
                return "⚠️ Indica o dispositivo a ligar."
        
        # Verificar comandos de desligar
        if (comando_lower.startswith("desligar ") or
            comando_lower.startswith("desliga ") or
            comando_lower.startswith("apagar ") or
            comando_lower.startswith("apaga ") or
            comando_lower.startswith("apague ")):
            
            # Extrair o dispositivo
            if comando_lower.startswith("desligar "):
                dispositivo = comando[9:].strip()
            elif comando_lower.startswith("desliga "):
                dispositivo = comando[8:].strip()
            elif comando_lower.startswith("apagar "):
                dispositivo = comando[7:].strip()
            elif comando_lower.startswith("apaga "):
                dispositivo = comando[6:].strip()
            elif comando_lower.startswith("apague "):
                dispositivo = comando[7:].strip()
            else:
                dispositivo = ""
            
            if dispositivo:
                # VALIDAÇÃO: verificar se é um dispositivo válido
                if self._is_dispositivo_valido(dispositivo):
                    return self._desligar_dispositivo(dispositivo)
                else:
                    # Não é um dispositivo reconhecido, tratar como comando não entendido
                    return f"Desculpa, não entendi: '{comando_original}'"
            else:
                return "⚠️ Indica o dispositivo a desligar."
        
        # Comando só com nome do dispositivo (apenas se for dispositivo válido)
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
                return "📚 Comandos disponíveis: música, web, dispositivos, utilitários"
        
        return f"Desculpa, não entendi: '{comando_original}'"
    
    def _abrir_porta(self) -> str:
        """Abre a porta enviando POWER2 ON (o Tasmota faz o reset automático)"""
        topico = "cmnd/porta/POWER2"
        print(f"[DEBUG] MQTT: {topico} -> ON")
        sucesso = enviar_mqtt(topico, "ON")
        if sucesso:
            return "🚪 A abrir a porta."
        else:
            return "❌ Erro ao abrir a porta. Verifica a configuração MQTT."

    def _ligar_dispositivo(self, dispositivo: str) -> str:
        """Liga um dispositivo"""
        dispositivo = dispositivo.lower().strip()
        
        # MAPEAMENTO UNIFICADO para ligar
        mapeamento = {
            # Fluorescente / Varanda
            'fluorescente': 'fluorescente',
            'varanda': 'fluorescente',
            'luz da varanda': 'fluorescente',
            'luz varanda': 'fluorescente',
            
            # Quarto 1
            'quarto 1': 'quarto1',
            'quarto casal' : 'quarto1',
            'luz quarto 1' : 'quarto1',
            'luz quarto casal' : 'quarto1',
            
            # Quarto 3
            'quarto 3': 'quarto3',
            'quarto tres': 'quarto3',
            'quarto três': 'quarto3',
            'quarto jorge': 'quarto3',
            'quarto do jorge': 'quarto3',
            'luz quarto 3': 'quarto3',
            
            # Quarto 4
            'quarto 4': 'quarto4',
            'quarto quatro': 'quarto4',
            'quarto convidados': 'quarto4',
            'quarto convidades': 'quarto4',
            'quarto dos convidados': 'quarto4',
            'luz quarto 4': 'quarto4',
            
            # Ventilador
            'ventilador': 'ventilador',
            'ventoinha': 'ventilador',
            'ventuinha': 'ventilador',
            'vento': 'ventilador',
        }
        
        # Procurar no mapeamento
        dispositivo_mqtt = mapeamento.get(dispositivo)
        
        # Se não encontrar, tentar correspondência parcial
        if not dispositivo_mqtt:
            for chave, valor in mapeamento.items():
                if chave in dispositivo:
                    dispositivo_mqtt = valor
                    print(f"[DEBUG] Correspondência parcial: '{dispositivo}' -> '{valor}'")
                    break
        
        # Se ainda não encontrou, usar o nome original com underscores
        if not dispositivo_mqtt:
            dispositivo_mqtt = dispositivo.replace(' ', '_')
        
        # Casos especiais
        if dispositivo_mqtt in ["porta", "portao"]:
            topico = f"cmnd/porta/POWER2"
        else:
            topico = f"cmnd/{dispositivo_mqtt}/POWER"
        
        print(f"[DEBUG] MQTT: {topico} -> ON")
        sucesso = enviar_mqtt(topico, "ON")
        
        if sucesso:
            # Escolher emoji apropriado
            if any(palavra in dispositivo for palavra in ['luz', 'fluorescente', 'varanda']):
                return f"💡 A ligar {dispositivo}."
            elif any(palavra in dispositivo for palavra in ['ventilador', 'vento']):
                return f"🌀 A ligar {dispositivo}."
            else:
                return f"🔌 A ligar {dispositivo}."
        else:
            return f"❌ Erro ao ligar {dispositivo}. Verifica a configuração MQTT."
    
    def _desligar_dispositivo(self, dispositivo: str) -> str:
        """Desliga um dispositivo"""
        dispositivo = dispositivo.lower().strip()
        
        # MAPEAMENTO UNIFICADO para desligar (IGUAL ao de ligar)
        mapeamento = {
            # Fluorescente / Varanda
            'fluorescente': 'fluorescente',
            'varanda': 'fluorescente',
            'luz da varanda': 'fluorescente',
            'luz varanda': 'fluorescente',
            
             # Quarto 1
            'quarto 1': 'quarto1',
            'quarto casal' : 'quarto1',
            'luz quarto 1' : 'quarto1',
            'luz quarto casal' : 'quarto1',
            
            # Quarto 3
            'quarto 3': 'quarto3',
            'quarto tres': 'quarto3',
            'quarto três': 'quarto3',
            'quarto jorge': 'quarto3',
            'quarto do jorge': 'quarto3',
            'luz quarto 3': 'quarto3',
            
            # Quarto 4
            'quarto 4': 'quarto4',
            'quarto quatro': 'quarto4',
            'quarto convidados': 'quarto4',
            'quarto convidades': 'quarto4',
            'quarto dos convidados': 'quarto4',
            'luz quarto 4': 'quarto4',
            
            # Ventilador
            'ventilador': 'ventilador',
            'ventoinha': 'ventilador',
            'ventuinha': 'ventilador',
            'vento': 'ventilador',
        }
        
        # Procurar no mapeamento
        dispositivo_mqtt = mapeamento.get(dispositivo)
        
        # Se não encontrar, tentar correspondência parcial
        if not dispositivo_mqtt:
            for chave, valor in mapeamento.items():
                if chave in dispositivo:
                    dispositivo_mqtt = valor
                    print(f"[DEBUG] Correspondência parcial: '{dispositivo}' -> '{valor}'")
                    break
        
        # Se ainda não encontrou, usar o nome original com underscores
        if not dispositivo_mqtt:
            dispositivo_mqtt = dispositivo.replace(' ', '_')
        
        # Casos especiais
        if dispositivo_mqtt in ["porta", "portao"]:
            topico = f"cmnd/porta/POWER2"
        else:
            topico = f"cmnd/{dispositivo_mqtt}/POWER"
        
        print(f"[DEBUG] MQTT: {topico} -> OFF")
        sucesso = enviar_mqtt(topico, "OFF")
        
        if sucesso:
            # Escolher emoji apropriado
            if any(palavra in dispositivo for palavra in ['luz', 'fluorescente', 'varanda']):
                return f"💡 A desligar {dispositivo}."
            elif any(palavra in dispositivo for palavra in ['ventilador', 'vento']):
                return f"🌀 A desligar {dispositivo}."
            else:
                return f"🔌 A desligar {dispositivo}."
        else:
            return f"❌ Erro ao desligar {dispositivo}. Verifica a configuração MQTT."
    
    def _handle_music_command(self, acao: str, config: dict, parametro: Optional[str]) -> str:
        """Handler para comandos de música (usado pelo sistema JSON)"""
        return "❌ Comando de música não disponível."
    
    def _handle_web_command(self, acao: str, config: dict, parametro: Optional[str]) -> str:
        """Handler para comandos web"""
        return "❌ Comando web não disponível."
    
    def _handle_device_command(self, acao: str, config: dict, parametro: Optional[str]) -> str:
        """Handler para comandos de dispositivos"""
        return "❌ Comando de dispositivo não disponível."
    
    def _handle_utility_command(self, acao: str, config: dict, parametro: Optional[str]) -> str:
        """Handler para comandos utilitários"""
        return "❌ Comando utilitário não disponível."
