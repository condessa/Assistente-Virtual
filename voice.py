"""
Reconhecimento de voz usando SpeechRecognition - VERSÃO SEM FEEDBACK
"""
import speech_recognition as sr
import threading
import time

_STOP = False
_LISTENING = False
_ACTIVE = False

# Usar microfone PulseAudio
MICROFONE_INDEX = 3
THRESHOLD = 1500

def stop_voice():
    """Para o reconhecimento de voz"""
    global _STOP
    _STOP = True
    print("[VOZ] Comando de paragem recebido")

def set_active(active):
    """Ativa/desativa a escuta"""
    global _ACTIVE
    _ACTIVE = active

def voice_recognition(callback):
    """
    Escuta continuamente - SEM MENSAGENS DE ÁUDIO
    """
    global _STOP, _LISTENING, _ACTIVE
    
    _STOP = False
    _LISTENING = True
    
    r = sr.Recognizer()
    r.energy_threshold = THRESHOLD
    r.dynamic_energy_threshold = False
    r.pause_threshold = 0.8
    
    try:
        with sr.Microphone(device_index=MICROFONE_INDEX) as source:
            # Ajuste único de ruído
            r.adjust_for_ambient_noise(source, duration=1)
            
            while not _STOP:
                if _ACTIVE:
                    try:
                        audio = r.listen(source, timeout=3, phrase_time_limit=3)
                        
                        try:
                            texto = r.recognize_google(audio, language='pt-PT')
                            print(f"[VOZ] ✅ '{texto}'")
                            
                            if texto and len(texto) > 2:
                                callback(texto)
                                _ACTIVE = False  # Desativa após comando
                            
                        except:
                            pass
                            
                    except sr.WaitTimeoutError:
                        _ACTIVE = False  # Timeout desativa
                else:
                    time.sleep(0.1)
                    
    except Exception as e:
        print(f"[VOZ] ❌ Erro: {e}")
        
    finally:
        _LISTENING = False

def testar_microfone():
    """Testa o microfone"""
    r = sr.Recognizer()
    r.energy_threshold = THRESHOLD
    
    try:
        with sr.Microphone(device_index=MICROFONE_INDEX) as source:
            print("🎤 Diz 'teste'...")
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            texto = r.recognize_google(audio, language='pt-PT')
            print(f"✅ '{texto}'")
            return 'teste' in texto.lower()
    except:
        return False
