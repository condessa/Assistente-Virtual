"""
Constantes e paths centralizados para todo o projeto
Funciona em Linux (desenvolvimento e .deb) e Windows (PyInstaller)
"""
import os
import shutil
import sys

IS_WINDOWS = sys.platform.startswith("win")


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


def _pasta_config() -> str:
    """Pasta de configuração do utilizador, por sistema operativo."""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "HCsoftware", "AssistenteVirtual")
    return os.path.join(os.path.expanduser("~"), ".config", "assistente-virtual")


def _pasta_download() -> str:
    """Onde ficam as músicas descarregadas."""
    if IS_WINDOWS:
        return os.path.join(os.path.expanduser("~"), "Music", "Assistente Virtual")
    return os.path.join(os.path.expanduser("~"), ".local", "share",
                        "assistente-virtual", "Download")


# Diretórios importantes
DOWNLOAD_DIR = _pasta_download()
IMAGES_DIR = resource_path("imagens")
FFMPEG_DIR = resource_path(os.path.join("ffmpeg", "bin"))


def _binario(nome: str) -> str:
    """Caminho do ffmpeg/ffprobe: primeiro o embutido, senão o que estiver no PATH."""
    exe = nome + ".exe" if IS_WINDOWS else nome
    embutido = os.path.join(FFMPEG_DIR, exe)
    if os.path.exists(embutido):
        return embutido
    encontrado = shutil.which(nome)
    return encontrado or embutido


FFMPEG_BIN = _binario("ffmpeg")
FFPROBE_BIN = _binario("ffprobe")

# Ficheiros de configuração
# config.ini fica na pasta de configuração do utilizador para que este tenha
# sempre permissão de leitura/escrita, independentemente de onde o programa
# está instalado (/usr/share/... não é editável por utilizadores normais)
CONFIG_DIR = _pasta_config()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
LOG_FILE = os.path.join(CONFIG_DIR, "erro.log")

COMMANDS_FILE = resource_path("commands.json")

# Garantir que os diretórios existem
for _dir in (CONFIG_DIR, DOWNLOAD_DIR):
    try:
        os.makedirs(_dir, exist_ok=True)
    except OSError:
        pass
