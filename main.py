#!/usr/bin/env python3
"""
Assistente Virtual - Ponto de entrada principal
"""
import os
import sys
import configparser
import traceback

# No Linux o yt-dlp/deno podem estar em ~/.deno/bin.
# No Windows essa pasta não existe e o PATH do sistema já chega.
_deno = os.path.expanduser("~/.deno/bin")
if os.path.isdir(_deno):
    os.environ["PATH"] = _deno + os.pathsep + os.environ.get("PATH", "")

# Garante que o diretório atual está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _preparar_stdio():
    """
    Num .exe compilado sem consola (--noconsole) o sys.stdout/stdout são None
    e qualquer print() rebentava a aplicação. Redireciona para o "nada".
    """
    for nome in ("stdout", "stderr"):
        stream = getattr(sys, nome, None)
        if stream is None:
            try:
                setattr(sys, nome, open(os.devnull, "w", encoding="utf-8"))
            except OSError:
                pass
        else:
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_preparar_stdio()

from constants import CONFIG_FILE, LOG_FILE
from gui import ChatbotGUI
from config_window import solicitar_configuracao


def garantir_config_ini():
    """
    Se não existir config.ini, abre janela para pedir dados
    """
    if not os.path.exists(CONFIG_FILE):
        print("📝 Primeira execução - a pedir configuração MQTT...")
        cfg = solicitar_configuracao()

        if cfg and "MQTT" in cfg:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                cfg.write(f)
            print("✅ Configuração guardada em config.ini")
        else:
            # Fallback para configuração mínima
            cfg = configparser.ConfigParser()
            cfg["MQTT"] = {
                "host": "localhost",
                "port": "1883",
                "username": "",
                "password": ""
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                cfg.write(f)
            print("⚠️ Usando configuração mínima (localhost)")


def _registar_erro(exc: BaseException) -> str:
    """Guarda o erro num ficheiro de log e devolve o caminho."""
    texto = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(texto)
    except OSError:
        pass
    return LOG_FILE


def _avisar_erro(caminho_log: str):
    """Mostra um aviso ao utilizador quando a app falha ao arrancar."""
    mensagem = (
        "O Assistente Virtual não conseguiu arrancar.\n\n"
        f"Detalhes técnicos guardados em:\n{caminho_log}\n\n"
        "Envia esse ficheiro para condessasilva@gmail.com."
    )
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Assistente Virtual", mensagem)
        root.destroy()
    except Exception:
        print(mensagem)


def main():
    """Função principal"""
    print("=" * 50)
    print("🎙️  Assistente Virtual")
    print("=" * 50)

    # Garante configuração
    garantir_config_ini()

    # Inicia aplicação
    app = ChatbotGUI()

    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\n👋 A encerrar...")
    finally:
        # Limpeza
        try:
            from mqtt_handler import disconnect
            disconnect()
        except Exception:
            pass
        print("✅ Assistente encerrado.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        _avisar_erro(_registar_erro(erro))
        raise
