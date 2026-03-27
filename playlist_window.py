"""
Janela de playlist de música
"""
import os
import time  # <<< IMPORT ADICIONADO
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox
import customtkinter as ctk
import pygame

from constants import DOWNLOAD_DIR


class PlaylistWindow:
    """Janela para mostrar e gerir playlist"""
    
    win = None
    listbox = None
    player_ref = None
    font = None
    status = None
    
    @classmethod
    def mostrar_playlist(cls, player, parent=None, font_size=13):
        """Mostra janela da playlist"""
        
        # Reusar janela se já existir
        if cls.win and cls.win.winfo_exists():
            cls.player_ref = player
            cls.refresh()
            cls.win.lift()
            return

        # Cria janela
        win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
        cls.win = win
        cls.player_ref = player

        win.title("Playlist")
        win.geometry("600x550")
        
        # Ícone
        try:
            if parent and hasattr(parent, 'iconbitmap'):
                win.iconbitmap(parent.iconbitmap())
        except Exception:
            pass

        # Fonte
        cls.font = tkfont.Font(family="Segoe UI", size=font_size)

        # Frame principal
        main = ctk.CTkFrame(win)
        main.pack(padx=10, pady=10, fill="both", expand=True)

        # Título
        titulo = ctk.CTkLabel(
            main, 
            text="🎵 Minhas Músicas", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        titulo.pack(pady=(0, 10))

        # Informação da pasta
        pasta_info = ctk.CTkLabel(
            main,
            text=f"Pasta: {DOWNLOAD_DIR}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        pasta_info.pack()

        # Frame da lista
        frame_lista = ctk.CTkFrame(main)
        frame_lista.pack(fill="both", expand=True, padx=5, pady=5)

        # Listbox com scrollbar
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
        
        # Botões
        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(fill="x", pady=5)

        cls.btn_tocar = ctk.CTkButton(
            btn_frame,
            text="▶️ Tocar",
            command=cls.tocar_selecionada,
            fg_color="#2e7d32",
            width=100
        )
        cls.btn_tocar.pack(side="left", padx=2, expand=True, fill="x")

        cls.btn_parar = ctk.CTkButton(
            btn_frame,
            text="⏹️ Parar",
            command=cls.parar_musica,
            fg_color="#b71c1c",
            width=100
        )
        cls.btn_parar.pack(side="left", padx=2, expand=True, fill="x")

        cls.btn_remover = ctk.CTkButton(
            btn_frame,
            text="🗑️ Remover",
            command=cls.remover_selecionada,
            fg_color="#ff6d00",
            width=100
        )
        cls.btn_remover.pack(side="left", padx=2, expand=True, fill="x")

        # Segunda linha
        btn_frame2 = ctk.CTkFrame(main)
        btn_frame2.pack(fill="x", pady=5)

        ctk.CTkButton(
            btn_frame2,
            text="🔄 Atualizar",
            command=cls.refresh,
            width=100
        ).pack(side="left", padx=2, expand=True, fill="x")

        ctk.CTkButton(
            btn_frame2,
            text="📂 Abrir pasta",
            command=cls.abrir_pasta,
            width=100
        ).pack(side="left", padx=2, expand=True, fill="x")

        ctk.CTkButton(
            btn_frame2,
            text="Fechar",
            command=win.destroy,
            fg_color="#666666",
            width=80
        ).pack(side="right", padx=2)

        # Status
        cls.status = ctk.CTkLabel(main, text="", anchor="w", font=ctk.CTkFont(size=12))
        cls.status.pack(fill="x", pady=5)

        # Aplica tema
        cls.apply_theme()
        
        # Carrega músicas
        cls.refresh()
        
        # Duplo clique toca
        lb.bind("<Double-Button-1>", lambda e: cls.tocar_selecionada())
        
        # Atualizar estado dos botões periodicamente
        cls.atualizar_estado_botoes()

    @classmethod
    def tocar_selecionada(cls):
        """Toca a música selecionada"""
        if not cls.listbox or not cls.player_ref:
            cls.set_status("❌ Erro: Player não disponível")
            return
            
        sel = cls.listbox.curselection()
        if not sel:
            cls.set_status("⚠️ Selecione uma música")
            return
            
        # Obter o texto selecionado e extrair apenas o nome do ficheiro
        item_texto = cls.listbox.get(sel[0])
        
        # Verificar se é uma mensagem de "sem músicas"
        if item_texto.startswith("—") or "Nenhuma" in item_texto or "Sem" in item_texto:
            cls.set_status("⚠️ Não há músicas para tocar")
            return
        
        # Extrair nome do ficheiro (remover informação de tamanho)
        if "(" in item_texto:
            nome_ficheiro = item_texto.split(" (")[0].strip()
        else:
            nome_ficheiro = item_texto.strip()
        
        # Construir caminho completo
        caminho = os.path.join(DOWNLOAD_DIR, nome_ficheiro)
        
        print(f"[PLAYLIST] A tocar: {caminho}")
        
        # Verificar se o ficheiro existe
        if not os.path.exists(caminho):
            cls.set_status(f"❌ Ficheiro não encontrado: {nome_ficheiro}")
            # Tentar encontrar o ficheiro (ignorar maiúsculas/minúsculas)
            encontrado = False
            for f in os.listdir(DOWNLOAD_DIR):
                if f.lower() == nome_ficheiro.lower():
                    caminho = os.path.join(DOWNLOAD_DIR, f)
                    encontrado = True
                    print(f"[PLAYLIST] Encontrado como: {f}")
                    break
            
            if not encontrado:
                cls.set_status(f"❌ Ficheiro não encontrado: {nome_ficheiro}")
                return
        
        try:
            # Parar música atual se estiver a tocar
            cls.player_ref.parar_musica()
            time.sleep(0.2)  # Agora o time está importado
            
            # Tocar nova música
            cls.player_ref.tocar_arquivo(caminho)
            cls.set_status(f"▶️ A tocar: {nome_ficheiro}")
            
            # Atualizar estado dos botões
            cls.atualizar_estado_botoes()
            
        except Exception as e:
            cls.set_status(f"❌ Erro: {e}")
            print(f"[PLAYLIST] Erro ao tocar: {e}")
            import traceback
            traceback.print_exc()

    @classmethod
    def parar_musica(cls):
        """Para a reprodução"""
        if cls.player_ref:
            cls.player_ref.parar_musica()
            cls.set_status("⏹️ Música parada")
            cls.atualizar_estado_botoes()

    @classmethod
    def remover_selecionada(cls):
        """Remove música selecionada do disco"""
        if not cls.listbox:
            return
            
        sel = cls.listbox.curselection()
        if not sel:
            cls.set_status("⚠️ Selecione uma música")
            return
            
        item_texto = cls.listbox.get(sel[0])
        
        # Verificar se é uma mensagem de "sem músicas"
        if item_texto.startswith("—") or "Nenhuma" in item_texto or "Sem" in item_texto:
            cls.set_status("⚠️ Não há músicas para remover")
            return
        
        # Extrair nome do ficheiro
        if "(" in item_texto:
            nome_ficheiro = item_texto.split(" (")[0].strip()
        else:
            nome_ficheiro = item_texto.strip()
            
        # Confirmação
        confirm = messagebox.askyesno(
            "Confirmar",
            f"Remover '{nome_ficheiro}' da playlist?"
        )
        
        if confirm:
            caminho = os.path.join(DOWNLOAD_DIR, nome_ficheiro)
            try:
                # Verificar se o ficheiro existe
                if os.path.exists(caminho):
                    os.remove(caminho)
                    cls.set_status(f"🗑️ Removido: {nome_ficheiro}")
                else:
                    # Tentar encontrar com case insensitive
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
        """Abre a pasta de downloads no explorador"""
        try:
            if os.path.exists(DOWNLOAD_DIR):
                if os.name == 'nt':  # Windows
                    os.startfile(DOWNLOAD_DIR)
                elif os.name == 'posix':  # Linux/Mac
                    import subprocess
                    subprocess.run(['xdg-open', DOWNLOAD_DIR])
                cls.set_status("📂 Pasta aberta")
        except Exception as e:
            cls.set_status(f"❌ Erro: {e}")

    @classmethod
    def refresh(cls):
        """Atualiza lista de músicas"""
        if not cls.listbox:
            return
            
        lb = cls.listbox
        lb.delete(0, tk.END)
        
        files = []
        if os.path.isdir(DOWNLOAD_DIR):
            files = [f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith(".mp3")]
            files.sort(key=str.lower)
        
        if not files:
            lb.insert(tk.END, "— Sem músicas guardadas —")
            lb.config(state="disabled")
            cls.set_status("📭 Playlist vazia")
        else:
            lb.config(state="normal")
            for f in files:
                # Mostra tamanho do ficheiro
                try:
                    caminho = os.path.join(DOWNLOAD_DIR, f)
                    tamanho = os.path.getsize(caminho) // 1024  # KB
                    lb.insert(tk.END, f"{f} ({tamanho} KB)")
                except:
                    lb.insert(tk.END, f)
            cls.set_status(f"{len(files)} música(s) na playlist")
        
        cls.atualizar_estado_botoes()

    @classmethod
    def atualizar_estado_botoes(cls):
        """Atualiza estado dos botões baseado no player"""
        if not hasattr(cls, 'btn_tocar') or not cls.player_ref:
            return
            
        if cls.player_ref.tocando:
            cls.btn_tocar.configure(state="disabled", fg_color="#666666")
            cls.btn_parar.configure(state="normal", fg_color="#b71c1c")
        else:
            cls.btn_tocar.configure(state="normal", fg_color="#2e7d32")
            cls.btn_parar.configure(state="disabled", fg_color="#666666")

    @classmethod
    def apply_theme(cls):
        """Aplica cores do tema atual"""
        if not cls.listbox:
            return
            
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            colors = {
                "bg": "#2b2b2b", "fg": "#ffffff",
                "selectbg": "#1f6aa5", "selectfg": "#ffffff",
                "border": "#3a3a3a"
            }
        else:
            colors = {
                "bg": "#ffffff", "fg": "#000000",
                "selectbg": "#1f6aa5", "selectfg": "#ffffff",
                "border": "#cccccc"
            }
        
        lb = cls.listbox
        lb.config(
            bg=colors["bg"],
            fg=colors["fg"],
            selectbackground=colors["selectbg"],
            selectforeground=colors["selectfg"],
            highlightthickness=1,
            highlightbackground=colors["border"],
            relief="flat",
            borderwidth=1,
        )

    @classmethod
    def set_status(cls, texto):
        """Atualiza texto de status"""
        if hasattr(cls, 'status') and cls.status:
            cls.status.configure(text=texto)
