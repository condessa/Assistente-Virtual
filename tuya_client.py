# tuya_client.py
import json
import os
import tinytuya

from constants import CONFIG_DIR

_CONFIG_PATH = os.path.join(CONFIG_DIR, "tuya_luz_sala.json")


def _carregar_config():
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _dispositivo():
    cfg = _carregar_config()
    d = tinytuya.OutletDevice(cfg["id"], cfg["ip"], cfg["key"])
    d.set_version(float(cfg["version"]))
    return d


def _executar(acao: str, descricao: str) -> bool:
    """Chama turn_on/turn_off no dispositivo; devolve True em caso de sucesso."""
    try:
        resultado = getattr(_dispositivo(), acao)()
        return "Error" not in resultado
    except FileNotFoundError:
        print(f"[ERRO] Ficheiro de configuração da luz da sala não encontrado: {_CONFIG_PATH}")
        return False
    except Exception as e:
        print(f"[ERRO] Tuya {descricao} luz sala: {e}")
        return False


def ligar_luz_sala() -> bool:
    return _executar("turn_on", "ligar")


def desligar_luz_sala() -> bool:
    return _executar("turn_off", "desligar")


def estado_luz_sala():
    """Devolve True (ligada), False (desligada) ou None se não conseguir ler."""
    try:
        status = _dispositivo().status()
        dps = status.get("dps", {})
        return dps.get("1")
    except Exception as e:
        print(f"[ERRO] Tuya estado luz sala: {e}")
        return None
