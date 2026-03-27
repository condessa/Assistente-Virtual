#!/usr/bin/env python3
"""
Assistente Virtual - Ponto de entrada principal
"""
import os
import sys
import configparser

# Garante que o diretório atual está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import CONFIG_FILE
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
        from mqtt_handler import disconnect
        disconnect()
        print("✅ Assistente encerrado.")


if __name__ == "__main__":
    main()
