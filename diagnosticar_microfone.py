#!/usr/bin/env python3
"""
Script para diagnosticar problemas com o microfone
"""
import speech_recognition as sr
import pyaudio
import time

def diagnosticar():
    print("=" * 50)
    print("🔧 DIAGNÓSTICO DO MICROFONE")
    print("=" * 50)
    
    # 1. Verificar versões
    print("\n📦 Versões:")
    print(f"   SpeechRecognition: {sr.__version__}")
    print(f"   PyAudio: {pyaudio.__version__}")
    
    # 2. Listar dispositivos de áudio
    print("\n🎤 Dispositivos de áudio:")
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:  # Só dispositivos com entrada
            print(f"   {i}: {dev['name']}")
            print(f"      Taxas: {int(dev['defaultSampleRate'])} Hz")
            print(f"      Canais: {int(dev['maxInputChannels'])}")
    p.terminate()
    
    # 3. Testar microfone com diferentes configurações
    print("\n🔍 A testar microfone com diferentes configurações...")
    
    configuracoes = [
        {"energy": 300, "dynamic": True, "pause": 0.5},
        {"energy": 1000, "dynamic": True, "pause": 0.8},
        {"energy": 3000, "dynamic": True, "pause": 1.0},
        {"energy": 5000, "dynamic": False, "pause": 0.8},
    ]
    
    for i, config in enumerate(configuracoes):
        print(f"\n⚙️  Configuração {i+1}:")
        print(f"   Energy: {config['energy']}, Dynamic: {config['dynamic']}, Pause: {config['pause']}")
        
        r = sr.Recognizer()
        r.energy_threshold = config['energy']
        r.dynamic_energy_threshold = config['dynamic']
        r.pause_threshold = config['pause']
        
        try:
            with sr.Microphone() as source:
                print("   A ajustar ruído...")
                r.adjust_for_ambient_noise(source, duration=1)
                print(f"   Threshold final: {r.energy_threshold}")
                print("   A ouvir (diz 'teste' agora)...")
                
                audio = r.listen(source, timeout=3, phrase_time_limit=2)
                print("   ✅ Áudio capturado!")
                
                try:
                    texto = r.recognize_google(audio, language='pt-PT')
                    print(f"   ✅ Reconhecido: '{texto}'")
                    return True
                except sr.UnknownValueError:
                    print("   ❌ Não percebi")
                except sr.RequestError as e:
                    print(f"   ❌ Erro serviço: {e}")
                    
        except sr.WaitTimeoutError:
            print("   ❌ Timeout - sem áudio")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    print("\n❌ Nenhuma configuração funcionou.")
    return False

if __name__ == "__main__":
    diagnosticar()
