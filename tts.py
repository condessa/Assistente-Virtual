"""
Text-to-Speech usando Google TTS (voz natural)
"""
import os
import tempfile
import threading
import time
import hashlib
import shutil
import pygame
from gtts import gTTS

# Inicializar pygame mixer
try:
    pygame.mixer.init()
    pygame.mixer.set_num_channels(8)
except Exception:
    pass

# Canal dedicado ao TTS (separado do music player que usa pygame.mixer.music)
_TTS_CHANNEL = None

def _get_channel():
    """Obtém o canal dedicado ao TTS"""
    global _TTS_CHANNEL
    try:
        if _TTS_CHANNEL is None:
            _TTS_CHANNEL = pygame.mixer.Channel(7)  # canal 7 reservado para TTS
        return _TTS_CHANNEL
    except Exception:
        return None

# Cache de vozes para evitar downloads repetidos
_cache_dir = os.path.join(tempfile.gettempdir(), "tts_cache")
os.makedirs(_cache_dir, exist_ok=True)

# Lock para evitar sobreposição de falas
_tts_lock = threading.Lock()


def _normalizar_texto_tts(texto: str) -> str:
    """
    Converte padrões numéricos que o gTTS lê mal para texto por extenso.
    Ex: 'anos 70' -> 'anos setenta', '80s' -> 'oitenta'
    """
    import re

    dezenas = {
        10: 'dez', 11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze',
        15: 'quinze', 16: 'dezasseis', 17: 'dezassete', 18: 'dezoito', 19: 'dezanove',
        20: 'vinte', 30: 'trinta', 40: 'quarenta', 50: 'cinquenta',
        60: 'sessenta', 70: 'setenta', 80: 'oitenta', 90: 'noventa',
    }
    séculos = {
        1900: 'mil e novecentos', 1910: 'mil novecentos e dez',
        1920: 'mil novecentos e vinte', 1930: 'mil novecentos e trinta',
        1940: 'mil novecentos e quarenta', 1950: 'mil novecentos e cinquenta',
        1960: 'mil novecentos e sessenta', 1970: 'mil novecentos e setenta',
        1980: 'mil novecentos e oitenta', 1990: 'mil novecentos e noventa',
        2000: 'dois mil', 2010: 'dois mil e dez', 2020: 'dois mil e vinte',
    }

    # Anos por extenso: 1970, 1980, 2000, etc.
    def substituir_ano(m):
        n = int(m.group(0))
        return séculos.get(n, m.group(0))
    texto = re.sub(r'\b(19[0-9]{2}|20[0-2][0-9])\b', substituir_ano, texto)

    # Décadas com 's' ou sozinhas: 70s, 80s, anos 70, anos 80
    def substituir_decada(m):
        n = int(m.group(1))
        return dezenas.get(n, m.group(0))
    texto = re.sub(r'\b([1-9]\d)s?\b', substituir_decada, texto)

    return texto


def _gerar_audio(texto: str, idioma: str, velocidade: str) -> str | None:
    """Gera ou obtém do cache o ficheiro mp3. Retorna o caminho ou None."""
    texto = _normalizar_texto_tts(texto)
    texto_clean = ''.join(c for c in texto if c.isalnum() or c.isspace() or c in '.,!?:-')
    if not texto_clean.strip():
        return None

    hash_key = hashlib.md5(f"{texto_clean}_{idioma}_{velocidade}".encode()).hexdigest()
    cache_file = os.path.join(_cache_dir, f"{hash_key}.mp3")

    if os.path.exists(cache_file):
        return cache_file

    try:
        tts = gTTS(text=texto_clean, lang=idioma, slow=(velocidade == 'lento'))
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            tmp = f.name
        tts.save(tmp)
        shutil.move(tmp, cache_file)
        return cache_file
    except Exception as e:
        print(f"[TTS] Erro ao gerar áudio: {e}")
        return None


def falar(texto: str, idioma='pt', velocidade='normal', bloquear=True):
    """
    Fala o texto usando Google TTS.

    Args:
        texto:     Texto a ser falado
        idioma:    'pt' (Portugal), 'pt-br' (Brasil), 'en' (Inglês)
        velocidade: 'normal' ou 'lento'
        bloquear:  Se True (padrão), aguarda até o áudio terminar antes de retornar.
                   A chamada é sempre feita numa thread separada para não bloquear
                   o event loop do tkinter, mas internamente espera pelo fim do áudio.
    """
    if not texto:
        return

    def _play():
        with _tts_lock:
            _idioma = idioma if idioma is not None else "pt"
            print(f"[TTS] A falar: '{texto[:50]}' (idioma={_idioma})")
            caminho = _gerar_audio(texto, _idioma, velocidade)
            if not caminho:
                print("[TTS] Falhou a gerar áudio")
                return
            print(f"[TTS] Áudio gerado: {caminho}")
            try:
                canal = _get_channel()
                print(f"[TTS] Canal: {canal}, Mixer init: {pygame.mixer.get_init()}")
                if canal:
                    sound = pygame.mixer.Sound(caminho)
                    canal.play(sound)
                    print("[TTS] A reproduzir no canal 7...")
                    while canal.get_busy():
                        time.sleep(0.05)
                    print("[TTS] Concluído")
                else:
                    print("[TTS] Canal indisponível, a usar mixer.music")
                    pygame.mixer.music.load(caminho)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
            except Exception as e:
                print(f"[TTS] Erro ao reproduzir: {e}")
                import traceback
                traceback.print_exc()

    t = threading.Thread(target=_play, daemon=True)
    t.start()
    if bloquear:
        t.join()


def falar_sync(texto: str, idioma='pt'):
    """Alias para compatibilidade — equivalente a falar(..., bloquear=True)"""
    falar(texto, idioma=idioma, bloquear=True)


def parar_tts():
    """Para imediatamente qualquer fala em curso (não afeta a música)"""
    try:
        canal = _get_channel()
        if canal:
            canal.stop()
    except Exception:
        pass


# Teste rápido
if __name__ == "__main__":
    falar("Olá! Eu sou o teu assistente virtual. Esta é a minha voz.")
