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
_device_last_seen: dict = {}     # device -> timestamp da última mensagem em tempo real
_esphome_online: set = set()     # dispositivos ESPHome confirmados online via /status
DEVICE_TIMEOUT_SECONDS = 86400   # 24h — OpenBK só publica connected uma vez
_device_callbacks: list[Callable] = []
_discovery_in_progress = False
_esphome_command_topics: dict = {}  # device -> command_topic (descoberto via +/switch/+/state)

_PAYLOAD_ONLINE = ("online", "true", "1")
_PAYLOAD_OFFLINE = ("offline", "false", "0")

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
    if name_lower.count('_') > 5:
        return False
    
    # Verificar tamanho mínimo
    if len(name_lower) < 2:
        return False
    
    # Verificar se parece um comando
    if name_lower in ['on', 'off', 'toggle', 'power']:
        return False
    
    return True


def _marcar_online(device: str):
    _online_devices.add(device)
    _device_last_seen[device] = time.time()


def _marcar_offline(device: str):
    _online_devices.discard(device)
    _device_last_seen.pop(device, None)


def _notificar_cbs():
    """Avisa os listeners da lista actual de dispositivos online."""
    for cb in _device_callbacks:
        try:
            cb(list(_online_devices))
        except Exception:
            pass


def _notificar_estado(dev: str, estado: str):
    try:
        from devices_window import DevicesWindow
        DevicesWindow._atualizar_estado_dispositivo(dev, estado)
    except Exception as e:
        print(f"⚠️ Erro ao notificar estado: {e}")


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

        # Subscrever a tópicos ESPHome (BK7231N, ESP8266, ESP32)
        client.subscribe("+/status")             # online/offline ESPHome
        client.subscribe("+/switch/+/state")     # estado dos relés
        client.subscribe("+/switch/+/command")   # respostas a comandos
        client.subscribe("+/light/+/state")      # estado de luzes
        client.subscribe("+/binary_sensor/+/state")  # sensores binários

        # Subscrever tópicos OpenBK (BK7231N/T)
        client.subscribe("+/connected")          # presença OpenBK
        client.subscribe("+/+/get")              # estado de canais OpenBK
        client.subscribe("+/rssi")               # OpenBK publica periodicamente
        client.subscribe("+/uptime")             # OpenBK publica periodicamente
        client.subscribe("+/ip")                 # OpenBK publica periodicamente

        print("📡 Subscrito em tópicos Tasmota + ESPHome")
        
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
    retain = msg.retain  # 1 = mensagem retida (antiga), 0 = mensagem em tempo real

    print(f"[MQTT] {'[RETAIN] ' if retain else ''}{topic} -> {payload}")

    # Extrair nome do dispositivo do tópico
    parts = topic.split('/')
    if len(parts) < 2:
        return

    # Determinar firmware pelo prefixo:
    # Tasmota:  tele/DEVICE/... ou stat/DEVICE/... ou cmnd/DEVICE/...
    # OpenBK/ESPHome: DEVICE/...  (device é sempre parts[0])
    tasmota_prefix = parts[0] in ("tele", "stat", "cmnd", "tasmota", "homeassistant", "esphome")
    if tasmota_prefix:
        device = parts[1]
    else:
        device = parts[0]

    if not _is_valid_device_name(device):
        return

    _known_devices.add(device)

    # ── Tasmota: tele/DEVICE/LWT ─────────────────────────────────────────────
    # Retained LWT é fiável — o broker actualiza-o quando o dispositivo cai
    if topic.endswith("/LWT"):
        if payload == "Online":
            _marcar_online(device)
            print(f"📱 ONLINE (Tasmota LWT{'[R]' if retain else ''}): {device}")
        elif payload == "Offline":
            _marcar_offline(device)
            print(f"📴 OFFLINE (Tasmota LWT): {device}")
        _notificar_cbs()
        return

    # ── OpenBK: DEVICE/connected ──────────────────────────────────────────────
    # OpenBK só publica "online" quando liga — retained é fiável (é o último estado real)
    # Nunca publica "offline" — usa Will Message se configurado
    if not tasmota_prefix and parts[-1] == "connected":
        if payload.lower() in _PAYLOAD_ONLINE:
            _marcar_online(device)
            print(f"📱 ONLINE (OpenBK connected{'[R]' if retain else ''}): {device}")
            # Pedir estado do canal 1 para saber se está ON ou OFF
            if _client and _connected:
                _client.publish(f"{device}/1/get", "")
        elif payload.lower() in _PAYLOAD_OFFLINE:
            _marcar_offline(device)
            print(f"📴 OFFLINE (OpenBK connected): {device}")
        _notificar_cbs()
        return

    # ── ESPHome: DEVICE/status ────────────────────────────────────────────────
    # ESPHome publica "online" e "offline" correctamente — retained é fiável
    if not tasmota_prefix and parts[-1] == "status":
        if payload.lower() in _PAYLOAD_ONLINE:
            _marcar_online(device)
            _esphome_online.add(device)
            print(f"📱 ONLINE (ESPHome status{'[R]' if retain else ''}): {device}")
        elif payload.lower() in _PAYLOAD_OFFLINE:
            _marcar_offline(device)
            _esphome_online.discard(device)
            print(f"📴 OFFLINE (ESPHome status{'[R]' if retain else ''}): {device}")
        _notificar_cbs()
        return

    # ── OpenBK: DEVICE/CHANNEL/get → estado do canal (0/1) ───────────────────
    # Formato: dispositivo/1/get → "1" ou "0"
    if not tasmota_prefix and len(parts) == 3 and parts[2] == "get":
        # Mesmo com canal não numérico, confirma presença
        _marcar_online(device)
        try:
            canal = int(parts[1])
        except ValueError:
            canal = None
        if canal is not None:
            # OpenBK: 1=ON, 0=OFF
            estado = "ON" if payload.strip() in ("1", "ON", "on", "true", "True") else "OFF"
            print(f"📊 OpenBK CHANNEL {canal}: {device} = {estado}")
            _notificar_estado(device, estado)
        _notificar_cbs()
        return

    # ── OpenBK: DEVICE/rssi, DEVICE/uptime, DEVICE/ip → heartbeat periódico ──
    if not tasmota_prefix and len(parts) == 2 and parts[1] in ("rssi", "uptime", "ip", "freeheap", "sockets"):
        _marcar_online(device)
        print(f"💓 HEARTBEAT OpenBK: {device} ({parts[1]}={payload})")
        _notificar_cbs()
        return

    # ── ESPHome: DEVICE/switch/NOME/state ────────────────────────────────────
    # Só actualiza estado se o dispositivo foi confirmado online via /status
    if not tasmota_prefix and len(parts) == 4 and parts[1] == "switch" and parts[3] == "state":
        _esphome_command_topics[device] = topic.replace("/state", "/command")
        # Não adicionar como online apenas por ter switch/state (pode ser retained antigo)
        # Só actualizar estado se já está na lista de online
        if device in _esphome_online or device in _online_devices:
            estado = "ON" if payload.strip().upper() == "ON" else "OFF"
            print(f"📊 ESPHome SWITCH: {device} = {estado}")
            _notificar_estado(device, estado)
            _notificar_cbs()
        return

    # Mensagens retidas de POWER/STATE/RESULT são ignoradas para estado ON/OFF
    # (podem ser de sessões anteriores e não refletem o estado atual)
    if retain:
        print(f"[MQTT] Mensagem retida ignorada para estado: {topic}")
        # Mesmo assim, se o dispositivo tinha LWT=Online, mantém-no na lista
        return

    # A partir daqui: apenas mensagens em tempo real

    # Resposta de POWER
    if "POWER" in topic:
        _online_devices.add(device)
        print(f"📱 POWER: {device} = {payload}")
        if payload in ["ON", "OFF"]:
            _notificar_estado(device, payload)

    # tele/+/STATE — estado completo periódico
    elif topic.endswith("/STATE"):
        _online_devices.add(device)
        print(f"📊 STATE: {device}")
        try:
            data = json.loads(payload)
            if "POWER" in data:
                _notificar_estado(device, data["POWER"])
        except Exception:
            pass

    # stat/+/RESULT — resposta a comandos
    elif topic.endswith("/RESULT"):
        _online_devices.add(device)
        print(f"📊 RESULT: {device}")
        try:
            data = json.loads(payload)
            if "POWER" in data:
                _notificar_estado(device, data["POWER"])
        except Exception:
            pass

    # Qualquer outra mensagem em tempo real — dispositivo está online
    else:
        _online_devices.add(device)

    # Notificar listeners
    _notificar_cbs()


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

        # Broadcast OpenBK: pedir estado dos canais a todos os dispositivos conhecidos
        # O OpenBK responde a cmnd/DEVICE/status e também ao formato nativo
        for device in list(_known_devices):
            if _is_valid_device_name(device):
                # Pedir canal 1 (relé principal) — OpenBK responde com DEVICE/1/get
                _client.publish(f"{device}/1/get", "")
                # Também tentar formato Tasmota (OpenBK suporta ambos)
                _client.publish(f"cmnd/{device}/POWER", "")
        
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


def registar_topico_comando_esphome(device: str, state_topic: str):
    """Regista o tópico de comando ESPHome a partir do tópico de estado."""
    cmd_topic = state_topic.replace("/state", "/command")
    _esphome_command_topics[device] = cmd_topic
    print(f"[ESPHome] Tópico de comando registado: {cmd_topic}")

def enviar_comando_dispositivo(device: str, comando: str) -> bool:
    """
    Envia comando a um dispositivo — detecta automaticamente Tasmota, ESPHome ou OpenBK.
    """
    # ESPHome: usa o tópico de comando registado (dispositivo/switch/nome/command)
    if device in _esphome_command_topics:
        return enviar_mqtt(_esphome_command_topics[device], comando)

    # OpenBK: formato DEVICE/1/set com valor 1 ou 0
    # Se o device publicou via DEVICE/1/get, é OpenBK
    valor = "1" if comando.upper() in ("ON", "1", "TRUE") else "0"
    # Tentar OpenBK primeiro (canal 1 por defeito)
    # e também Tasmota em paralelo — o dispositivo responderá ao que conhece
    sucesso_obk = enviar_mqtt(f"{device}/1/set", valor)
    sucesso_tas = enviar_mqtt(f"cmnd/{device}/POWER", comando)
    return sucesso_obk or sucesso_tas

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


def _limpar_dispositivos_timeout():
    """Remove dispositivos que não publicam há mais de DEVICE_TIMEOUT_SECONDS."""
    global _online_devices
    agora = time.time()
    expirados = {
        d for d in list(_online_devices)
        if d in _device_last_seen and (agora - _device_last_seen[d]) > DEVICE_TIMEOUT_SECONDS
    }
    for d in expirados:
        _online_devices.discard(d)
        _device_last_seen.pop(d, None)
        print(f"⏱️ TIMEOUT: {d} removido (sem actividade há +{DEVICE_TIMEOUT_SECONDS}s)")


def listar_dispositivos_ativos() -> list[str]:
    """
    Retorna lista de dispositivos online (filtrada e sem timeout)
    """
    global _online_devices

    # Remover dispositivos por timeout
    _limpar_dispositivos_timeout()

    # Filtrar dispositivos inválidos
    _online_devices = {d for d in _online_devices if _is_valid_device_name(d)}

    # Se não há dispositivos, tenta descobrir
    if not _online_devices and not _discovery_in_progress:
        threading.Thread(target=_discover_devices, daemon=True).start()
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
    # A pasta já é criada em constants.py, mas garantir por segurança
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
