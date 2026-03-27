"""
Script para criar ícones placeholder
"""
import os
from PIL import Image, ImageDraw, ImageFont
from constants import IMAGES_DIR

def criar_icone(nome, cor, texto, tamanho=256):
    """Cria um ícone simples"""
    img = Image.new('RGBA', (tamanho, tamanho), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fundo circular
    draw.ellipse([10, 10, tamanho-10, tamanho-10], fill=cor)
    
    # Texto
    try:
        font = ImageFont.truetype("arial.ttf", tamanho//2)
    except:
        font = ImageFont.load_default()
    
    # Centraliza texto
    bbox = draw.textbbox((0, 0), texto, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (tamanho - text_width) // 2
    y = (tamanho - text_height) // 2
    
    draw.text((x, y), texto, fill="white", font=font)
    
    # Guarda
    img.save(os.path.join(IMAGES_DIR, f"{nome}.png"))
    
    # Cria também ICO
    img.save(os.path.join(IMAGES_DIR, f"{nome}.ico"), format='ICO', 
             sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    
    print(f"✅ Criado: {nome}.png e {nome}.ico")

def main():
    """Cria ícones necessários"""
    print("🎨 A criar ícones...")
    
    # Garante pasta
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    # Ícones
    icones = [
        ("chatbot", "#1f6aa5", "🤖"),
        ("playlist", "#2e7d32", "🎵"),
        ("devices", "#ff6d00", "📱"),
        ("enviar", "#1f6aa5", "📤"),
        ("limpar", "#d32f2f", "🗑️"),
        ("microfone", "#2e7d32", "🎤"),
        ("modo_escuro", "#2b2b2b", "🌙"),
        ("modo_claro", "#ffffff", "☀️"),
        ("mqtt", "#ff6d00", "⚙️"),
        ("ajuda", "#1f6aa5", "❓"),
    ]
    
    for nome, cor, texto in icones:
        criar_icone(nome, cor, texto)
    
    print("\n✅ Todos os ícones criados com sucesso!")

if __name__ == "__main__":
    main()
