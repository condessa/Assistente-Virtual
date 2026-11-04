# ollama_client.py
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "llama3.2:3b"

SYSTEM_PROMPT = (
    "És o Assistente Virtual da HCsoftware, um programa de computador em Python "
    "com interface gráfica, criado por Herculano. Tens síntese de voz (consegues "
    "falar as respostas, quando a opção 'Com voz' está ativa) e reconhecimento de "
    "voz. Também sabes tocar música do YouTube, controlar dispositivos domésticos "
    "por MQTT (Tasmota) e pesquisar na web. "
    "Respondes em português de Portugal, de forma direta e conversacional, em 1 a "
    "3 frases curtas, sem listas, sem markdown e sem títulos."
)

def perguntar(prompt: str, timeout: int = 30) -> str:
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODELO,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
            "options": {"num_predict": 120}
        }, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "⚠️ O Ollama não está em execução (corre 'ollama serve')."
    except requests.exceptions.Timeout:
        return "⚠️ O Ollama demorou demasiado tempo a responder."
    except Exception as e:
        return f"⚠️ Erro ao contactar o Ollama: {e}"
