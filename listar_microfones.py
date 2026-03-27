import speech_recognition as sr
import pyaudio

print("=" * 50)
print("🎤 MICROFONES DISPONÍVEIS")
print("=" * 50)

# Listar com PyAudio
p = pyaudio.PyAudio()
print("\n📋 Microfones (PyAudio):")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f"  [{i}] {info['name']}")
        print(f"      Canais: {int(info['maxInputChannels'])}")
        print(f"      Taxa: {int(info['defaultSampleRate'])} Hz")
p.terminate()

# Listar com SpeechRecognition
print("\n📋 Microfones (SpeechRecognition):")
try:
    mics = sr.Microphone.list_microphone_names()
    for i, name in enumerate(mics):
        if name:
            print(f"  [{i}] {name}")
except Exception as e:
    print(f"Erro: {e}")

print("\n✅ Para usar um microfone específico, adiciona no código:")
print('   with sr.Microphone(device_index=INDICE) as source:')
