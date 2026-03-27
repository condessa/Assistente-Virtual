"""
Janela de ajuda com suporte a duplo clique para enviar comandos
"""
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk


def _colors_for_current_mode():
    """Retorna cores conforme tema atual"""
    mode = ctk.get_appearance_mode()
    if mode == "Dark":
        return {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "selectbg": "#1f6aa5",
            "selectfg": "#ffffff",
            "border": "#3a3a3a",
        }
    else:
        return {
            "bg": "#ffffff",
            "fg": "#000000",
            "selectbg": "#1f6aa5",
            "selectfg": "#ffffff",
            "border": "#cccccc",
        }


def mostrar_ajuda(parent, commands=None):
    """Mostra janela de ajuda com lista de atalhos clicáveis"""
    
    win = ctk.CTkToplevel(parent)
    win.title("Ajuda - Comandos Disponíveis")
    win.geometry("760x520")
    
    try:
        if parent and hasattr(parent, 'iconbitmap'):
            win.iconbitmap(parent.iconbitmap())
    except Exception:
        pass

    fonte = tkfont.Font(family="Segoe UI", size=14)

    # Frame principal com duas colunas
    cols = ctk.CTkFrame(win)
    cols.pack(padx=10, pady=10, fill="both", expand=True)
    cols.grid_columnconfigure(0, weight=1)
    cols.grid_columnconfigure(1, weight=1)
    cols.grid_rowconfigure(0, weight=1)

    # Texto de ajuda (esquerda)
    texto = """📌 Comandos disponíveis

💡 Dispositivos:
• ligar <nome do dispositivo>
• desligar <nome do dispositivo>
• abrir <nome do dispositivo> (ex.: abrir porta)

🔌 MQTT / Dispositivos:
• pesquisar dispositivos   → abre janela com lista

🎵 Música:
• tocar <nome da música>
• pausa | pausar
• continua | retomar
• parar
• limpar playlist
• mostrar playlist
• volume <0-100>

🌐 Web:
• abre no youtube <termo>
• pesquisa na web <termo>

🕒 Utilitários:
• que horas são
• que dia é hoje
"""

    # Caixa de texto à esquerda
    tb = ctk.CTkTextbox(cols, wrap="word")
    tb.grid(row=0, column=0, padx=(0,8), pady=(0,6), sticky="nsew")
    tb.insert("1.0", texto)
    tb.configure(state="disabled")
    try:
        tb._textbox.configure(font=fonte)
    except:
        tb.configure(font=fonte)

    # Frame para atalhos (direita)
    frame_list = ctk.CTkFrame(cols)
    frame_list.grid(row=0, column=1, padx=(8,0), pady=(0,6), sticky="nsew")
    frame_list.grid_rowconfigure(1, weight=1)
    frame_list.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        frame_list, 
        text="Atalhos interativos (duplo clique)",
        font=ctk.CTkFont(size=14, weight="bold")
    ).grid(row=0, column=0, padx=8, pady=(8,0), sticky="w")

    # Lista de atalhos
    lista = tk.Listbox(frame_list, activestyle="dotbox")
    lista.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
    lista.config(font=fonte, height=14)

    # Atalhos disponíveis
    atalhos = [
        ("🧭 Pesquisar dispositivos", "pesquisar dispositivos", True),
        ("📜 Mostrar playlist", "mostrar playlist", True),
        ("🧹 Limpar playlist", "limpar playlist", True),
        ("⏸️ Pausar música", "pausar", True),
        ("▶️ Continuar música", "retomar", True),
        ("⏹️ Parar música", "parar", True),
        ("🕒 Que horas são?", "que horas são", True),
        ("📅 Que dia é hoje?", "que dia é hoje", True),
        ("🎵 Tocar música…", "tocar ", False),  # Espaço no final para digitar
        ("💡 Ligar dispositivo…", "ligar ", False),
        ("💡 Desligar dispositivo…", "desligar ", False),
        ("🚪 Abrir porta", "abrir porta", True),
        ("▶️ Abre no YouTube…", "abre no youtube ", False),
        ("🔎 Pesquisa na Web…", "pesquisa na web ", False),
    ]

    idx_map = {}
    for i, (label, cmd, auto) in enumerate(atalhos):
        lista.insert(tk.END, label)
        idx_map[i] = (cmd, auto)

    # Checkbox para envio automático
    auto_var = tk.BooleanVar(value=True)
    ctk.CTkCheckBox(
        cols, 
        text="Enviar automaticamente", 
        variable=auto_var
    ).grid(row=1, column=1, padx=(8,0), pady=(0,4), sticky="w")

    def executar_selecionado():
        """Função chamada ao clicar/duplo clique num atalho"""
        sel = lista.curselection()
        if not sel:
            return
        
        cmd, auto_default = idx_map[sel[0]]
        print(f"[DEBUG] Atalho clicado: '{cmd}', auto: {auto_default}")
        
        # Limpa o campo de entrada
        parent.entry_comando.delete(0, "end")
        
        if auto_default:
            # Comando completo (ex: "que horas são")
            parent.entry_comando.insert(0, cmd)
            if auto_var.get():
                parent.enviar_comando()
            else:
                parent.entry_comando.focus_set()
                parent.entry_comando.icursor("end")
        else:
            # Comando que precisa de complemento (ex: "tocar")
            parent.entry_comando.insert(0, cmd)
            parent.entry_comando.focus_set()
            parent.entry_comando.icursor("end")

    # Bind do duplo clique
    lista.bind("<Double-Button-1>", lambda e: executar_selecionado())

    # Botão executar
    ctk.CTkButton(
        cols, 
        text="Executar selecionado", 
        command=executar_selecionado
    ).grid(row=2, column=1, padx=(8,0), pady=(0,8), sticky="w")

    # Botão fechar
    ctk.CTkButton(
        cols, 
        text="Fechar", 
        command=win.destroy
    ).grid(row=2, column=0, pady=(0,8), sticky="e")

    # Aplicar cores do tema
    colors = _colors_for_current_mode()
    lista.config(
        bg=colors["bg"],
        fg=colors["fg"],
        selectbackground=colors["selectbg"],
        selectforeground=colors["selectfg"],
        highlightthickness=1,
        highlightbackground=colors["border"]
    )

    # Centralizar a janela
    win.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (win.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (win.winfo_height() // 2)
    win.geometry(f"+{x}+{y}")
