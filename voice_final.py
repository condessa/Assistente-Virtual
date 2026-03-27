"""
Reconhecimento de voz usando PyAudio + SpeechRecognition - VERSÃO FINAL
"""
import speech_recognition as sr
import threading
import time
import pyaudio
import wave
import io

_STOP = False
_LISTENING = False

# Usar microfone PulseAudio
MICROFONE_INDEX = 3

def stop_voice():
    """Para o reconhecimento de voz"""
    global _STOP
    _STOP = True
    print("[VOZ] Comando de paragem recebido")

def voice_recognition(callback, language='pt-PT'):
    """
    Escuta continuamente e envia texto reconhecido para callback
    """
    global _STOP, _LISTENING
    
    _STOP = False
    _LISTENING = True
    
    r = sr.Recognizer()
    
    # Configurações otimizadas
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8
    
    print(f"[VOZ] Usando microfone índice: {MICROFONE_INDEX}")
    
    try:
        with sr.Microphone(device_index=MICROFONE_INDEX) as source:
            print("[VOZ] A ajustar para ruído ambiente...")
            r.adjust_for_ambient_noise(source, duration=2)
            print(f"[VOZ] Threshold: {r.energy_threshold}")
            print("[VOZ] ✅ Pronto! Podes falar...")
            
            while not _STOP:
                try:
                    print("[VOZ] 🎤 A ouvir...")
                    # Aumentar timeout e phrase_time_limit
                    audio = r.listen(source, timeout=3, phrase_time_limit=8)
                    
                    print("[VOZ] ✅ Áudio capturado!")
                    
                    # Salvar áudio temporariamente para debug
                    with open("temp_audio.wav", "wb") as f:
                        f.write(audio.get_wav_data())
                    
                    # Tentar reconhecer com retry
                    for tentativa in range(3):
                        try:
                            texto = r.recognize_google(audio, language='pt-PT', show_all=False)
                            print(f"[VOZ] ✅ Reconhecido: '{texto}'")
                            
                            if texto and not _STOP:
                                callback(texto)
                            break
                        except sr.UnknownValueError:
                            if tentativa == 2:
                                print("[VOZ] Não percebi após 3 tentativas")
                        except sr.RequestError as e:
                            print(f"[VOZ] Erro no serviço: {e}")
                            time.sleep(1)
                        except Exception as e:
                            print(f"[VOZ] Erro inesperado: {e}")
                            break
                            
                except sr.WaitTimeoutError:
                    continue
                    
    except Exception as e:
        print(f"[VOZ] ❌ Erro no microfone: {e}")
        callback("[ERRO] Microfone não disponível")
        
    finally:
        _LISTENING = False
        print("[VOZ] 👋 Reconhecimento parado.")

def testar_microfone():
    """Testa o funcionamento do microfone com gravação e reprodução"""
    print("🎤 A testar microfone...")
    print("Este teste vai gravar 3 segundos e tentar reconhecer.")
    
    import pyaudio
    import wave
    
    # Configurações de gravação
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 3
    
    p = pyaudio.PyAudio()
    
    # Listar dispositivos
    print("\nDispositivos disponíveis:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']}")
    
    # Usar dispositivo padrão
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=MICROFONE_INDEX,
                    frames_per_buffer=CHUNK)
    
    print(f"\n🎤 A gravar {RECORD_SECONDS} segundos...")
    frames = []
    
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    print("✅ Gravação concluída!")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Salvar arquivo
    filename = "teste_microfone.wav"
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"📁 Áudio salvo em: {filename}")
    
    # Reproduzir o áudio
    print("🔊 A reproduzir gravação...")
    import os
    os.system(f"aplay {filename}")
    
    # Tentar reconhecer com speech_recognition
    print("\n🔍 A tentar reconhecer o áudio gravado...")
    r = sr.Recognizer()
    
    with sr.AudioFile(filename) as source:
        audio = r.record(source)
        
        try:
            texto = r.recognize_google(audio, language='pt-PT')
            print(f"✅ Reconhecido: '{texto}'")
            return True
        except sr.UnknownValueError:
            print("❌ Não percebi o áudio")
        except sr.RequestError as e:
            print(f"❌ Erro no serviço: {e}")
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    return False

if __name__ == "__main__":
    testar_microfone()
