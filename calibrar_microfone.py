import speech_recognition as sr

# Testar diferentes thresholds
for threshold in [100, 200, 300, 400, 500]:
    print(f"\n🔍 Testando threshold: {threshold}")
    r = sr.Recognizer()
    r.energy_threshold = threshold
    r.dynamic_energy_threshold = False
    
    try:
        with sr.Microphone(device_index=3) as source:
            print("Diz 'teste' agora...")
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            texto = r.recognize_google(audio, language='pt-PT')
            print(f"✅ Reconhecido: '{texto}'")
            if 'teste' in texto.lower():
                print(f"🎯 Threshold {threshold} FUNCIONOU!")
                break
    except:
        print(f"❌ Threshold {threshold} falhou")
        continue
