"""
Janela de playlist de música
"""
import os
import time
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox
import customtkinter as ctk
import pygame

from constants import DOWNLOAD_DIR
from tooltip import Tooltip


class PlaylistWindow:
    """Janela para mostrar e gerir playlist"""
    
    win = None
    listbox = None
    player_ref = None
    font = None
    status = None
    _subpasta_atual = None
    
    @classmethod
    def mostrar_playlist(cls, player, parent=None, font_size=9):
        """Mostra janela da playlist"""
        
        if cls.win and cls.win.winfo_exists():
            cls.player_ref = player
            cls.refresh()
            cls.win.lift()
            return

        win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
        cls.win = win
        cls.player_ref = player

        win.title("Playlist")
        win.geometry("640x540")
        
        try:
            if parent and hasattr(parent, 'iconbitmap'):
                win.iconbitmap(parent.iconbitmap())
        except Exception:
            pass

        # ── Fontes reduzidas ────────────────────────────────────────────────
        cls.font  = tkfont.Font(family="Segoe UI", size=font_size)
        font_btn  = ctk.CTkFont(size=11)
        font_lbl  = ctk.CTkFont(size=11)
        font_tit  = ctk.CTkFont(size=14, weight="bold")
        font_info = ctk.CTkFont(size=10)

        main = ctk.CTkFrame(win)
        main.pack(padx=10, pady=10, fill="both", expand=True)

        ctk.CTkLabel(main, text="🎵 Minhas Músicas", font=font_tit).pack(pady=(0, 6))

        ctk.CTkLabel(
            main, text=f"Pasta: {DOWNLOAD_DIR}",
            font=font_info, text_color="gray"
        ).pack()

        frame_lista = ctk.CTkFrame(main)
        frame_lista.pack(fill="both", expand=True, padx=4, pady=4)

        lb = tk.Listbox(
            frame_lista,
            activestyle="dotbox",
            selectmode=tk.SINGLE,
            font=cls.font,
            height=15,
            exportselection=False
        )
        lb.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(frame_lista, command=lb.yview)
        scroll.pack(side="right", fill="y")
        lb.config(yscrollcommand=scroll.set)

        cls.listbox = lb
        
        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(fill="x", pady=3)

        cls.btn_anterior = ctk.CTkButton(
            btn_frame, text="⏮️",
            command=cls.faixa_anterior,
            fg_color="#37474f", width=36, font=font_btn, height=26
        )
        cls.btn_anterior.pack(side="left", padx=2)
        Tooltip(cls.btn_anterior, "Faixa anterior da subpasta")

        cls.btn_tocar = ctk.CTkButton(
            btn_frame, text="▶️ Tocar",
            command=cls.tocar_selecionada,
            fg_color="#2e7d32", width=70, font=font_btn, height=26
        )
        cls.btn_tocar.pack(side="left", padx=2, expand=True, fill="x")
        Tooltip(cls.btn_tocar, "Tocar a música selecionada na lista")

        cls.btn_proxima = ctk.CTkButton(
            btn_frame, text="⏭️",
            command=cls.faixa_proxima,
            fg_color="#37474f", width=36, font=font_btn, height=26
        )
        cls.btn_proxima.pack(side="left", padx=2)
        Tooltip(cls.btn_proxima, "Próxima faixa da subpasta")

        cls.btn_parar = ctk.CTkButton(
            btn_frame, text="⏹️ Parar",
            command=cls.parar_musica,
            fg_color="#b71c1c", width=70, font=font_btn, height=26
        )
        cls.btn_parar.pack(side="left", padx=2, expand=True, fill="x")

        cls.btn_remover = ctk.CTkButton(
            btn_frame, text="🗑️ Remover",
            command=cls.remover_selecionada,
            fg_color="#ff6d00", width=70, font=font_btn, height=26
        )
        cls.btn_remover.pack(side="left", padx=2, expand=True, fill="x")

        ctk.CTkButton(
            btn_frame, text="🔄 Atualizar",
            command=cls.refresh,
            width=70, font=font_btn, height=26
        ).pack(side="left", padx=2, expand=True, fill="x")

        ctk.CTkButton(
            btn_frame, text="📂 Pasta",
            command=cls.abrir_pasta,
            width=70, font=font_btn, height=26
        ).pack(side="left", padx=2, expand=True, fill="x")

        btn_extrair = ctk.CTkButton(
            btn_frame, text="✂️ Extrair faixas",
            command=lambda: cls.extrair_faixas(win),
            fg_color="#6a1b9a", width=70, font=font_btn, height=26
        )
        btn_extrair.pack(side="left", padx=2, expand=True, fill="x")
        Tooltip(btn_extrair, "Extrair faixas individuais do ficheiro selecionado")

        ctk.CTkButton(
            btn_frame, text="✖ Fechar",
            command=win.destroy,
            fg_color="#666666", width=70, font=font_btn, height=26
        ).pack(side="left", padx=2, expand=True, fill="x")

        Tooltip(cls.btn_parar,   "Parar a música a tocar")
        Tooltip(cls.btn_remover, "Remover a música selecionada do disco")

        cls.status = ctk.CTkLabel(main, text="", anchor="w", font=font_lbl)
        cls.status.pack(fill="x", pady=3)

        cls.apply_theme()
        cls.refresh()
        lb.bind("<Double-Button-1>", lambda e: cls.tocar_selecionada())
        cls.atualizar_estado_botoes()

        # Centralizar relativamente ao parent
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

    @classmethod
    def tocar_selecionada(cls):
        if not cls.listbox or not cls.player_ref:
            cls.set_status("❌ Erro: Player não disponível")
            return
        sel = cls.listbox.curselection()
        if not sel:
            cls.set_status("⚠️ Selecione uma música")
            return
        item_texto = cls.listbox.get(sel[0])
        if item_texto.startswith("—") or "Nenhuma" in item_texto or "Sem" in item_texto:
            cls.set_status("⚠️ Não há músicas para tocar")
            return
        nome_ficheiro = item_texto.split(" (")[0].strip() if "(" in item_texto else item_texto.strip()
        caminho = os.path.join(DOWNLOAD_DIR, nome_ficheiro)
        if not os.path.exists(caminho):
            for f in os.listdir(DOWNLOAD_DIR):
                if f.lower() == nome_ficheiro.lower():
                    caminho = os.path.join(DOWNLOAD_DIR, f)
                    break
            else:
                cls.set_status(f"❌ Ficheiro não encontrado: {nome_ficheiro}")
                return
        try:
            cls.player_ref.parar_musica()
            time.sleep(0.2)
            cls.player_ref.tocar_arquivo(caminho)
            cls.set_status(f"▶️ A tocar: {nome_ficheiro}")
            cls.atualizar_estado_botoes()
        except Exception as e:
            cls.set_status(f"❌ Erro: {e}")

    @classmethod
    def parar_musica(cls):
        if cls.player_ref:
            cls.player_ref.parar_musica()
            cls.set_status("⏹️ Música parada")
            cls.atualizar_estado_botoes()

    @classmethod
    def remover_selecionada(cls):
        if not cls.listbox:
            return
        sel = cls.listbox.curselection()
        if not sel:
            cls.set_status("⚠️ Selecione uma música")
            return
        item_texto = cls.listbox.get(sel[0])
        if item_texto.startswith("—") or "Nenhuma" in item_texto or "Sem" in item_texto:
            cls.set_status("⚠️ Não há músicas para tocar")
            return
        nome_ficheiro = item_texto.split(" (")[0].strip() if "(" in item_texto else item_texto.strip()
        confirm = messagebox.askyesno("Confirmar", f"Remover '{nome_ficheiro}' da playlist?")
        if confirm:
            caminho = os.path.join(DOWNLOAD_DIR, nome_ficheiro)
            try:
                if os.path.exists(caminho):
                    os.remove(caminho)
                    cls.set_status(f"🗑️ Removido: {nome_ficheiro}")
                else:
                    for f in os.listdir(DOWNLOAD_DIR):
                        if f.lower() == nome_ficheiro.lower():
                            os.remove(os.path.join(DOWNLOAD_DIR, f))
                            cls.set_status(f"🗑️ Removido: {f}")
                            break
                    else:
                        cls.set_status(f"❌ Ficheiro não encontrado: {nome_ficheiro}")
                cls.refresh()
            except Exception as e:
                cls.set_status(f"❌ Erro ao remover: {e}")

    @classmethod
    def abrir_pasta(cls):
        try:
            if os.path.exists(DOWNLOAD_DIR):
                if os.name == 'nt':
                    os.startfile(DOWNLOAD_DIR)
                elif os.name == 'posix':
                    import subprocess
                    subprocess.run(['xdg-open', DOWNLOAD_DIR])
                cls.set_status("📂 Pasta aberta")
        except Exception as e:
            cls.set_status(f"❌ Erro: {e}")

    @classmethod
    def _musicas_subpasta(cls) -> list:
        pasta = cls._subpasta_atual if (cls._subpasta_atual and os.path.isdir(cls._subpasta_atual)) else DOWNLOAD_DIR
        return sorted([os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(".mp3")])

    @classmethod
    def faixa_proxima(cls):
        if not cls.player_ref:
            return
        musicas = cls._musicas_subpasta()
        if not musicas:
            cls.set_status("⚠️ Sem faixas na subpasta")
            return
        atual = cls.player_ref.musica_atual
        try:
            idx = (musicas.index(atual) + 1) % len(musicas)
        except ValueError:
            idx = 0
        cls.player_ref.tocar_arquivo(musicas[idx])
        cls.set_status(f"⏭️ {os.path.basename(musicas[idx])}")

    @classmethod
    def faixa_anterior(cls):
        if not cls.player_ref:
            return
        musicas = cls._musicas_subpasta()
        if not musicas:
            cls.set_status("⚠️ Sem faixas na subpasta")
            return
        atual = cls.player_ref.musica_atual
        try:
            idx = (musicas.index(atual) - 1) % len(musicas)
        except ValueError:
            idx = len(musicas) - 1
        cls.player_ref.tocar_arquivo(musicas[idx])
        cls.set_status(f"⏮️ {os.path.basename(musicas[idx])}")

    @classmethod
    def extrair_faixas(cls, parent=None):
        if not cls.listbox:
            return
        sel = cls.listbox.curselection()
        if not sel:
            cls.set_status("⚠️ Selecione uma música para extrair faixas")
            return
        item_texto = cls.listbox.get(sel[0])
        if item_texto.startswith("—") or "Nenhuma" in item_texto:
            cls.set_status("⚠️ Não há músicas para extrair")
            return
        nome = item_texto.split(" (")[0].strip() if "(" in item_texto else item_texto.strip()
        caminho = os.path.join(DOWNLOAD_DIR, nome)
        if not os.path.exists(caminho):
            cls.set_status(f"❌ Ficheiro não encontrado: {nome}")
            return
        try:
            import importlib.util
            extrator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extrator_faixas.py")
            if not os.path.exists(extrator_path):
                cls.set_status("❌ extrator_faixas.py não encontrado")
                return
            spec = importlib.util.spec_from_file_location("extrator_faixas", extrator_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            app = mod.App()
            app.audio_file = caminho
            app.file_lbl.configure(text=nome)
            import re as _re
            nome_limpo = _re.sub(r"[_-]+", " ", os.path.splitext(nome)[0]).strip().title()
            subpasta = os.path.join(DOWNLOAD_DIR, nome_limpo)
            os.makedirs(subpasta, exist_ok=True)
            cls._subpasta_atual = subpasta
            app.out_entry.delete(0, "end")
            app.out_entry.insert(0, subpasta)
            app.album_entry.delete(0, "end")
            app.album_entry.insert(0, nome_limpo)
            app.album_ck.deselect()
            app.after(300, app.on_detect)
            app.protocol("WM_DELETE_WINDOW", lambda: (
                app.destroy(),
                cls.refresh() if cls.win and cls.win.winfo_exists() else None
            ))
            cls.set_status(f"✂️ Extrator aberto para: {nome}")
        except Exception as e:
            cls.set_status(f"❌ Erro ao abrir extrator: {e}")

    @classmethod
    def refresh(cls):
        if not cls.listbox:
            return
        lb = cls.listbox
        lb.delete(0, tk.END)
        files = []
        if os.path.isdir(DOWNLOAD_DIR):
            files = sorted([f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith(".mp3")], key=str.lower)
        if not files:
            lb.insert(tk.END, "— Sem músicas guardadas —")
            lb.config(state="disabled")
            cls.set_status("📭 Playlist vazia")
        else:
            lb.config(state="normal")
            for f in files:
                try:
                    tamanho = os.path.getsize(os.path.join(DOWNLOAD_DIR, f)) // 1024
                    lb.insert(tk.END, f"{f} ({tamanho} KB)")
                except Exception:
                    lb.insert(tk.END, f)
            cls.set_status(f"{len(files)} música(s) na playlist")
        cls.atualizar_estado_botoes()

    @classmethod
    def atualizar_estado_botoes(cls):
        if not hasattr(cls, 'btn_tocar') or not cls.player_ref:
            return
        if cls.player_ref.tocando:
            cls.btn_tocar.configure(state="disabled", fg_color="#666666")
            cls.btn_parar.configure(state="normal",   fg_color="#b71c1c")
        else:
            cls.btn_tocar.configure(state="normal",   fg_color="#2e7d32")
            cls.btn_parar.configure(state="disabled", fg_color="#666666")

    @classmethod
    def apply_theme(cls):
        if not cls.listbox:
            return
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            colors = {"bg": "#2b2b2b", "fg": "#ffffff",
                      "selectbg": "#1f6aa5", "selectfg": "#ffffff", "border": "#3a3a3a"}
        else:
            colors = {"bg": "#ffffff", "fg": "#000000",
                      "selectbg": "#1f6aa5", "selectfg": "#ffffff", "border": "#cccccc"}
        cls.listbox.config(
            bg=colors["bg"], fg=colors["fg"],
            selectbackground=colors["selectbg"],
            selectforeground=colors["selectfg"],
            highlightthickness=1,
            highlightbackground=colors["border"],
            relief="flat", borderwidth=1,
        )

    @classmethod
    def set_status(cls, texto):
        if hasattr(cls, 'status') and cls.status:
            cls.status.configure(text=texto)
