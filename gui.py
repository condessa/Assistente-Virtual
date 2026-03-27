"""
Interface gráfica principal do Assistente Virtual
"""
import os
import threading
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from voice import voice_recognition, stop_voice, set_active, testar_microfone
from tts import falar
from music_player import MusicPlayer
from playlist_window import PlaylistWindow
from devices_window import DevicesWindow
from mqtt_handler import ensure_config_present, subscrever_dispositivos, _connected
from command_processor import CommandProcessor
from constants import IMAGES_DIR


class ChatbotGUI(ctk.CTk):
    """Janela principal do assistente"""
    
    def __init__(self):
        super().__init__()

        # Configuração da janela
        self.title("Assistente Virtual")
        self.geometry("900x520")
        self.minsize(820, 420)
        
        # Ícone
        try:
            ico_path = os.path.join(IMAGES_DIR, "chatbot.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

        # Estado
        self.voz_ativa = False
        self.music_player = MusicPlayer()
        self.voice_thread = None
        self.voice_running = False
        
        # Inicializa processador de comandos
        self.command_processor = CommandProcessor(self.music_player, self)
        self.music_player.set_gui(self)
        
        # Tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Subscreve a mudanças de tema
        self._theme_subscribers = []
        self._help_refs = None

        # Constrói UI
        self._build_gui()

        # Callbacks do MusicPlayer
        self.music_player.on_download_status = self._on_dl_status
        self.music_player.on_download_progress = self._on_dl_progress
        self.music_player.on_state_change = self._on_player_state

        # Slider começa desativado
        self.slider_volume.configure(state="disabled")

        # Garante configuração MQTT
        self.after(100, self._verificar_config_mqtt)
        
        # Subscreve a mudanças de dispositivos
        subscrever_dispositivos(self._on_devices_changed)
        
        # Mensagem de boas-vindas
        self.after(500, lambda: self.exibir_mensagem("Chatbot", 
            "Olá! Sou o teu assistente virtual. Podes digitar comandos ou ativar o modo voz."))
    
    def _verificar_config_mqtt(self):
        """Verifica se config MQTT existe"""
        if not ensure_config_present(self):
            self.exibir_mensagem("Chatbot", 
                "⚠️ Configuração MQTT não encontrada. Usa o botão ⚙️ MQTT para configurar.")
        else:
            self._atualizar_status_mqtt()
    
    def _on_devices_changed(self, devices):
        """Callback quando lista de dispositivos muda"""
        pass
    
    # ---------------- UI ----------------
    def _build_gui(self):
        """Constrói todos os elementos da interface"""

        # Área de histórico
        self.txt_area = ctk.CTkTextbox(self, wrap="word")
        self.txt_area.pack(padx=15, pady=(15, 5), fill="both", expand=True)
        self.txt_area.configure(state="disabled")

        # Entrada de comando
        self.entry_comando = ctk.CTkEntry(
            self,
            placeholder_text="Digite um comando ou clique em '🎤 Voz ON'..."
        )
        self.entry_comando.pack(padx=15, pady=(0, 4), fill="x")
        self.entry_comando.bind("<Return>", lambda e: self.enviar_comando())

        # Barra de progresso (download) — oculta por defeito
        self.lbl_prog = ctk.CTkLabel(self, text="", anchor="w")
        self.pb = ctk.CTkProgressBar(self)
        self.pb.set(0)
        self.lbl_prog.pack_forget()
        self.pb.pack_forget()

        # ── Barra inferior ───────────────────────────────────────────────────
        frame_inferior = ctk.CTkFrame(self)
        frame_inferior.pack(padx=10, pady=(0, 10), fill="x")

        # ── Linha 0: botões de ação ──────────────────────────────────────────
        frame_botoes = ctk.CTkFrame(frame_inferior, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=5, pady=(6, 2))

        self.btn_enviar = ctk.CTkButton(
            frame_botoes, text="📤 Enviar", command=self.enviar_comando
        )
        self.btn_enviar.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_voz = ctk.CTkButton(
            frame_botoes, text="🎤 Voz ON", command=self.toggle_voz,
            fg_color="#2e7d32"
        )
        self.btn_voz.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_parar = ctk.CTkButton(
            frame_botoes, text="⏹️ Parar",
            command=self.parar_musica,
            fg_color="#b71c1c"
        )
        self.btn_parar.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_testar_voz = ctk.CTkButton(
            frame_botoes, text="🎤 Testar", command=self.testar_microfone,
            fg_color="#1f6aa5"
        )
        self.btn_testar_voz.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_ajuda = ctk.CTkButton(
            frame_botoes, text="❓ Ajuda", command=self.mostrar_ajuda
        )
        self.btn_ajuda.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_config = ctk.CTkButton(
            frame_botoes, text="⚙️ MQTT", command=self.abrir_config_mqtt
        )
        self.btn_config.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_dispositivos = ctk.CTkButton(
            frame_botoes, text="📱 Dispositivos",
            command=self.mostrar_dispositivos, fg_color="#ff6d00"
        )
        self.btn_dispositivos.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_limpar = ctk.CTkButton(
            frame_botoes, text="🧹 Limpar", command=self.limpar_texto
        )
        self.btn_limpar.pack(side="left", padx=4, expand=True, fill="x")

        self.btn_sair = ctk.CTkButton(
            frame_botoes, text="🚪 Sair", fg_color="#d32f2f", command=self.quit
        )
        self.btn_sair.pack(side="left", padx=4, expand=True, fill="x")

        # ── Linha 1: tema + volume + status ─────────────────────────────────
        frame_linha2 = ctk.CTkFrame(frame_inferior, fg_color="transparent")
        frame_linha2.pack(fill="x", padx=8, pady=(2, 6))

        # — Tema —
        ctk.CTkLabel(
            frame_linha2, text="Tema:", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 4))

        self._tema_escuro = True
        # Texto indica a ação (para onde vai), não o estado atual
        # Tema escuro ativo → botão mostra "☀️ Mudar para Claro"
        self.btn_tema = ctk.CTkButton(
            frame_linha2,
            text="☀️ Mudar para Claro",
            width=150,
            fg_color="#37474f",
            command=self.toggle_tema,
        )
        self.btn_tema.pack(side="left", padx=(0, 12))

        # separador
        ctk.CTkFrame(frame_linha2, width=2, height=22, fg_color="#555555").pack(
            side="left", padx=(0, 12)
        )

        # — Volume —
        ctk.CTkLabel(
            frame_linha2, text="🔊 Volume:", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 6))

        self.slider_volume = ctk.CTkSlider(
            frame_linha2, from_=0, to=100, width=200,
            command=self.ajustar_volume
        )
        self.slider_volume.set(50)
        self.slider_volume.pack(side="left", padx=(0, 6))

        self.lbl_volume_val = ctk.CTkLabel(
            frame_linha2, text="50%",
            font=ctk.CTkFont(size=12, weight="bold"), width=38, anchor="w"
        )
        self.lbl_volume_val.pack(side="left", padx=(0, 12))

        # separador
        ctk.CTkFrame(frame_linha2, width=2, height=22, fg_color="#555555").pack(
            side="left", padx=(0, 12)
        )

        # — Indicadores de estado —
        self.mqtt_status = ctk.CTkLabel(
            frame_linha2, text="● MQTT",
            font=ctk.CTkFont(size=12), text_color="#666666"
        )
        self.mqtt_status.pack(side="left", padx=(0, 10))

        self.voz_status = ctk.CTkLabel(
            frame_linha2, text="● Voz",
            font=ctk.CTkFont(size=12), text_color="#666666"
        )
        self.voz_status.pack(side="left")

    # ----------- Handlers UI -----------
    def ajustar_volume(self, valor):
        """Ajusta volume pelo slider"""
        v = int(float(valor))
        # Atualiza label sempre, mesmo com música parada (para feedback visual)
        try:
            self.lbl_volume_val.configure(text=f"{v}%")
        except Exception:
            pass
        if str(self.slider_volume.cget("state")).lower() != "disabled":
            self.music_player.controlar_volume(v)

    def enviar_comando(self):
        """Envia comando digitado"""
        comando = self.entry_comando.get().strip()
        if not comando:
            return
            
        print(f"[DEBUG] Comando: '{comando}'")
        
        self.exibir_mensagem("Você", comando)
        resposta = self.command_processor.process(comando)
        self.exibir_mensagem("Chatbot", resposta)
        self.entry_comando.delete(0, "end")

    # No gui.py, modificar a função exibir_mensagem:

    def exibir_mensagem(self, remetente, mensagem):
        """Adiciona mensagem ao histórico - SEM ÁUDIO durante modo voz"""
        self.txt_area.configure(state="normal")
        self.txt_area.insert("end", f"{remetente}: {mensagem}\n")
        self.txt_area.configure(state="disabled")
        self.txt_area.see("end")
        
        # NÃO reproduz áudio durante modo voz para evitar eco
        if remetente.lower() == "chatbot" and not self.voz_ativa:
            try:
                falar(mensagem)
            except:
                pass
                
    def parar_musica(self):
        """Para a música que está a tocar"""
        resultado = self.music_player.parar_musica()
        self.exibir_mensagem("Chatbot", resultado)

    def testar_microfone(self):
        """Testa o funcionamento do microfone"""
        self.exibir_mensagem("Chatbot", "🎤 A testar microfone... diz 'teste'!")
        
        def _test():
            resultado = testar_microfone()
            if resultado:
                self.after(0, lambda: self.exibir_mensagem("Chatbot", "✅ Microfone OK!"))
            else:
                self.after(0, lambda: self.exibir_mensagem("Chatbot", "❌ Problema no microfone!"))
        
        threading.Thread(target=_test, daemon=True).start()

# No gui.py, substitui a função toggle_voz por esta:

    def toggle_voz(self):
        """Ativa/desativa modo de voz - SEM FEEDBACK DE ÁUDIO"""
        if not self.voz_ativa:
            # Iniciar thread se necessário
            if not self.voice_running:
                self.voice_running = True
                self.voice_thread = threading.Thread(
                    target=lambda: voice_recognition(self.processar_voz),
                    daemon=True
                )
                self.voice_thread.start()
                time.sleep(0.5)
            
            self.voz_ativa = True
            self.btn_voz.configure(
                text="🔊 FALAR",
                fg_color="#b71c1c"
            )
            self.voz_status.configure(text="🟢 ATIVO", text_color="#2e7d32")
            set_active(True)
            # NÃO mostrar mensagem de feedback
            
        else:
            self.voz_ativa = False
            self.btn_voz.configure(
                text="🎤 VOZ",
                fg_color="#2e7d32"
            )
            self.voz_status.configure(text="⚫ INATIVO", text_color="#666666")
            set_active(False)
        
    def processar_voz(self, texto):
        """Processa comando vindo da voz"""
        if not self.voz_ativa:
            return
            
        print(f"[DEBUG] Voz recebida: '{texto}'")
        
        # Atualiza UI na thread principal
        self.after(0, self._processar_voz_ui, texto)
    
    def _processar_voz_ui(self, texto):
        """Processa voz na thread principal"""
        self.exibir_mensagem("Você (voz)", texto)
        resposta = self.command_processor.process(texto)
        self.exibir_mensagem("Chatbot", resposta)
        
        # Após processar, desativa automaticamente o microfone
        if self.voz_ativa:
            self.after(100, self.toggle_voz)

    # ----------- Janelas -----------
    def abrir_config_mqtt(self):
        """Abre janela de configuração MQTT"""
        from mqtt_handler import abrir_config_mqtt
        abrir_config_mqtt(self)
        self.after(1000, self._atualizar_status_mqtt)
    
    def mostrar_dispositivos(self):
        """Abre janela de dispositivos"""
        from devices_window import DevicesWindow
        DevicesWindow.mostrar_dispositivos(self)
    
    def _atualizar_status_mqtt(self):
        """Atualiza indicador visual do MQTT"""
        if _connected:
            self.mqtt_status.configure(text="🟢 MQTT", text_color="#2e7d32")
        else:
            self.mqtt_status.configure(text="🔴 MQTT", text_color="#b71c1c")

    def mostrar_ajuda(self):
        """Mostra janela de ajuda"""
        from help_window import mostrar_ajuda
        mostrar_ajuda(self, self.command_processor.commands)

    def toggle_tema(self):
        """Alterna entre tema claro/escuro"""
        self._tema_escuro = not self._tema_escuro
        if self._tema_escuro:
            # Passou para escuro → botão oferece voltar ao claro
            ctk.set_appearance_mode("dark")
            self.btn_tema.configure(text="☀️ Mudar para Claro", fg_color="#37474f")
        else:
            # Passou para claro → botão oferece voltar ao escuro
            ctk.set_appearance_mode("light")
            self.btn_tema.configure(text="🌙 Mudar para Escuro", fg_color="#546e7a")

    def limpar_texto(self):
        """Limpa histórico de mensagens"""
        self.txt_area.configure(state="normal")
        self.txt_area.delete("1.0", "end")
        self.txt_area.configure(state="disabled")
    
    # ----------- Callbacks do MusicPlayer -----------
    def _on_dl_status(self, text: str):
        """Callback para status do download"""
        if not text:
            try:
                self.pb.stop()
                self.pb.pack_forget()
                self.lbl_prog.pack_forget()
            except:
                pass
            return
            
        if str(self.pb.cget("mode")) != "indeterminate":
            try:
                self.pb.configure(mode="indeterminate")
                self.pb.start()
            except:
                pass
                
        self.lbl_prog.configure(text=text)
        self.lbl_prog.pack(padx=15, pady=(0, 0), fill="x")
        self.pb.pack(padx=15, pady=(2, 6), fill="x")

    def _on_dl_progress(self, pct: float | None, speed: float | None, eta: float | None):
        """Callback para progresso do download"""
        if pct is not None:
            try:
                if str(self.pb.cget("mode")) != "determinate":
                    self.pb.configure(mode="determinate")
                self.pb.set(max(0.0, min(1.0, pct/100.0)))
            except:
                pass
        
        bits = []
        if speed:
            try:
                bits.append(f"{int(speed/1024)} kB/s")
            except:
                pass
        if eta:
            try:
                bits.append(f"ETA {int(eta)}s")
            except:
                pass
        
        if bits:
            self.lbl_prog.configure(text=f"A descarregar... {' • '.join(bits)}")

    def _on_player_state(self, playing: bool):
        """Callback para mudança de estado do player"""
        print(f"[PLAYER] Estado: {'tocando' if playing else 'parado'}")
        try:
            if playing:
                self.slider_volume.configure(state="normal")
            else:
                self.slider_volume.configure(state="disabled")
                try:
                    self.pb.stop()
                    self.pb.pack_forget()
                    self.lbl_prog.pack_forget()
                except:
                    pass
        except:
            pass
