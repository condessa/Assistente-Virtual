"""
Constantes e paths centralizados para todo o projeto
"""
import os
import sys

# Versão unificada e robusta do resource_path
def resource_path(relative_path: str) -> str:
    """
    Obtém o caminho absoluto para um recurso, funcionando em desenvolvimento
    e em executável compilado com PyInstaller.
    """
    try:
        # PyInstaller cria uma pasta temporária e guarda o path em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Em desenvolvimento, usa o diretório do ficheiro atual
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    # Tenta algumas localizações possíveis
    candidates = [
        os.path.join(base_path, relative_path),
        os.path.join(base_path, "_internal", relative_path),
        os.path.join(os.path.dirname(base_path), relative_path)
    ]
    
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    
    # Retorna o primeiro caminho como fallback
    return os.path.join(base_path, relative_path)

# Diretórios importantes
DOWNLOAD_DIR = resource_path("Download")
IMAGES_DIR = resource_path("imagens")
FFMPEG_DIR = resource_path(os.path.join("ffmpeg", "bin"))

# Ficheiros de configuração
CONFIG_FILE = resource_path("config.ini")
COMMANDS_FILE = resource_path("commands.json")

# Garantir que diretórios existem
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
