"""
Janela de dispositivos MQTT com indicação de estado ON/OFF usando CTkTextbox
"""
import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
import threading
import time
import re
from tts import falar
from tooltip import Tooltip

# Referência à janela principal — definida pelo gui.py ao iniciar
_gui_ref = None

def set_gui_ref(gui):
    """Guarda referência à GUI principal para verificar silêncio"""
    global _gui_ref
    _gui_ref = gui

def _falar_se_ativo(texto: str):
    """Fala apenas se o TTS não estiver silenciado na GUI"""
    if _gui_ref is not None and getattr(_gui_ref, 'tts_silenciado', False):
        return
    falar(texto, bloquear=False)

import json

from mqtt_handler import (
    listar_dispositivos_ativos,
    enviar_mqtt,
    subscrever_dispositivos,
    pesquisar_dispositivos,
    adicionar_dispositivo_manual
)


class DevicesWindow:
    """Janela para mostrar e controlar dispositivos MQTT com estado"""

    win = None
    textbox = None
    font = None
    status = None
    _devices = []
    _device_states = {}
    _aguardar_confirmacao = None
    search_button = None
    auto_refresh = None
    selected_device = None

    @classmethod
    def mostrar_dispositivos(cls, parent=None, font_size=12):
        """Mostra janela de dispositivos"""

        if cls.win and cls.win.winfo_exists():
            cls.refresh()
            cls.win.lift()
            return

        win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
        cls.win = win
        win.title("Dispositivos MQTT")
        win.geometry("400x520")

        try:
            if parent and hasattr(parent, 'iconbitmap'):
                win.iconbitmap(parent.iconbitmap())
        except Exception:
            pass

        # ── Fontes reduzidas ────────────────────────────────────────────────
        cls.font    = ctk.CTkFont(family="Segoe UI", size=font_size)
        title_font  = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        legend_font = ctk.CTkFont(family="Segoe UI", size=11)
        button_font = ctk.CTkFont(family="Segoe UI", size=11)
        status_font = ctk.CTkFont(size=11)

        # Frame principal
        main = ctk.CTkFrame(win)
        main.pack(padx=12, pady=12, fill="both", expand=True)

        # Título
        ctk.CTkLabel(
            main,
            text="📱 Dispositivos MQTT",
            font=title_font
        ).pack(pady=(0, 4))

        # Info broker
        from mqtt_handler import _read_cfg
        host, port, _, _ = _read_cfg()
        ctk.CTkLabel(
            main,
            text=f"Broker: {host}:{port}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack()

        # Legenda de estados
        legenda_frame = ctk.CTkFrame(main, fg_color="transparent")
        legenda_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            legenda_frame, text="🟢 Ligado",
            text_color="#2e7d32", font=legend_font
        ).pack(side="left", padx=6)

        ctk.CTkLabel(
            legenda_frame, text="🔴 Desligado",
            text_color="#c0392b", font=legend_font
        ).pack(side="left", padx=6)

        ctk.CTkLabel(
            legenda_frame, text="⚫ Desconhecido",
            text_color="#7f8c8d", font=legend_font
        ).pack(side="left", padx=6)

        # Lista de dispositivos
        frame_lista = ctk.CTkFrame(main)
        frame_lista.pack(fill="both", expand=True, padx=4, pady=6)

        cls.textbox = ctk.CTkTextbox(
            frame_lista,
            font=cls.font,
            wrap="none",
            activate_scrollbars=True,
            cursor="arrow"
        )
        cls.textbox.pack(fill="both", expand=True)

        cls.textbox.tag_config("icon_on",      foreground="#2ecc71")
        cls.textbox.tag_config("icon_off",     foreground="#e74c3c")
        cls.textbox.tag_config("icon_unknown", foreground="#7f8c8d")
        cls.textbox.tag_config("selected",     background="#3498db", foreground="#ffffff")

        cls.textbox.bind("<Button-1>",        cls._on_click)
        cls.textbox.bind("<Double-Button-1>", cls._on_double_click)

        # Botões de controlo — mais compactos
        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(fill="x", pady=(4, 2))

        cls.btn_ligar = ctk.CTkButton(
            btn_frame, text="🔛 Ligar",
            command=lambda: cls._enviar_comando("ON"),
            fg_color="#27ae60", width=70, font=button_font, height=26
        )
        cls.btn_ligar.pack(side="left", padx=2, expand=True, fill="x")

        cls.btn_toggle = ctk.CTkButton(
            btn_frame, text="🔄 Toggle",
            command=lambda: cls._enviar_comando("TOGGLE"),
            fg_color="#f39c12", width=70, font=button_font, height=26
        )
        cls.btn_toggle.pack(side="left", padx=2, expand=True, fill="x")

        cls.btn_desligar = ctk.CTkButton(
            btn_frame, text="🔚 Desligar",
            command=lambda: cls._enviar_comando("OFF"),
            fg_color="#c0392b", width=70, font=button_font, height=26
        )
        cls.btn_desligar.pack(side="left", padx=2, expand=True, fill="x")

        cls.btn_fechar = ctk.CTkButton(
            btn_frame, text="✖ Fechar",
            command=win.destroy,
            fg_color="#7f8c8d", width=70, font=button_font, height=26
        )
        cls.btn_fechar.pack(side="left", padx=2, expand=True, fill="x")

        # Tooltips
        Tooltip(cls.btn_ligar,    "Ligar o dispositivo selecionado")
        Tooltip(cls.btn_toggle,   "Inverter o estado do dispositivo")
        Tooltip(cls.btn_desligar, "Desligar o dispositivo selecionado")
        Tooltip(cls.btn_fechar,   "Fechar esta janela")

        # Auto-refresh
        auto_frame = ctk.CTkFrame(main, fg_color="transparent")
        auto_frame.pack(fill="x", pady=4)

        cls.auto_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            auto_frame,
            text="Atualizar automaticamente (a cada 5s)",
            variable=cls.auto_var,
            command=cls.toggle_auto_refresh,
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=4)

        # Status bar
        cls.status = ctk.CTkLabel(
            main, text="", anchor="w", font=status_font
        )
        cls.status.pack(fill="x", pady=3)

        # Inicia
        subscrever_dispositivos(cls._on_devices_updated)
        cls.refresh()
        win.after(1000, cls._consultar_todos_estados)
        cls.toggle_auto_refresh()

        # Centralizar relativamente ao parent (ou ao ecrã se não houver)
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

    # ── Handlers de clique ───────────────────────────────────────────────────

    @classmethod
    def _on_click(cls, event):
        index = cls.textbox.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        line_text = cls.textbox.get(f"{line}.0", f"{line}.end").strip()
        if line_text and not line_text.startswith("—"):
            device = re.sub(r'[🟢🔴⚪⚫]\s*', '', line_text).strip()
            cls.selected_device = device
            cls._highlight_line(line)

    @classmethod
    def _on_double_click(cls, event):
        cls._enviar_comando("TOGGLE")

    @classmethod
    def _highlight_line(cls, line):
        cls.textbox.tag_remove("selected", "1.0", "end")
        cls.textbox.tag_add("selected", f"{line}.0", f"{line}.end")

    # ── Callbacks ────────────────────────────────────────────────────────────

    @classmethod
    def _on_devices_updated(cls, devices):
        cls._devices = devices
        if cls.win and cls.win.winfo_exists():
            cls.win.after(0, cls.refresh)

    @classmethod
    def _atualizar_estado_dispositivo(cls, device: str, estado: str):
        if not device or not estado:
            return
        estado = estado.upper()
        if estado in ["ON", "OFF"]:
            cls._device_states[device] = estado
            print(f"[DEVICES] Estado: {device} = {estado}")
            if cls._aguardar_confirmacao == device:
                cls._aguardar_confirmacao = None
                msg = f"{device} {'ligado' if estado == 'ON' else 'desligado'}."
                threading.Thread(target=lambda: _falar_se_ativo(msg), daemon=True).start()
        if cls.win and cls.win.winfo_exists():
            cls.win.after(0, cls.refresh)

    @classmethod
    def _consultar_estado_selecionado(cls):
        if not cls.selected_device:
            cls.set_status("⚠️ Selecione um dispositivo")
            return
        device = cls.selected_device
        cls.set_status(f"📤 A consultar {device}...")
        enviar_mqtt(f"cmnd/{device}/STATUS", "")
        enviar_mqtt(f"cmnd/{device}/POWER", "")
        cls.win.after(1500, cls.refresh)

    @classmethod
    def _consultar_todos_estados(cls):
        devices = listar_dispositivos_ativos()
        if not devices:
            return
        for device in devices:
            enviar_mqtt(f"cmnd/{device}/STATUS", "")
            enviar_mqtt(f"cmnd/{device}/POWER", "")
            time.sleep(0.1)
        cls.set_status("📤 A consultar estados...")
        if cls.win and cls.win.winfo_exists():
            cls.win.after(2000, cls.refresh)

    @classmethod
    def _enviar_comando(cls, comando):
        if not cls.selected_device:
            cls.set_status("⚠️ Selecione um dispositivo")
            return
        device = cls.selected_device
        if device.lower() in ["porta", "portao", "portão"]:
            topic = "cmnd/porta/POWER2"
        else:
            topic = f"cmnd/{device}/POWER"
        cls.set_status(f"📤 A enviar {comando} para {device}...")
        sucesso = enviar_mqtt(topic, comando)
        if sucesso:
            cls.set_status(f"✅ {comando} enviado para {device}")
            if comando == "ON":
                threading.Thread(
                    target=lambda: _falar_se_ativo(f"{device} ligado."), daemon=True).start()
            elif comando == "OFF":
                threading.Thread(
                    target=lambda: _falar_se_ativo(f"{device} desligado."), daemon=True).start()
            elif comando == "TOGGLE":
                cls._aguardar_confirmacao = device
            cls.win.after(1000, cls._consultar_estado_selecionado)
        else:
            cls.set_status(f"❌ Falha ao enviar para {device}")

    @classmethod
    def pesquisar(cls):
        if cls.search_button:
            cls.search_button.configure(state="disabled", text="🔍 A pesquisar...")
        cls.set_status("🔍 A pesquisar dispositivos...")

        def _pesquisar():
            from mqtt_handler import _online_devices, _known_devices, _client, _connected
            if _client and _connected:
                _client.publish("cmnd/tasmotas/STATUS", "0")
                _client.publish("cmnd/tasmotas/POWER", "")
            todos = sorted(_online_devices | _known_devices)
            todos = [d for d in todos if d and len(d) > 1]
            for device in todos:
                enviar_mqtt(f"cmnd/{device}/POWER", "")
                time.sleep(0.05)
            time.sleep(3)
            devices = listar_dispositivos_ativos()
            if cls.win and cls.win.winfo_exists():
                cls.win.after(0, cls.refresh)
                msg = f"✅ {len(devices)} dispositivo(s)" if devices else "⚠️ Nenhum online"
                cls.win.after(0, lambda: cls.set_status(msg))
                if cls.search_button:
                    cls.win.after(0, lambda: cls.search_button.configure(
                        state="normal", text="🔍 Pesquisar"))

        threading.Thread(target=_pesquisar, daemon=True).start()

    @classmethod
    def adicionar_manual(cls, parent):
        dialog = ctk.CTkInputDialog(
            text="Nome do dispositivo (ex: luz_sala):",
            title="Adicionar Dispositivo"
        )
        nome = dialog.get_input()
        if nome:
            cls.set_status(f"📤 A contactar {nome}...")

            def _adicionar():
                online = adicionar_dispositivo_manual(nome)
                if online:
                    enviar_mqtt(f"cmnd/{nome}/STATUS", "")
                    enviar_mqtt(f"cmnd/{nome}/POWER", "")
                if cls.win and cls.win.winfo_exists():
                    msg = f"✅ {nome} adicionado!" if online else f"⚠️ {nome} sem resposta"
                    cls.win.after(0, lambda: cls.set_status(msg))
                    cls.win.after(2000, cls.refresh)

            threading.Thread(target=_adicionar, daemon=True).start()

    # ── Refresh e auto-refresh ───────────────────────────────────────────────

    @classmethod
    def refresh(cls):
        if not cls.textbox:
            return
        cls.textbox.delete("1.0", "end")
        devices = listar_dispositivos_ativos()
        if not devices:
            cls.textbox.insert("end", "— Nenhum dispositivo online —\n")
            cls.textbox.insert("end", "— Clique em 'Pesquisar' para procurar —\n")
            cls.set_status("0 dispositivos online")
        else:
            for d in sorted(devices):
                estado = cls._device_states.get(d, "UNKNOWN")
                if estado == "ON":
                    cls.textbox.insert("end", "🟢 ", "icon_on")
                elif estado == "OFF":
                    cls.textbox.insert("end", "🔴 ", "icon_off")
                else:
                    cls.textbox.insert("end", "⚫ ", "icon_unknown")
                cls.textbox.insert("end", f"{d}\n")

            if cls.selected_device:
                lines = cls.textbox.get("1.0", "end").split('\n')
                for i, line in enumerate(lines, 1):
                    if cls.selected_device in line:
                        cls._highlight_line(i)
                        break

            cls.set_status(f"{len(devices)} dispositivo(s) detetado(s)")

    @classmethod
    def toggle_auto_refresh(cls):
        if hasattr(cls, 'auto_refresh') and cls.auto_refresh:
            cls.win.after_cancel(cls.auto_refresh)
            cls.auto_refresh = None
        if cls.auto_var.get():
            cls.auto_refresh = cls.win.after(5000, cls.auto_refresh_callback)

    @classmethod
    def auto_refresh_callback(cls):
        if cls.win and cls.win.winfo_exists() and cls.auto_var.get():
            cls._consultar_todos_estados()
            cls.auto_refresh = cls.win.after(5000, cls.auto_refresh_callback)

    @classmethod
    def set_status(cls, texto):
        if cls.status:
            cls.status.configure(text=texto)
