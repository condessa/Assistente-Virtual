#!/usr/bin/env python3
"""
Script para testar microfone com diferentes configurações
"""
import speech_recognition as sr
import time

def testar_microfone_completo():
    """Testa o microfone com várias configurações"""
    
    print("=" * 50)
    print("🎤 TESTE DE MICROFONE")
    print("=" * 50)
    
    # Listar microfones disponíveis
    print("\n📋 Microfones disponíveis:")
    try:
        mics = sr.Microphone.list_microphone_names()
        if not mics:
            print("  Nenhum microfone encontrado!")
        else:
            for i, name in enumerate(mics):
                print(f"  {i}: {name}")
    except Exception as e:
        print(f"  Erro ao listar: {e}")
    
    # Testar cada microfone
    for mic_index in range(len(mics) if 'mics' in locals() and mics else [0]):
        print(f"\n🎤 Testando microfone {mic_index}...")
        
        recognizer = sr.Recognizer()
        
        # Configurações ajustáveis
        configs = [
            {"energy": 300, "dynamic": True, "desc": "Baixo threshold"},
            {"energy": 1000, "dynamic": True, "desc": "Médio threshold"},
            {"energy": 3000, "dynamic": True, "desc": "Alto threshold"},
            {"energy": 300, "dynamic": False, "desc": "Baixo fixo"},
        ]
        
        for config in configs:
            print(f"\n⚙️  Config: {config['desc']}")
            print(f"   Energy: {config['energy']}, Dynamic: {config['dynamic']}")
            
            recognizer.energy_threshold = config['energy']
            recognizer.dynamic_energy_threshold = config['dynamic']
            recognizer.pause_threshold = 0.8
            recognizer.phrase_threshold = 0.3
            
            try:
                with sr.Microphone(device_index=mic_index if mic_index < len(mics) else None) as source:
                    print("   Ajustando ruído ambiente...")
                    recognizer.adjust_for_ambient_noise(source, duration=2)
                    print(f"   Energy threshold final: {recognizer.energy_threshold}")
                    
                    print("   A ouvir... (diz 'teste' agora!)")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    
                    print("   ✅ Áudio capturado! A reconhecer...")
                    try:
                        texto = recognizer.recognize_google(audio, language='pt-PT')
                        print(f"   ✅ Reconhecido: '{texto}'")
                        return True
                    except sr.UnknownValueError:
                        print("   ❌ Não percebi")
                    except sr.RequestError as e:
                        print(f"   ❌ Erro serviço: {e}")
                        
            except sr.WaitTimeoutError:
                print("   ❌ Timeout - sem deteção de voz")
            except Exception as e:
                print(f"   ❌ Erro: {e}")
    
    print("\n❌ Nenhuma configuração funcionou.")
    return False

if __name__ == "__main__":
    testar_microfone_completo()
