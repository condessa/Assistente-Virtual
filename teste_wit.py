import speech_recognition as sr

# Testar com API da Microsoft (não precisa de chave para teste)
r = sr.Recognizer()
with sr.Microphone() as source:
    print("Fala alguma coisa...")
    audio = r.listen(source)
    
    try:
        # Tentar Bing (Microsoft)
        texto = r.recognize_bing(audio, language="pt-BR")
        print(f"Bing: {texto}")
    except:
        try:
            # Tentar Google
            texto = r.recognize_google(audio, language="pt-BR")
            print(f"Google: {texto}")
        except:
            print("Nenhum serviço funcionou")
