"""
Janela de configuração MQTT
"""
import configparser
import customtkinter as ctk


def solicitar_configuracao(parent=None):
    """
    Mostra janela de configuração MQTT
    Retorna ConfigParser com secção [MQTT]
    """
    cfg = configparser.ConfigParser()
    result = {}

    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title("Configuração do MQTT")
    win.geometry("480x400")
    win.resizable(False, False)
    
    # Tenta centralizar
    win.update_idletasks()
    if parent:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (win.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    font_lbl = ctk.CTkFont("Segoe UI", 14)
    font_in = ctk.CTkFont("Segoe UI", 14)

    # Título
    ctk.CTkLabel(
        win, 
        text="Configuração do MQTT", 
        font=ctk.CTkFont(size=18, weight="bold")
    ).pack(pady=(14, 6))

    # Frame do formulário
    frame = ctk.CTkFrame(win)
    frame.pack(fill="x", padx=20, pady=10)

    entradas = {}
    campos = [
        ("host", "Endereço do broker", "192.168.1.100"),
        ("port", "Porta", "1883"),
        ("username", "Utilizador", ""),
    ]

    # Campos normais
    for key, rotulo, padrao in campos:
        row = ctk.CTkFrame(frame)
        row.pack(fill="x", padx=10, pady=6)
        
        ctk.CTkLabel(row, text=rotulo, width=150, anchor="w", font=font_lbl).pack(side="left")
        
        ent = ctk.CTkEntry(row, width=220, font=font_in)
        ent.insert(0, padrao)
        ent.pack(side="left", padx=(8, 0))
        
        entradas[key] = ent

    # Password com checkbox "mostrar"
    row_pwd = ctk.CTkFrame(frame)
    row_pwd.pack(fill="x", padx=10, pady=6)
    
    ctk.CTkLabel(row_pwd, text="Palavra-passe", width=150, anchor="w", font=font_lbl).pack(side="left")
    
    ent_pwd = ctk.CTkEntry(row_pwd, width=220, font=font_in, show="•")
    ent_pwd.pack(side="left", padx=(8, 0))
    entradas["password"] = ent_pwd

    # Checkbox mostrar password
    chk_row = ctk.CTkFrame(frame)
    chk_row.pack(fill="x", padx=10, pady=(0, 10))
    
    mostrar_var = ctk.BooleanVar(value=False)
    
    def toggle_password():
        ent_pwd.configure(show="" if mostrar_var.get() else "•")
    
    ctk.CTkCheckBox(
        chk_row, 
        text="Mostrar palavra-passe", 
        variable=mostrar_var,
        command=toggle_password
    ).pack(side="left", padx=(150, 0))

    # Informação
    ctk.CTkLabel(
        win, 
        text="Os dados serão guardados em config.ini", 
        text_color="gray70"
    ).pack(pady=(0, 10))

    def confirmar():
        cfg["MQTT"] = {
            "host": entradas["host"].get().strip(),
            "port": entradas["port"].get().strip() or "1883",
            "username": entradas["username"].get().strip(),
            "password": entradas["password"].get(),
        }
        nonlocal result
        result = cfg
        win.destroy()

    def testar_conexao():
        """Testa conexão MQTT com os dados inseridos"""
        from mqtt_handler import _ensure_client
        # Guarda config temporária
        old_cfg = None
        try:
            # TODO: Implementar teste
            ctk.CTkMessageBox.showinfo("Teste", "Funcionalidade em breve!")
        except Exception as e:
            ctk.CTkMessageBox.showerror("Erro", f"Falha no teste: {e}")

    # Botões
    btn_frame = ctk.CTkFrame(win)
    btn_frame.pack(pady=10)

    ctk.CTkButton(
        btn_frame, 
        text="Guardar", 
        command=confirmar,
        font=font_in,
        width=120
    ).pack(side="left", padx=5)

    ctk.CTkButton(
        btn_frame, 
        text="Cancelar", 
        command=win.destroy,
        fg_color="#666666",
        font=font_in,
        width=120
    ).pack(side="left", padx=5)

    win.grab_set()  # Modal
    win.wait_window()
    
    return result
