"""
Text-to-Speech usando Google TTS (voz natural)
"""
import os
import tempfile
import threading
import time
import pygame
from gtts import gTTS

# Inicializar pygame mixer
try:
    pygame.mixer.init()
except:
    pass

# Cache de vozes para evitar downloads repetidos
_tts_cache = {}
_cache_dir = os.path.join(tempfile.gettempdir(), "tts_cache")
os.makedirs(_cache_dir, exist_ok=True)

def falar(texto: str, idioma='pt', velocidade='normal', use_cache=True):
    """
    Fala o texto usando Google TTS
    
    Args:
        texto: Texto a ser falado
        idioma: 'pt' (Portugal), 'pt-br' (Brasil), 'en' (Inglês)
        velocidade: 'normal' ou 'lento'
        use_cache: Se True, guarda em cache para uso futuro
    """
    if not texto:
        return
    
    def _play():
        try:
            # Remove caracteres que podem causar problemas
            texto_clean = ''.join(c for c in texto if c.isalnum() or c.isspace() or c in '.,!?')
            
            # Gera nome do ficheiro cache
            import hashlib
            hash_obj = hashlib.md5(f"{texto_clean}_{idioma}_{velocidade}".encode())
            cache_file = os.path.join(_cache_dir, f"{hash_obj.hexdigest()}.mp3")
            
            # Verifica cache
            if use_cache and os.path.exists(cache_file):
                temp_filename = cache_file
            else:
                # Cria ficheiro temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                    temp_filename = f.name
                
                # Gera áudio
                tts = gTTS(text=texto_clean, lang=idioma, slow=(velocidade=='lento'))
                tts.save(temp_filename)
                
                # Guarda em cache se desejado
                if use_cache:
                    try:
                        import shutil
                        shutil.copy2(temp_filename, cache_file)
                    except:
                        pass
            
            # Reproduz
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            
            # Aguarda terminar
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            # Limpa temporário (não o cache)
            if not use_cache or not os.path.exists(cache_file):
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                
        except Exception as e:
            print(f"Erro no TTS: {e}")
    
    # Executa em thread
    threading.Thread(target=_play, daemon=True).start()

def falar_sync(texto: str, idioma='pt'):
    """Versão síncrona (bloqueante)"""
    if not texto:
        return
    
    try:
        tts = gTTS(text=texto, lang=idioma)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_filename = f.name
        tts.save(temp_filename)
        
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
        os.unlink(temp_filename)
    except Exception as e:
        print(f"Erro no TTS síncrono: {e}")

# Teste rápido
if __name__ == "__main__":
    falar("Olá! Eu sou o teu assistente virtual. Esta é a minha voz.")
    time.sleep(3)
