"""
Reconhecimento de voz usando SpeechRecognition
"""
import speech_recognition as sr
import threading
import time

_STOP = False
_LISTENING = False

def stop_voice():
    """Para o reconhecimento de voz"""
    global _STOP
    _STOP = True
    print("[VOZ] Comando de paragem recebido")

def is_listening():
    """Verifica se está a ouvir"""
    global _LISTENING
    return _LISTENING

def voice_recognition(callback, language='pt-PT'):
    """
    Escuta continuamente e envia texto reconhecido para callback
    """
    global _STOP, _LISTENING
    
    _STOP = False
    _LISTENING = True
    
    r = sr.Recognizer()
    
    # Configurações otimizadas
    r.energy_threshold = 30000
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8
    r.phrase_threshold = 0.3
    r.non_speaking_duration = 0.5
    
    print("[VOZ] A inicializar microfone...")
    
    # Listar microfones disponíveis (debug)
    try:
        mics = sr.Microphone.list_microphone_names()
        print(f"[VOZ] Microfones encontrados: {len(mics)}")
        for i, name in enumerate(mics):
            if name:
                print(f"[VOZ]   {i}: {name}")
    except:
        pass
    
    try:
        with sr.Microphone() as source:
            print("[VOZ] A ajustar para ruído ambiente...")
            r.adjust_for_ambient_noise(source, duration=2)
            print(f"[VOZ] Threshold ajustado: {r.energy_threshold}")
            print("[VOZ] ✅ Pronto! Podes falar...")
            
            while not _STOP:
                try:
                    print("[VOZ] 🎤 A ouvir...")
                    audio = r.listen(source, timeout=2, phrase_time_limit=5)
                    
                    print("[VOZ] ✅ Áudio capturado! A processar...")
                    
                    # Tentar reconhecer
                    try:
                        texto = r.recognize_google(audio, language='pt-PT')
                        print(f"[VOZ] ✅ Reconhecido: '{texto}'")
                        
                        # Callback na thread principal
                        if texto and not _STOP:
                            callback(texto)
                            
                    except sr.UnknownValueError:
                        print("[VOZ] Não percebi (tentar pt-BR)...")
                        try:
                            texto = r.recognize_google(audio, language='pt-BR')
                            print(f"[VOZ] ✅ Reconhecido (pt-BR): '{texto}'")
                            if texto and not _STOP:
                                callback(texto)
                        except:
                            print("[VOZ] ❌ Não percebi o que disseste")
                            
                    except sr.RequestError as e:
                        print(f"[VOZ] ❌ Erro no serviço: {e}")
                        
                except sr.WaitTimeoutError:
                    # Timeout normal - continua
                    continue
                    
                except Exception as e:
                    print(f"[VOZ] ⚠️ Erro: {e}")
                    time.sleep(0.5)
                    
    except Exception as e:
        print(f"[VOZ] ❌ Erro no microfone: {e}")
        print("[VOZ] Verifica se o microfone está ligado e a funcionar.")
        callback("[ERRO] Microfone não disponível")
        
    finally:
        _LISTENING = False
        print("[VOZ] 👋 Reconhecimento parado.")

def testar_microfone():
    """Testa o funcionamento do microfone"""
    print("🎤 A testar microfone...")
    
    r = sr.Recognizer()
    r.energy_threshold = 4000
    
    try:
        with sr.Microphone() as source:
            print("A ajustar ruído...")
            r.adjust_for_ambient_noise(source, duration=1)
            print(f"Threshold: {r.energy_threshold}")
            print("Diz 'teste' agora (tens 3 segundos)...")
            
            audio = r.listen(source, timeout=3, phrase_time_limit=2)
            print("Áudio capturado! A reconhecer...")
            
            texto = r.recognize_google(audio, language='pt-PT')
            print(f"✅ Reconhecido: '{texto}'")
            
            if 'teste' in texto.lower():
                print("✅✅✅ Microfone OK!")
                return True
            else:
                print(f"⚠️ Reconheceu '{texto}' em vez de 'teste'")
                return False
                
    except sr.WaitTimeoutError:
        print("❌ Timeout - ninguém falou")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return False

if __name__ == "__main__":
    testar_microfone()
