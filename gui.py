"""
Interface gráfica principal do Assistente Virtual
Estilo: AluminioManager — sidebar escura, cabeçalho laranja HCsoftware
"""
import os
import threading
import time
import customtkinter as ctk
from tkinter import font as tkfont

from voice import voice_recognition, stop_voice, set_active, testar_microfone
from tts import falar
from music_player import MusicPlayer
from playlist_window import PlaylistWindow
from devices_window import DevicesWindow
from mqtt_handler import ensure_config_present, subscrever_dispositivos
import mqtt_handler as _mqtt_handler
from command_processor import CommandProcessor
from constants import IMAGES_DIR
from tooltip import Tooltip


# ── Paleta de cores (espelha o AluminioManager) ─────────────────────────────
DARK_BG      = "#1a2332"   # sidebar / fundo principal
DARKER_BG    = "#141c28"   # barra lateral mais escura
ORANGE       = "#d4560a"   # laranja primário (botões principais, cabeçalho)
ORANGE_HOVER = "#c04a08"
ORANGE_LIGHT = "#FF8C00"   # laranja secundário
CARD_BG      = "#1e2d40"   # fundo dos cards/painéis
CARD_BORDER  = "#243447"
TEXT_PRIMARY = "#e8edf2"
TEXT_MUTED   = "#8a9bb0"
TEXT_ACCENT  = "#d4560a"
GREEN        = "#2e7d32"
GREEN_LIGHT  = "#43a047"
RED          = "#b71c1c"
RED_LIGHT    = "#e53935"
BLUE         = "#1f6aa5"
AMBER        = "#f57c00"
SEPARATOR    = "#2a3a52"


class ChatbotGUI(ctk.CTk):
    """Janela principal do Assistente Virtual — estilo HCsoftware"""

    def __init__(self):
        super().__init__()

        # ── Tema base ────────────────────────────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._tema_escuro = True

        # ── Janela ───────────────────────────────────────────────────────────
        self.title("Assistente Virtual HCsoftware")
        self.geometry("1020x660")
        self.minsize(860, 540)
        self.configure(fg_color=DARK_BG)

        try:
            ico_path = os.path.join(IMAGES_DIR, "chatbot.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

        # ── Estado ───────────────────────────────────────────────────────────
        self.voz_ativa       = False
        self.tts_silenciado  = True
        self.music_player    = MusicPlayer()
        self.voice_thread    = None
        self.voice_running   = False
        self._slider_a_mover = False
        self._help_refs      = None

        # ── Processadores ────────────────────────────────────────────────────
        self.command_processor = CommandProcessor(self.music_player, self)
        self.music_player.set_gui(self)

        try:
            from devices_window import set_gui_ref
            set_gui_ref(self)
        except Exception:
            pass

        # ── Construção da UI ─────────────────────────────────────────────────
        self._build_gui()

        # ── Callbacks do MusicPlayer ─────────────────────────────────────────
        self.music_player.on_download_status   = self._on_dl_status
        self.music_player.on_download_progress = self._on_dl_progress
        self.music_player.on_state_change      = self._on_player_state
        self.music_player.on_progress          = lambda pos, dur: self.after(
            0, lambda: self._on_progress(pos, dur))
        self.music_player.on_chat_message      = lambda msg: self.after(
            0, lambda: self.exibir_mensagem("Chatbot", msg))

        self.slider_volume.configure(state="disabled")

        # ── Centralizar janela no ecrã ──────────────────────────────────────
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = self.winfo_width()
        h  = self.winfo_height()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # ── MQTT e boas-vindas ───────────────────────────────────────────────
        self.after(100, self._verificar_config_mqtt)
        subscrever_dispositivos(self._on_devices_changed)
        self.after(500, lambda: self.exibir_mensagem(
            "Chatbot",
            "Olá! Sou o teu assistente virtual. Podes digitar comandos ou ativar o modo voz."))

    # ════════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DA INTERFACE
    # ════════════════════════════════════════════════════════════════════════

    def _build_gui(self):
        """Constrói toda a interface no estilo AluminioManager."""

        # ── Raiz: sidebar | conteúdo ─────────────────────────────────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ══════════════════════════════════════
        # SIDEBAR ESQUERDA
        # ══════════════════════════════════════
        self._build_sidebar()

        # ══════════════════════════════════════
        # ÁREA PRINCIPAL (direita)
        # ══════════════════════════════════════
        self._build_main_area()

    # ── Sidebar ─────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, width=210, fg_color=DARKER_BG, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1)
        sidebar.grid_propagate(False)

        # ── Logótipo / cabeçalho da sidebar ─────────────────────────────────
        logo_frame = ctk.CTkFrame(sidebar, fg_color=DARK_BG, corner_radius=0, height=90)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)

        # Imagem chatbot.png em vez de emoji
        try:
            from PIL import Image as _PIL
            _cb_path = os.path.join(IMAGES_DIR, "chatbot.png")
            _cb_img = _PIL.open(_cb_path)
            _ratio = 28 / _cb_img.height
            _cb_ctk = ctk.CTkImage(
                light_image=_cb_img, dark_image=_cb_img,
                size=(int(_cb_img.width * _ratio), 28))
            ctk.CTkLabel(logo_frame, image=_cb_ctk, text="").pack(pady=(6, 0))
        except Exception:
            ctk.CTkLabel(logo_frame, text="🎙️",
                         font=ctk.CTkFont(size=22)).pack(pady=(6, 0))

        ctk.CTkLabel(
            logo_frame, text="Assistente Virtual",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack()

        # "by HCsoftware.png" por baixo do título
        try:
            from PIL import Image as _PIL_hc
            _hc_img = _PIL_hc.open(os.path.join(IMAGES_DIR, "HCsoftware.png"))
            _ratio_hc = 14 / _hc_img.height
            _hc_ctk = ctk.CTkImage(
                light_image=_hc_img, dark_image=_hc_img,
                size=(int(_hc_img.width * _ratio_hc), 14))
            brand_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
            brand_frame.pack(pady=(2, 5))
            ctk.CTkLabel(brand_frame, text="by ",
                         font=ctk.CTkFont(size=9),
                         text_color=TEXT_MUTED).pack(side="left")
            ctk.CTkLabel(brand_frame, image=_hc_ctk, text="").pack(side="left")
        except Exception:
            ctk.CTkLabel(logo_frame, text="by HCsoftware",
                         font=ctk.CTkFont(family="BlackChancery", size=11),
                         text_color="#A0522D").pack(pady=(2, 5))

        # Separador laranja
        ctk.CTkFrame(sidebar, height=3, fg_color=ORANGE, corner_radius=0).pack(fill="x")

        # ── Secção VISTA (primeiro, como pedido) ─────────────────────────────
        self._sidebar_section(sidebar, "VISTA")
        self.btn_limpar = self._sidebar_btn(
            sidebar, "🧹  Limpar chat", self.limpar_texto)
        self.btn_silenciar = self._sidebar_btn(
            sidebar, "🔔  Com voz", self.toggle_silenciar)
        self.btn_tema = self._sidebar_btn(
            sidebar, "☀️  Tema claro", self.toggle_tema)

        # ── Secção FERRAMENTAS ───────────────────────────────────────────────
        self._sidebar_section(sidebar, "FERRAMENTAS")
        self.btn_testar_voz = self._sidebar_btn(
            sidebar, "🎤  Testar mic", self.testar_microfone)
        self.btn_dispositivos = self._sidebar_btn(
            sidebar, "📱  Dispositivos", self.mostrar_dispositivos)
        self.btn_config = self._sidebar_btn(
            sidebar, "⚙️  MQTT", self.abrir_config_mqtt)
        self.btn_ajuda = self._sidebar_btn(
            sidebar, "❓  Ajuda", self.mostrar_ajuda)

        # ── Secção INTERAÇÃO (por último, perto do rodapé) ───────────────────
        self._sidebar_section(sidebar, "INTERAÇÃO")
        self.btn_voz = self._sidebar_btn(
            sidebar, "🎤  Voz ON", self.toggle_voz)
        self.btn_parar = self._sidebar_btn(
            sidebar, "⏹️  Parar música", self.parar_musica)
        self.btn_sair_sidebar = self._sidebar_btn(
            sidebar, "🚪  Sair", self.quit)

        # Espaço expansível
        ctk.CTkFrame(sidebar, fg_color="transparent").pack(expand=True, fill="both")

        # ── Rodapé: branding "by HCsoftware.png" ────────────────────────────
        rodape = ctk.CTkFrame(sidebar, fg_color=DARK_BG, corner_radius=0, height=48)
        rodape.pack(fill="x", side="bottom")
        rodape.pack_propagate(False)

        _brand_frame = ctk.CTkFrame(rodape, fg_color="transparent")
        _brand_frame.pack(expand=True)
        try:
            from PIL import Image as _PIL_Image
            _hc_img = _PIL_Image.open(os.path.join(IMAGES_DIR, "HCsoftware.png"))
            _ratio = 20 / _hc_img.height
            _hc_ctk = ctk.CTkImage(
                light_image=_hc_img, dark_image=_hc_img,
                size=(int(_hc_img.width * _ratio), 20))
            ctk.CTkLabel(_brand_frame, text="by ",
                         font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side="left")
            ctk.CTkLabel(_brand_frame, image=_hc_ctk, text="").pack(side="left")
        except Exception:
            ctk.CTkLabel(_brand_frame, text="by HCsoftware",
                         font=ctk.CTkFont(family="BlackChancery", size=14),
                         text_color="#A0522D").pack()

        # ── Tooltips sidebar ─────────────────────────────────────────────────
        Tooltip(self.btn_voz,          "Ativar/desativar reconhecimento de voz")
        Tooltip(self.btn_parar,        "Parar a música que está a tocar")
        Tooltip(self.btn_sair_sidebar, "Fechar o Assistente Virtual")
        Tooltip(self.btn_testar_voz,   "Testar se o microfone está a funcionar")
        Tooltip(self.btn_dispositivos, "Controlar dispositivos IoT via MQTT")
        Tooltip(self.btn_config,       "Configurar ligação ao broker MQTT")
        Tooltip(self.btn_ajuda,        "Ver lista de comandos disponíveis")
        Tooltip(self.btn_limpar,       "Limpar o histórico de mensagens")
        Tooltip(self.btn_silenciar,    "Silenciar/ativar a voz do assistente")
        Tooltip(self.btn_tema,         "Alternar entre tema escuro e claro")

    def _sidebar_section(self, parent, title: str):
        """Cabeçalho de secção na sidebar."""
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=16, pady=(14, 2))

    def _sidebar_btn(self, parent, text: str, cmd, color=None, accent=False):
        """Botão de navegação da sidebar — estilo AluminioManager.
        
        Todos transparentes; só os marcados como accent ficam com cor de fundo.
        """
        btn = ctk.CTkButton(
            parent,
            text=text,
            command=cmd,
            anchor="w",
            corner_radius=6,
            height=34,
            font=ctk.CTkFont(size=13),
            fg_color=ORANGE if accent else "transparent",
            hover_color=ORANGE_HOVER if accent else "#2a3a52",
            text_color=TEXT_PRIMARY,
        )
        btn.pack(fill="x", padx=10, pady=2)
        return btn

    # ── Área principal ───────────────────────────────────────────────────────
    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # ── Cabeçalho laranja ────────────────────────────────────────────────
        header = ctk.CTkFrame(main, fg_color=DARK_BG , corner_radius=0, height=52)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="💬  Chat",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).grid(row=0, column=0, padx=18, pady=14, sticky="w")

        # Status MQTT e Voz no cabeçalho (à direita)
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.grid(row=0, column=1, sticky="e", padx=12)

        self.mqtt_status = ctk.CTkLabel(
            status_frame, text="● MQTT",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#b0bec5"
        )
        self.mqtt_status.pack(side="left", padx=(0, 14))

        self.voz_status = ctk.CTkLabel(
            status_frame, text="● Voz",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#b0bec5"
        )
        self.voz_status.pack(side="left", padx=(0, 6))

        # ── Corpo: chat + input ──────────────────────────────────────────────
        body = ctk.CTkFrame(main, fg_color=DARK_BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # Área de histórico
        self.txt_area = ctk.CTkTextbox(
            body, wrap="word",
            fg_color=CARD_BG,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            corner_radius=10,
            border_width=1,
            border_color=CARD_BORDER,
            cursor="arrow",
        )
        self.txt_area.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="nsew")
        self.txt_area.configure(state="disabled")

        # Barra de progresso download (oculta por defeito)
        self.lbl_prog = ctk.CTkLabel(body, text="", anchor="w",
                                     font=ctk.CTkFont(size=11),
                                     text_color=TEXT_MUTED)
        self.pb = ctk.CTkProgressBar(body, fg_color=CARD_BG,
                                     progress_color=ORANGE)
        self.pb.set(0)
        self.lbl_prog.grid_forget()
        self.pb.grid_forget()

        # ── Painel de entrada + controlos de música ──────────────────────────
        self._build_input_panel(body)

    def _build_input_panel(self, parent):
        """Painel inferior: entrada de texto e controlos de música."""
        panel = ctk.CTkFrame(
            parent, fg_color=CARD_BG,
            corner_radius=10, border_width=1, border_color=CARD_BORDER
        )
        panel.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")
        panel.grid_columnconfigure(0, weight=1)

        # ── Linha de entrada ─────────────────────────────────────────────────
        row_input = ctk.CTkFrame(panel, fg_color="transparent")
        row_input.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="ew")
        row_input.grid_columnconfigure(0, weight=1)

        self.entry_comando = ctk.CTkEntry(
            row_input,
            placeholder_text="Digite um comando ou prima Enter...",
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=DARK_BG,
            border_color=SEPARATOR,
            text_color=TEXT_PRIMARY,
        )
        self.entry_comando.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry_comando.bind("<Return>", lambda e: self.enviar_comando())

        self.btn_enviar = ctk.CTkButton(
            row_input, text="📤 Enviar", width=88, height=38,
            fg_color=ORANGE, hover_color=ORANGE_HOVER,
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.enviar_comando
        ).grid(row=0, column=1)

        # ── Linha de música ──────────────────────────────────────────────────
        row_music = ctk.CTkFrame(panel, fg_color="transparent")
        row_music.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Ícone música
        ctk.CTkLabel(
            row_music, text="🎵",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 6))

        # Slider progresso
        self.slider_progresso = ctk.CTkSlider(
            row_music, from_=0, to=100, width=200,
            button_color=ORANGE, progress_color=ORANGE_LIGHT,
            command=self._seek_musica
        )
        self.slider_progresso.set(0)
        self.slider_progresso.configure(state="disabled")
        self.slider_progresso.pack(side="left", padx=(0, 6))
        Tooltip(self.slider_progresso, "Posição da música — arrasta para avançar ou recuar")

        self.lbl_progresso = ctk.CTkLabel(
            row_music, text="0:00",
            font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, width=36, anchor="w"
        )
        self.lbl_progresso.pack(side="left", padx=(0, 18))

        # Separador
        ctk.CTkFrame(row_music, width=1, height=20,
                     fg_color=SEPARATOR).pack(side="left", padx=(0, 18))

        # Volume
        ctk.CTkLabel(
            row_music, text="🔊",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 4))

        self.slider_volume = ctk.CTkSlider(
            row_music, from_=0, to=100, width=130,
            button_color=ORANGE, progress_color=ORANGE_LIGHT,
            command=self.ajustar_volume
        )
        self.slider_volume.set(50)
        self.slider_volume.pack(side="left", padx=(0, 4))
        Tooltip(self.slider_volume, "Volume da música (0-100%)")

        self.lbl_volume_val = ctk.CTkLabel(
            row_music, text="50%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED, width=34, anchor="w"
        )
        self.lbl_volume_val.pack(side="left", padx=(0, 14))

        # Separador
        ctk.CTkFrame(row_music, width=1, height=20,
                     fg_color=SEPARATOR).pack(side="left", padx=(0, 14))



    # ════════════════════════════════════════════════════════════════════════
    # LÓGICA / HANDLERS
    # ════════════════════════════════════════════════════════════════════════

    def _verificar_config_mqtt(self):
        if not ensure_config_present(self):
            self.exibir_mensagem("Chatbot",
                "⚠️ Configuração MQTT não encontrada. Usa ⚙️ MQTT na barra lateral.")
        else:
            self._atualizar_status_mqtt()

    def _on_devices_changed(self, devices):
        pass

    # ── Seek ────────────────────────────────────────────────────────────────
    def _seek_musica(self, valor):
        if not self.music_player.tocando:
            return
        dur = self.music_player._duracao
        if dur > 0:
            self.music_player._seek_pendente = (float(valor) / 100.0) * dur

    def _on_progress(self, pos: float, dur: float):
        try:
            if dur > 0:
                self.slider_progresso.set((pos / dur) * 100.0)
            m, s = divmod(int(pos), 60)
            self.lbl_progresso.configure(text=f"{m}:{s:02d}")
        except Exception:
            pass

    # ── Volume ───────────────────────────────────────────────────────────────
    def ajustar_volume(self, valor):
        v = int(float(valor))
        try:
            self.lbl_volume_val.configure(text=f"{v}%")
        except Exception:
            pass
        if str(self.slider_volume.cget("state")).lower() != "disabled":
            self.music_player.controlar_volume(v)

    # ── Enviar comando ───────────────────────────────────────────────────────
    def enviar_comando(self):
        comando = self.entry_comando.get().strip()
        if not comando:
            return
        print(f"[DEBUG] Comando: '{comando}'")
        self.exibir_mensagem("Você", comando)
        resposta = self.command_processor.process(comando)
        self.exibir_mensagem("Chatbot", resposta)
        self.entry_comando.delete(0, "end")

    # ── Exibir mensagem ──────────────────────────────────────────────────────
    def exibir_mensagem(self, remetente, mensagem):
        self.txt_area.configure(state="normal")
        self.txt_area.insert("end", f"{remetente}: {mensagem}\n")
        self.txt_area.configure(state="disabled")
        self.txt_area.see("end")

        if remetente.lower() == "chatbot" and not self.voz_ativa and not self.tts_silenciado:
            gui_ref = self
            def _falar(msg=mensagem):
                if not gui_ref.tts_silenciado:
                    falar(msg, bloquear=True)
            threading.Thread(target=_falar, daemon=True).start()

    # ── Parar música ─────────────────────────────────────────────────────────
    def parar_musica(self):
        resultado = self.music_player.parar_musica()
        self.exibir_mensagem("Chatbot", resultado)

    # ── Silenciar TTS ────────────────────────────────────────────────────────
    def toggle_silenciar(self):
        self.tts_silenciado = not self.tts_silenciado
        if self.tts_silenciado:
            try:
                from tts import parar_tts
                parar_tts()
            except Exception:
                pass
            self.btn_silenciar.configure(text="🔔  Com voz", fg_color="transparent")
        else:
            self.btn_silenciar.configure(text="🔕  Sem voz", fg_color="transparent")

    # ── Testar microfone ──────────────────────────────────────────────────────
    def testar_microfone(self):
        self.exibir_mensagem("Chatbot", "🎤 A testar microfone... diz 'teste'!")
        def _test():
            resultado = testar_microfone()
            msg = "✅ Microfone OK!" if resultado else "❌ Problema no microfone!"
            self.after(0, lambda: self.exibir_mensagem("Chatbot", msg))
        threading.Thread(target=_test, daemon=True).start()

    # ── Toggle voz ───────────────────────────────────────────────────────────
    def toggle_voz(self):
        if not self.voz_ativa:
            if not self.voice_running:
                self.voice_running = True
                self.voice_thread = threading.Thread(
                    target=lambda: voice_recognition(self.processar_voz),
                    daemon=True)
                self.voice_thread.start()
                time.sleep(0.5)
            self.voz_ativa = True
            self.btn_voz.configure(text="🔊  FALAR", fg_color=ORANGE)
            self.voz_status.configure(text="🟢 ATIVO", text_color="#4ade80")
            set_active(True)
        else:
            self.voz_ativa = False
            self.btn_voz.configure(text="🎤  Voz ON", fg_color=GREEN)
            self.voz_status.configure(text="⚫ INATIVO", text_color=TEXT_MUTED)
            set_active(False)

    def processar_voz(self, texto):
        if not self.voz_ativa:
            return
        print(f"[DEBUG] Voz: '{texto}'")
        self.after(0, self._processar_voz_ui, texto)

    def _processar_voz_ui(self, texto):
        self.exibir_mensagem("Você (voz)", texto)
        if self.voz_ativa:
            self.toggle_voz()
        resposta = self.command_processor.process(texto)
        self.exibir_mensagem("Chatbot", resposta)

    # ── Janelas secundárias ──────────────────────────────────────────────────
    def abrir_config_mqtt(self):
        from mqtt_handler import abrir_config_mqtt
        abrir_config_mqtt(self)
        self.after(1000, self._atualizar_status_mqtt)

    def mostrar_dispositivos(self):
        from devices_window import DevicesWindow
        DevicesWindow.mostrar_dispositivos(self)

    def _atualizar_status_mqtt(self):
        if _mqtt_handler._connected:
            self.mqtt_status.configure(text="🟢 MQTT", text_color="#4ade80")
        else:
            self.mqtt_status.configure(text="🔴 MQTT", text_color="#f87171")
        self.after(3000, self._atualizar_status_mqtt)

    def mostrar_ajuda(self):
        from help_window import mostrar_ajuda
        mostrar_ajuda(self, self.command_processor.commands)

    # ── Tema ─────────────────────────────────────────────────────────────────
    def toggle_tema(self):
        self._tema_escuro = not self._tema_escuro

        if self._tema_escuro:
            ctk.set_appearance_mode("dark")
            bg        = "#1a2332"
            darker    = "#141c28"
            card      = "#1e2d40"
            border    = "#243447"
            sep       = "#2a3a52"
            txt       = "#e8edf2"
            txt_muted = "#8a9bb0"
            hover_btn = "#2a3a52"
            self.btn_tema.configure(text="☀️  Tema claro")
        else:
            ctk.set_appearance_mode("light")
            bg        = "#f0f4f8"
            darker    = "#dce3ec"
            card      = "#ffffff"
            border    = "#c8d4de"
            sep       = "#d0dae6"
            txt       = "#1a2332"
            txt_muted = "#5a6a7a"
            hover_btn = "#d0dae6"
            self.btn_tema.configure(text="🌙  Tema escuro")

        # Re-colorir todos os frames/widgets com cores fixas
        self.configure(fg_color=bg)

        # Percorrer todos os widgets e actualizar os que têm fg_color definido
        def _recolor(widget):
            try:
                c = str(widget.cget("fg_color"))
                if c in ("#1a2332", "#f0f4f8"):
                    widget.configure(fg_color=bg)
                elif c in ("#141c28", "#dce3ec"):
                    widget.configure(fg_color=darker)
                elif c in ("#1e2d40", "#ffffff"):
                    widget.configure(fg_color=card)
                elif c in ("#243447", "#c8d4de"):
                    widget.configure(fg_color=border)
                elif c in ("#2a3a52", "#d0dae6"):
                    widget.configure(fg_color=sep)
                elif c == "transparent":
                    pass  # manter transparente
            except Exception:
                pass
            try:
                c = str(widget.cget("hover_color"))
                if c in ("#2a3a52", "#d0dae6"):
                    widget.configure(hover_color=sep)
                elif c in ("#3a4a62", "#c0cdd8"):
                    widget.configure(hover_color="#3a4a62" if self._tema_escuro else "#c0cdd8")
            except Exception:
                pass
            try:
                c = str(widget.cget("text_color"))
                if c in ("#e8edf2", "#1a2332"):
                    widget.configure(text_color=txt)
                elif c in ("#8a9bb0", "#5a6a7a"):
                    widget.configure(text_color=txt_muted)
            except Exception:
                pass
            try:
                c = str(widget.cget("border_color"))
                if c in ("#243447", "#c8d4de"):
                    widget.configure(border_color=border)
            except Exception:
                pass
            for child in widget.winfo_children():
                _recolor(child)

        _recolor(self)

    # ── Limpar chat ───────────────────────────────────────────────────────────
    def limpar_texto(self):
        self.txt_area.configure(state="normal")
        self.txt_area.delete("1.0", "end")
        self.txt_area.configure(state="disabled")

    # ── Callbacks do MusicPlayer ─────────────────────────────────────────────
    def _on_dl_status(self, text: str):
        if not text:
            try:
                self.pb.stop()
                self.pb.grid_forget()
                self.lbl_prog.grid_forget()
            except Exception:
                pass
            return
        if str(self.pb.cget("mode")) != "indeterminate":
            try:
                self.pb.configure(mode="indeterminate")
                self.pb.start()
            except Exception:
                pass
        self.lbl_prog.configure(text=text)
        self.lbl_prog.grid(row=1, column=0, padx=14, pady=(0, 2), sticky="ew")
        self.pb.grid(row=2, column=0, padx=14, pady=(0, 4), sticky="ew")

    def _on_dl_progress(self, pct, speed, eta):
        if pct is not None:
            try:
                if str(self.pb.cget("mode")) != "determinate":
                    self.pb.configure(mode="determinate")
                self.pb.set(max(0.0, min(1.0, pct / 100.0)))
            except Exception:
                pass
        bits = []
        if speed:
            try: bits.append(f"{int(speed/1024)} kB/s")
            except Exception: pass
        if eta:
            try: bits.append(f"ETA {int(eta)}s")
            except Exception: pass
        if bits:
            self.lbl_prog.configure(text=f"A descarregar... {' • '.join(bits)}")

    def _on_player_state(self, playing: bool):
        print(f"[PLAYER] {'tocando' if playing else 'parado'}")
        try:
            if playing:
                self.slider_volume.configure(state="normal")
                self.slider_progresso.configure(state="normal")
            else:
                self.slider_volume.configure(state="disabled")
                self.slider_progresso.configure(state="disabled")
                self.slider_progresso.set(0)
                self.lbl_progresso.configure(text="0:00")
                try:
                    self.pb.stop()
                    self.pb.grid_forget()
                    self.lbl_prog.grid_forget()
                except Exception:
                    pass
        except Exception:
            pass
