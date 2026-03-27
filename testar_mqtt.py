#!/usr/bin/env python3
"""
Teste rápido do MQTT
"""
from mqtt_handler import enviar_mqtt, disconnect
import time

print("=" * 50)
print("🔧 TESTE MQTT")
print("=" * 50)

# Testar comando para fluorescente
print("\n📤 A enviar comando para fluorescente...")
sucesso = enviar_mqtt("cmnd/fluorescente/POWER", "ON")

if sucesso:
    print("✅ Comando enviado com sucesso!")
else:
    print("❌ Falha ao enviar comando")

print("\n⏱️  A aguardar 2 segundos...")
time.sleep(2)

print("\n📤 A enviar comando para desligar...")
enviar_mqtt("cmnd/fluorescente/POWER", "OFF")

disconnect()
print("\n✅ Teste concluído")
