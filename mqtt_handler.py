"""
Handler MQTT para comunicação com dispositivos IoT
"""
from __future__ import annotations

import os
import sys
import time
import json
import configparser
import threading
import re
from typing import Optional, Tuple, Set, Callable

import paho.mqtt.client as mqtt

from constants import CONFIG_FILE


# Cache de configuração
_cfg_cache: Optional[Tuple[str, int, str, str]] = None
_client: Optional[mqtt.Client] = None
_connected = False
_online_devices: Set[str] = set()
_known_devices: Set[str] = set()  # Dispositivos conhecidos (mesmo que offline)
_device_callbacks: list[Callable] = []
_discovery_in_progress = False

# Lista de nomes de dispositivos inválidos (falsos positivos)
INVALID_DEVICE_NAMES = {
    'status', 'teste', 'test', 'lwt', 'tele', 'stat', 'cmnd',
    'power', 'power1', 'power2', 'power3', 'power4',
    'sensor', 'state', 'result', 'response'
}

# Padrões de nomes inválidos (regex)
INVALID_PATTERNS = [
    r'^\d+$',  # Apenas números
    r'^test.*$',  # Começa com test
    r'^status.*$',  # Começa com status
    r'^lwt.*$',  # Começa com lwt
    r'^system.*$',  # Começa com system
    r'^broker.*$',  # Começa com broker
]


def _is_valid_device_name(name: str) -> bool:
    """
    Verifica se um nome corresponde a um dispositivo válido
    """
    name_lower = name.lower().strip()
    
    # Verificar lista de nomes inválidos
    if name_lower in INVALID_DEVICE_NAMES:
        return False
    
    # Verificar padrões inválidos
    for pattern in INVALID_PATTERNS:
        if re.match(pattern, name_lower):
            return False
    
    # Verificar se parece um tópico (tem muitos underscores)
    if name_lower.count('_') > 3:
        return False
    
    # Verificar tamanho mínimo
    if len(name_lower) < 2:
        return False
    
    # Verificar se parece um comando
    if name_lower in ['on', 'off', 'toggle', 'power']:
        return False
    
    return True


def _read_cfg() -> Tuple[str, int, str, str]:
    """Lê configuração MQTT do ficheiro config.ini"""
    global _cfg_cache
    if _cfg_cache is not None:
        return _cfg_cache
    
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    
    host = cfg.get("MQTT", "host", fallback="localhost")
    port = cfg.getint("MQTT", "port", fallback=1883)
    user = cfg.get("MQTT", "username", fallback="")
    pwd = cfg.get("MQTT", "password", fallback="")
    
    _cfg_cache = (host, port, user, pwd)
    print(f"[MQTT] Config: {host}:{port} user:{user}")
    return _cfg_cache


def _on_connect(client, userdata, flags, rc):
    """Callback quando liga ao broker"""
    global _connected
    if rc == 0:
        print("✅ Conectado ao broker MQTT")
        _connected = True
        
        # Subscrever a tópicos Tasmota
        client.subscribe("tele/+/LWT")           # Last Will and Testament
        client.subscribe("stat/+/POWER")         # Status de POWER
        client.subscribe("stat/+/POWER1")
        client.subscribe("stat/+/POWER2")
        client.subscribe("stat/+/POWER3")
        client.subscribe("stat/+/POWER4")
        client.subscribe("tele/+/STATE")         # Estado completo
        client.subscribe("tele/+/SENSOR")        # Sensores
        
        print("📡 Subscrito em tópicos Tasmota")
        
        # Lançar descoberta de dispositivos após conectar
        threading.Thread(target=_discover_devices, daemon=True).start()
        
    else:
        print(f"❌ Falha na ligação MQTT. Código: {rc}")
        _connected = False


def _on_message(client, userdata, msg):
    """Callback quando recebe mensagem MQTT"""
    global _online_devices, _known_devices
    
    topic = msg.topic
    payload = msg.payload.decode('utf-8', errors='ignore')
    
    print(f"[MQTT] {topic} -> {payload}")  # Debug
    
    # Extrair nome do dispositivo do tópico
    parts = topic.split('/')
    if len(parts) >= 2:
        device = parts[1]
        
        # Verificar se é um nome de dispositivo válido
        if not _is_valid_device_name(device):
            return
        
        # Adicionar aos conhecidos
        _known_devices.add(device)
        
        # LWT - Last Will and Testament
        if topic.endswith("/LWT"):
            if payload == "Online":
                _online_devices.add(device)
                print(f"📱 Dispositivo ONLINE (LWT): {device}")
            elif payload == "Offline":
                _online_devices.discard(device)
                print(f"📱 Dispositivo OFFLINE (LWT): {device}")
        
        # Resposta de POWER (dispositivo respondeu a um comando)
        elif "POWER" in topic:
            _online_devices.add(device)
            print(f"📱 Dispositivo respondeu: {device} = {payload}")
            
            # Detetar estado ON/OFF para atualizar a interface
            if payload in ["ON", "OFF"]:
                try:
                    # Notificar a janela de dispositivos sobre a mudança de estado
                    from devices_window import DevicesWindow
                    DevicesWindow._atualizar_estado_dispositivo(device, payload)
                except Exception as e:
                    print(f"⚠️ Erro ao notificar estado: {e}")
        
        # Estado do dispositivo
        elif topic.endswith("/STATE"):
            _online_devices.add(device)
            print(f"📊 Estado recebido de: {device}")
            
            # Tentar extrair estado POWER do JSON
            try:
                data = json.loads(payload)
                if "POWER" in data:
                    estado = data["POWER"]
                    try:
                        from devices_window import DevicesWindow
                        DevicesWindow._atualizar_estado_dispositivo(device, estado)
                    except:
                        pass
            except:
                pass
        
        # Sensor data
        elif topic.endswith("/SENSOR"):
            _online_devices.add(device)
            print(f"📊 Sensor data de: {device}")
        
        # RESULT (resposta a comandos)
        elif topic.endswith("/RESULT"):
            _online_devices.add(device)
            print(f"📊 Resultado de: {device}")
            
            # Tentar extrair estado POWER do JSON
            try:
                data = json.loads(payload)
                if "POWER" in data:
                    estado = data["POWER"]
                    try:
                        from devices_window import DevicesWindow
                        DevicesWindow._atualizar_estado_dispositivo(device, estado)
                    except:
                        pass
            except:
                pass
        
        # Qualquer outra mensagem - assume que está online
        else:
            _online_devices.add(device)
    
    # Notificar listeners sobre mudanças na lista de dispositivos
    for cb in _device_callbacks:
        try:
            cb(list(_online_devices))
        except Exception as e:
            print(f"Erro no callback: {e}")


def _discover_devices():
    """Descobre dispositivos na rede enviando comandos de broadcast"""
    global _discovery_in_progress, _online_devices, _known_devices
    
    if _discovery_in_progress:
        return
    
    _discovery_in_progress = True
    print("🔍 A descobrir dispositivos MQTT...")
    
    if not _client or not _connected:
        print("⚠️ Cliente não conectado, a tentar conectar...")
        _ensure_client()
        time.sleep(1)
    
    if _client and _connected:
        # Estratégia 1: Broadcast para todos os dispositivos Tasmota
        print("📢 Enviando broadcast para tasmotas...")
        _client.publish("cmnd/tasmotas/STATUS", "0")
        
        # Estratégia 2: Perguntar por dispositivos específicos comuns
        dispositivos_comuns = [
            "luz", "lampada", "lâmpada", "quarto", "sala", "cozinha",
            "quarto1", "quarto2", "quarto3", "quarto4",
            "ventilador", "fluorescente", "varanda", "porta", "portao",
            "tv", "televisao", "estores", "garagem"
        ]
        for device in dispositivos_comuns:
            _client.publish(f"cmnd/{device}/STATUS", "0")
        
        # Estratégia 3: Se já temos dispositivos conhecidos, perguntar por eles
        for device in _known_devices:
            if _is_valid_device_name(device):
                _client.publish(f"cmnd/{device}/STATUS", "0")
        
        # Aguardar respostas
        time.sleep(2)
        
        # Filtrar dispositivos inválidos
        _online_devices = {d for d in _online_devices if _is_valid_device_name(d)}
        _known_devices = {d for d in _known_devices if _is_valid_device_name(d)}
        
        print(f"✅ Descoberta concluída. Encontrados: {len(_online_devices)} dispositivos")
        if _online_devices:
            print(f"   Dispositivos: {', '.join(sorted(_online_devices))}")
    
    _discovery_in_progress = False


def _ensure_client() -> Tuple[Optional[mqtt.Client], bool]:
    """Garante que o cliente MQTT está ligado"""
    global _client, _connected
    
    if _client is not None and _connected:
        return _client, True

    host, port, user, pwd = _read_cfg()
    
    try:
        # Usar versão correta da API
        cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        cli.on_connect = _on_connect
        cli.on_message = _on_message
        
        if user:
            cli.username_pw_set(user, pwd)
        
        print(f"🔌 A conectar a {host}:{port}...")
        cli.connect(host, port, keepalive=60)
        cli.loop_start()
        
        # Aguarda conexão (máx 5 segundos)
        for _ in range(50):
            if cli.is_connected():
                _client, _connected = cli, True
                print("✅ Cliente MQTT pronto")
                return _client, True
            time.sleep(0.1)
        
        print("⚠️ Timeout na conexão MQTT")
        _client, _connected = cli, False
        
    except Exception as e:
        print(f"❌ Erro MQTT: {e}")
        _client, _connected = None, False
    
    return _client, _connected


def enviar_mqtt(topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
    """
    Publica uma mensagem MQTT
    Retorna True se bem sucedido
    """
    cli, ok = _ensure_client()
    if not ok or cli is None:
        print("⚠️ Cliente MQTT não disponível")
        return False
    
    try:
        print(f"📤 MQTT Enviar: {topic} -> {payload}")
        res = cli.publish(topic, payload, qos=qos, retain=retain)
        success = res.rc == mqtt.MQTT_ERR_SUCCESS
        if success:
            print("✅ Mensagem enviada")
        else:
            print(f"❌ Erro ao enviar: {res.rc}")
        return success
    except Exception as e:
        print(f"❌ Exceção ao enviar MQTT: {e}")
        return False


def disconnect():
    """Desliga o cliente MQTT"""
    global _client, _connected, _online_devices
    if _client:
        try:
            _client.loop_stop()
            _client.disconnect()
        except Exception:
            pass
    _client, _connected = None, False
    _online_devices.clear()
    print("🔌 Cliente MQTT desligado")


def listar_dispositivos_ativos() -> list[str]:
    """
    Retorna lista de dispositivos online (filtrada)
    """
    global _online_devices
    
    # Filtrar dispositivos inválidos
    _online_devices = {d for d in _online_devices if _is_valid_device_name(d)}
    
    # Se não há dispositivos, tenta descobrir
    if not _online_devices and not _discovery_in_progress:
        threading.Thread(target=_discover_devices, daemon=True).start()
        # Aguarda um pouco pela descoberta
        time.sleep(1)
    
    return sorted(list(_online_devices))


def pesquisar_dispositivos(timeout: float = 3.0) -> list[str]:
    """
    Pesquisa ativamente por dispositivos na rede
    Retorna lista de dispositivos encontrados (filtrada)
    """
    global _online_devices
    
    print("🔍 A pesquisar dispositivos...")
    _online_devices.clear()
    
    # Forçar descoberta
    _discover_devices()
    
    # Aguarda respostas
    time.sleep(timeout)
    
    # Filtrar novamente
    _online_devices = {d for d in _online_devices if _is_valid_device_name(d)}
    
    return sorted(list(_online_devices))


def subscrever_dispositivos(callback: Callable[[list[str]], None]):
    """
    Regista callback para ser chamado quando a lista de dispositivos muda
    """
    if callback not in _device_callbacks:
        _device_callbacks.append(callback)


def ensure_config_present(parent=None) -> bool:
    """
    Verifica se config.ini existe. Se não, abre janela de configuração.
    Retorna True se config existe ou foi criada.
    """
    if os.path.exists(CONFIG_FILE):
        return True
    
    # Abre janela de primeira configuração
    from config_window import solicitar_configuracao
    cfg = solicitar_configuracao(parent)
    
    if cfg and "MQTT" in cfg:
        _write_cfg(
            cfg["MQTT"].get("host", "localhost"),
            int(cfg["MQTT"].get("port", 1883)),
            cfg["MQTT"].get("username", ""),
            cfg["MQTT"].get("password", "")
        )
        return True
    
    return False


def _write_cfg(host: str, port: int, user: str, pwd: str) -> None:
    """Guarda configuração MQTT"""
    global _cfg_cache
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    cfg = configparser.ConfigParser()
    cfg["MQTT"] = {
        "host": host.strip(),
        "port": str(int(port)),
        "username": user.strip(),
        "password": pwd
    }
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)
    
    _cfg_cache = None  # Limpa cache


def abrir_config_mqtt(parent=None):
    """Abre janela de configuração MQTT"""
    from config_window import solicitar_configuracao
    cfg = solicitar_configuracao(parent)
    
    if cfg and "MQTT" in cfg:
        host = cfg["MQTT"].get("host", "localhost")
        port = int(cfg["MQTT"].get("port", 1883))
        user = cfg["MQTT"].get("username", "")
        pwd = cfg["MQTT"].get("password", "")
        
        _write_cfg(host, port, user, pwd)
        
        global _cfg_cache
        _cfg_cache = None
        disconnect()  # Força reconexão com novos dados
        
        # Tenta descobrir dispositivos após reconectar
        time.sleep(1)
        threading.Thread(target=_discover_devices, daemon=True).start()


def adicionar_dispositivo_manual(nome: str):
    """
    Adiciona um dispositivo manualmente à lista de conhecidos
    Útil para dispositivos que não enviam LWT
    """
    global _known_devices, _online_devices
    
    # Verificar se é um nome válido
    if not _is_valid_device_name(nome):
        print(f"⚠️ Nome '{nome}' parece inválido para um dispositivo")
        return False
    
    _known_devices.add(nome)
    # Tenta contactar
    enviar_mqtt(f"cmnd/{nome}/POWER", "")
    time.sleep(0.5)
    
    # Verificar se está online
    if nome in _online_devices:
        return True
    else:
        return False
