"""
Janela de ajuda com suporte a duplo clique para enviar comandos
"""
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from tooltip import Tooltip


def _colors_for_current_mode():
    mode = ctk.get_appearance_mode()
    if mode == "Dark":
        return {"bg": "#2b2b2b", "fg": "#ffffff",
                "selectbg": "#1f6aa5", "selectfg": "#ffffff", "border": "#3a3a3a"}
    else:
        return {"bg": "#ffffff", "fg": "#000000",
                "selectbg": "#1f6aa5", "selectfg": "#ffffff", "border": "#cccccc"}


def mostrar_ajuda(parent, commands=None):
    """Mostra janela de ajuda com lista de atalhos clicáveis"""

    win = ctk.CTkToplevel(parent)
    win.title("Ajuda - Comandos Disponíveis")
    win.geometry("660x420")

    try:
        if parent and hasattr(parent, 'iconbitmap'):
            win.iconbitmap(parent.iconbitmap())
    except Exception:
        pass

    # ── Fontes reduzidas ────────────────────────────────────────────────────
    fonte      = tkfont.Font(family="Segoe UI", size=9)
    fonte_bold = ctk.CTkFont(size=10, weight="bold")
    fonte_btn  = ctk.CTkFont(size=10)
    fonte_chk  = ctk.CTkFont(size=10)

    # Frame principal
    cols = ctk.CTkFrame(win)
    cols.pack(padx=10, pady=10, fill="both", expand=True)
    cols.grid_columnconfigure(0, weight=1)
    cols.grid_columnconfigure(1, weight=1)
    cols.grid_rowconfigure(0, weight=1)

    texto = """📌 Comandos disponíveis

💡 Dispositivos:
• ligar <nome do dispositivo>
• desligar <nome do dispositivo>
• abrir porta

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
    tb.grid(row=0, column=0, padx=(0, 8), pady=(0, 6), sticky="nsew")
    tb.insert("1.0", texto)
    tb.configure(state="disabled")
    try:
        tb._textbox.configure(font=fonte)
    except Exception:
        pass

    # Frame atalhos (direita)
    frame_list = ctk.CTkFrame(cols)
    frame_list.grid(row=0, column=1, padx=(8, 0), pady=(0, 6), sticky="nsew")
    frame_list.grid_rowconfigure(1, weight=1)
    frame_list.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        frame_list,
        text="Atalhos interativos (duplo clique)",
        font=fonte_bold
    ).grid(row=0, column=0, padx=8, pady=(8, 0), sticky="w")

    lista = tk.Listbox(frame_list, activestyle="dotbox")
    lista.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
    lista.config(font=fonte, height=14)

    atalhos = [
        ("🧭 Pesquisar dispositivos", "pesquisar dispositivos", True),
        ("📜 Mostrar playlist",        "mostrar playlist",       True),
        ("🧹 Limpar playlist",         "limpar playlist",        True),
        ("⏸️ Pausar música",           "pausar",                 True),
        ("▶️ Continuar música",        "retomar",                True),
        ("⏹️ Parar música",            "parar",                  True),
        ("🕒 Que horas são?",          "que horas são",          True),
        ("📅 Que dia é hoje?",         "que dia é hoje",         True),
        ("🎵 Tocar música…",           "tocar ",                 False),
        ("💡 Ligar dispositivo…",      "ligar ",                 False),
        ("💡 Desligar dispositivo…",   "desligar ",              False),
        ("🚪 Abrir porta",             "abrir porta",            True),
        ("▶️ Abre no YouTube…",        "abre no youtube ",       False),
        ("🔎 Pesquisa na Web…",        "pesquisa na web ",       False),
    ]

    idx_map = {}
    for i, (label, cmd, auto) in enumerate(atalhos):
        lista.insert(tk.END, label)
        idx_map[i] = (cmd, auto)

    auto_var = tk.BooleanVar(value=True)
    ctk.CTkCheckBox(
        cols,
        text="Enviar automaticamente",
        variable=auto_var,
        font=fonte_chk
    ).grid(row=1, column=1, padx=(8, 0), pady=(0, 4), sticky="w")

    def executar_selecionado():
        sel = lista.curselection()
        if not sel:
            return
        cmd, auto_default = idx_map[sel[0]]
        parent.entry_comando.delete(0, "end")
        if auto_default:
            parent.entry_comando.insert(0, cmd)
            if auto_var.get():
                parent.enviar_comando()
            else:
                parent.entry_comando.focus_set()
                parent.entry_comando.icursor("end")
        else:
            parent.entry_comando.insert(0, cmd)
            parent.entry_comando.focus_set()
            parent.entry_comando.icursor("end")

    lista.bind("<Double-Button-1>", lambda e: executar_selecionado())

    btn_exec = ctk.CTkButton(
        cols, text="Executar selecionado",
        command=executar_selecionado, font=fonte_btn
    )
    btn_exec.grid(row=2, column=1, padx=(8, 0), pady=(0, 8), sticky="w")
    Tooltip(btn_exec, "Executar o atalho selecionado na lista")

    btn_fechar = ctk.CTkButton(
        cols, text="Fechar",
        command=win.destroy, font=fonte_btn
    )
    btn_fechar.grid(row=2, column=0, pady=(0, 8), sticky="e")
    Tooltip(btn_fechar, "Fechar a janela de ajuda")

    colors = _colors_for_current_mode()
    lista.config(
        bg=colors["bg"], fg=colors["fg"],
        selectbackground=colors["selectbg"],
        selectforeground=colors["selectfg"],
        highlightthickness=1,
        highlightbackground=colors["border"]
    )

    win.update_idletasks()
    ww = win.winfo_width()
    wh = win.winfo_height()
    if parent:
        px = parent.winfo_x() + (parent.winfo_width()  - ww) // 2
        py = parent.winfo_y() + (parent.winfo_height() - wh) // 2
    else:
        px = (win.winfo_screenwidth()  - ww) // 2
        py = (win.winfo_screenheight() - wh) // 2
    win.geometry(f"+{px}+{py}")
