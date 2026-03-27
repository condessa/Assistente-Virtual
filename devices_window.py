"""
Janela de dispositivos MQTT com indicação de estado ON/OFF usando CTkTextbox
"""
import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
import threading
import time
import re
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
    _device_states = {}  # Dicionário para guardar estado dos dispositivos
    search_button = None
    auto_refresh = None
    selected_device = None
    
    @classmethod
    def mostrar_dispositivos(cls, parent=None, font_size=15):
        """Mostra janela de dispositivos (fonte aumentada)"""
        
        # Reusar janela se já existir
        if cls.win and cls.win.winfo_exists():
            cls.refresh()
            cls.win.lift()
            return

        # Cria janela
        win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
        cls.win = win
        win.title("Dispositivos MQTT")
        win.geometry("800x700")
        
        # Ícone
        try:
            if parent and hasattr(parent, 'iconbitmap'):
                win.iconbitmap(parent.iconbitmap())
        except Exception:
            pass

        # Fonte maior para todos os elementos
        cls.font = ctk.CTkFont(family="Segoe UI", size=font_size)
        title_font = ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        legend_font = ctk.CTkFont(family="Segoe UI", size=13)
        button_font = ctk.CTkFont(family="Segoe UI", size=14)

        # Frame principal
        main = ctk.CTkFrame(win)
        main.pack(padx=15, pady=15, fill="both", expand=True)

        # Título
        titulo = ctk.CTkLabel(
            main, 
            text="📱 Dispositivos MQTT", 
            font=title_font
        )
        titulo.pack(pady=(0, 5))

        # Info broker
        from mqtt_handler import _read_cfg
        host, port, _, _ = _read_cfg()
        broker_info = ctk.CTkLabel(
            main,
            text=f"Broker: {host}:{port}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        broker_info.pack()

        # Legenda de estados (com fontes maiores)
        legenda_frame = ctk.CTkFrame(main, fg_color="transparent")
        legenda_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            legenda_frame,
            text="🟢 Ligado",
            text_color="#2e7d32",
            font=legend_font
        ).pack(side="left", padx=8)
        
        ctk.CTkLabel(
            legenda_frame,
            text="⚪ Desligado",
            text_color="#757575",  # Cinza mais escuro
            font=legend_font
        ).pack(side="left", padx=8)
        
        ctk.CTkLabel(
            legenda_frame,
            text="⚫ Desconhecido",
            text_color="#9e9e9e",  # Cinza médio
            font=legend_font
        ).pack(side="left", padx=8)

        # Frame da lista
        frame_lista = ctk.CTkFrame(main)
        frame_lista.pack(fill="both", expand=True, padx=5, pady=10)

        # CTkTextbox para mostrar dispositivos com cores
        cls.textbox = ctk.CTkTextbox(
            frame_lista,
            font=cls.font,
            wrap="none",
            activate_scrollbars=True
        )
        cls.textbox.pack(fill="both", expand=True)
        
        # Configurar tags para cores (mais vivas)
        cls.textbox.tag_config("on", foreground="#2ecc71")  # Verde mais vivo
        cls.textbox.tag_config("off", foreground="#95a5a6")  # Cinza azulado
        cls.textbox.tag_config("unknown", foreground="#bdc3c7")  # Cinza claro
        cls.textbox.tag_config("selected", background="#3498db", foreground="#ffffff")  # Azul mais vivo
        
        # Bind de clique para seleção
        cls.textbox.bind("<Button-1>", cls._on_click)
        cls.textbox.bind("<Double-Button-1>", cls._on_double_click)

        # Frame de botões (primeira linha)
        btn_frame1 = ctk.CTkFrame(main)
        btn_frame1.pack(fill="x", pady=5)

        # Botões de controlo com fonte maior
        cls.btn_ligar = ctk.CTkButton(
            btn_frame1,
            text="🔛 LIGAR",
            command=lambda: cls._enviar_comando("ON"),
            fg_color="#27ae60",  # Verde mais vivo
            width=120,
            font=button_font,
            height=35
        )
        cls.btn_ligar.pack(side="left", padx=3, expand=True, fill="x")

        cls.btn_toggle = ctk.CTkButton(
            btn_frame1,
            text="🔄 TOGGLE",
            command=lambda: cls._enviar_comando("TOGGLE"),
            fg_color="#f39c12",  # Laranja
            width=120,
            font=button_font,
            height=35
        )
        cls.btn_toggle.pack(side="left", padx=3, expand=True, fill="x")

        cls.btn_desligar = ctk.CTkButton(
            btn_frame1,
            text="🔚 DESLIGAR",
            command=lambda: cls._enviar_comando("OFF"),
            fg_color="#c0392b",  # Vermelho mais vivo
            width=120,
            font=button_font,
            height=35
        )
        cls.btn_desligar.pack(side="left", padx=3, expand=True, fill="x")

        # Frame de botões (segunda linha)
        btn_frame2 = ctk.CTkFrame(main)
        btn_frame2.pack(fill="x", pady=5)

        cls.search_button = ctk.CTkButton(
            btn_frame2,
            text="🔍 Pesquisar Dispositivos",
            command=cls.pesquisar,
            fg_color="#2980b9",  # Azul
            width=150,
            font=button_font,
            height=35
        )
        cls.search_button.pack(side="left", padx=3, expand=True, fill="x")

        cls.btn_refresh = ctk.CTkButton(
            btn_frame2,
            text="🔄 Atualizar",
            command=cls.refresh,
            width=110,
            font=button_font,
            height=35
        )
        cls.btn_refresh.pack(side="left", padx=3, expand=True, fill="x")

        cls.btn_adicionar = ctk.CTkButton(
            btn_frame2,
            text="➕ Adicionar",
            command=lambda: cls.adicionar_manual(win),
            width=110,
            fg_color="#e67e22",  # Laranja
            font=button_font,
            height=35
        )
        cls.btn_adicionar.pack(side="left", padx=3, expand=True, fill="x")

        cls.btn_consultar = ctk.CTkButton(
            btn_frame2,
            text="🔍 Consultar Estado",
            command=lambda: cls._consultar_estado_selecionado(),
            width=140,
            fg_color="#8e44ad",  # Roxo
            font=button_font,
            height=35
        )
        cls.btn_consultar.pack(side="left", padx=3, expand=True, fill="x")

        cls.btn_fechar = ctk.CTkButton(
            btn_frame2,
            text="Fechar",
            command=win.destroy,
            fg_color="#7f8c8d",  # Cinza
            width=90,
            font=button_font,
            height=35
        )
        cls.btn_fechar.pack(side="right", padx=3)

        # Checkbox para auto-refresh
        auto_frame = ctk.CTkFrame(main, fg_color="transparent")
        auto_frame.pack(fill="x", pady=5)
        
        cls.auto_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            auto_frame,
            text="Atualizar automaticamente (a cada 5s)",
            variable=cls.auto_var,
            command=cls.toggle_auto_refresh,
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=5)
        
        # Status bar com fonte maior
        cls.status = ctk.CTkLabel(
            main, 
            text="", 
            anchor="w", 
            font=ctk.CTkFont(size=14)
        )
        cls.status.pack(fill="x", pady=5)

        # Subscreve a atualizações
        subscrever_dispositivos(cls._on_devices_updated)
        
        # Carrega dispositivos
        cls.refresh()
        
        # Consultar estado de todos os dispositivos após 1 segundo
        win.after(1000, cls._consultar_todos_estados)
        
        # Inicia auto-refresh
        cls.toggle_auto_refresh()

    @classmethod
    def _on_click(cls, event):
        """Handler para clique simples - seleciona o dispositivo"""
        # Obter a posição do clique
        index = cls.textbox.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        
        # Obter o texto da linha
        line_text = cls.textbox.get(f"{line}.0", f"{line}.end").strip()
        if line_text and not line_text.startswith("—"):
            # Remover ícone e espaços
            device = re.sub(r'[🟢⚪⚫]\s*', '', line_text).strip()
            cls.selected_device = device
            cls._highlight_line(line)

    @classmethod
    def _on_double_click(cls, event):
        """Handler para duplo clique - envia TOGGLE"""
        cls._enviar_comando("TOGGLE")

    @classmethod
    def _highlight_line(cls, line):
        """Destaca a linha selecionada"""
        # Limpar formatação anterior
        cls.textbox.tag_remove("selected", "1.0", "end")
        
        # Aplicar formatação à linha selecionada
        start = f"{line}.0"
        end = f"{line}.end"
        cls.textbox.tag_add("selected", start, end)

    @classmethod
    def _on_devices_updated(cls, devices):
        """Callback quando lista de dispositivos muda"""
        cls._devices = devices
        if cls.win and cls.win.winfo_exists():
            cls.win.after(0, cls.refresh)

    @classmethod
    def _atualizar_estado_dispositivo(cls, device: str, estado: str):
        """
        Atualiza o estado de um dispositivo (chamado pelo mqtt_handler)
        """
        if not device or not estado:
            return
        
        # Normalizar estado
        estado = estado.upper()
        if estado in ["ON", "OFF"]:
            cls._device_states[device] = estado
            print(f"[DEVICES] Estado atualizado: {device} = {estado}")
        
        # Atualizar display se a janela existir
        if cls.win and cls.win.winfo_exists():
            cls.win.after(0, cls.refresh)

    @classmethod
    def _consultar_estado_selecionado(cls):
        """Consulta o estado do dispositivo selecionado"""
        if not cls.selected_device:
            cls.set_status("⚠️ Selecione um dispositivo")
            return
        
        device = cls.selected_device
        cls.set_status(f"📤 A consultar estado de {device}...")
        
        # Enviar comando STATUS
        topic = f"cmnd/{device}/STATUS"
        enviar_mqtt(topic, "")
        
        # Também enviar POWER para obter resposta
        topic_power = f"cmnd/{device}/POWER"
        enviar_mqtt(topic_power, "")
        
        # Aguarda um pouco e atualiza
        cls.win.after(1500, cls.refresh)

    @classmethod
    def _consultar_todos_estados(cls):
        """Consulta o estado de todos os dispositivos"""
        devices = listar_dispositivos_ativos()
        if not devices:
            return
        
        print(f"[DEVICES] A consultar estado de {len(devices)} dispositivos...")
        for device in devices:
            # Enviar STATUS e POWER para garantir resposta
            topic_status = f"cmnd/{device}/STATUS"
            topic_power = f"cmnd/{device}/POWER"
            enviar_mqtt(topic_status, "")
            enviar_mqtt(topic_power, "")
            time.sleep(0.1)
        
        cls.set_status(f"📤 A consultar estados...")
        
        # Agendar refresh após receber respostas
        if cls.win and cls.win.winfo_exists():
            cls.win.after(2000, cls.refresh)

    @classmethod
    def _enviar_comando(cls, comando):
        """Envia comando para dispositivo selecionado"""
        if not cls.selected_device:
            cls.set_status("⚠️ Selecione um dispositivo")
            return
        
        device = cls.selected_device
        
        # Determina tópico (casos especiais)
        if device.lower() in ["porta", "portao", "portão"]:
            topic = f"cmnd/porta/POWER2"
        else:
            topic = f"cmnd/{device}/POWER"
        
        # Envia comando
        cls.set_status(f"📤 A enviar {comando} para {device}...")
        sucesso = enviar_mqtt(topic, comando)
        
        if sucesso:
            cls.set_status(f"✅ {comando} enviado para {device}")
            # Atualizar estado local (otimista)
            if comando in ["ON", "OFF"]:
                cls._device_states[device] = comando
                cls.refresh()
            # Aguarda um pouco e consulta estado real
            cls.win.after(1000, lambda: cls._consultar_estado_selecionado())
        else:
            cls.set_status(f"❌ Falha ao enviar para {device}")

    @classmethod
    def pesquisar(cls):
        """Pesquisa ativamente por dispositivos"""
        if cls.search_button:
            cls.search_button.configure(state="disabled", text="🔍 A pesquisar...")
        
        cls.set_status("🔍 A pesquisar dispositivos na rede...")
        
        def _pesquisar():
            devices = pesquisar_dispositivos(timeout=4.0)
            
            # Limpar estados anteriores
            cls._device_states.clear()
            
            # Consultar estado dos novos dispositivos
            for device in devices:
                topic_status = f"cmnd/{device}/STATUS"
                topic_power = f"cmnd/{device}/POWER"
                enviar_mqtt(topic_status, "")
                enviar_mqtt(topic_power, "")
                time.sleep(0.1)
            
            if cls.win and cls.win.winfo_exists():
                cls.win.after(2000, cls.refresh)
                if devices:
                    cls.win.after(0, lambda: cls.set_status(f"✅ Encontrados {len(devices)} dispositivo(s)"))
                else:
                    cls.win.after(0, lambda: cls.set_status("❌ Nenhum dispositivo encontrado"))
                cls.win.after(0, lambda: cls.search_button.configure(state="normal", text="🔍 Pesquisar Dispositivos"))
        
        threading.Thread(target=_pesquisar, daemon=True).start()

    @classmethod
    def adicionar_manual(cls, parent):
        """Janela para adicionar dispositivo manualmente"""
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
                    # Consultar estado
                    topic_status = f"cmnd/{nome}/STATUS"
                    topic_power = f"cmnd/{nome}/POWER"
                    enviar_mqtt(topic_status, "")
                    enviar_mqtt(topic_power, "")
                
                if cls.win and cls.win.winfo_exists():
                    if online:
                        cls.win.after(0, lambda: cls.set_status(f"✅ {nome} adicionado e online!"))
                    else:
                        cls.win.after(0, lambda: cls.set_status(f"⚠️ {nome} adicionado, mas sem resposta"))
                    cls.win.after(2000, cls.refresh)
            
            threading.Thread(target=_adicionar, daemon=True).start()

    @classmethod
    def refresh(cls):
        """Atualiza lista de dispositivos com estados coloridos"""
        if not cls.textbox:
            return
        
        # Limpar texto
        cls.textbox.delete("1.0", "end")
        
        devices = listar_dispositivos_ativos()
        
        if not devices:
            cls.textbox.insert("end", "— Nenhum dispositivo online —\n")
            cls.textbox.insert("end", "— Clique em 'Pesquisar' para procurar —\n")
            cls.set_status("0 dispositivos online")
        else:
            # Inserir dispositivos ordenados com cores vivas
            for d in sorted(devices):
                estado = cls._device_states.get(d, "UNKNOWN")
                
                if estado == "ON":
                    # Verde vivo para ligado
                    cls.textbox.insert("end", f"🟢 {d}\n", "on")
                elif estado == "OFF":
                    # Cinza para desligado
                    cls.textbox.insert("end", f"⚪ {d}\n", "off")
                else:
                    # Cinza claro para desconhecido
                    cls.textbox.insert("end", f"⚫ {d}\n", "unknown")
            
            # Reaplicar destaque se houver dispositivo selecionado
            if cls.selected_device:
                # Procurar a linha do dispositivo selecionado
                content = cls.textbox.get("1.0", "end").split('\n')
                for i, line in enumerate(content, 1):
                    if cls.selected_device in line:
                        cls._highlight_line(i)
                        break
            
            # Contar dispositivos por estado
            on_count = sum(1 for d in devices if cls._device_states.get(d) == "ON")
            off_count = sum(1 for d in devices if cls._device_states.get(d) == "OFF")
            unknown_count = len(devices) - on_count - off_count
            
            status_text = f"{len(devices)} dispositivo(s): 🟢 {on_count} ligado(s) | ⚪ {off_count} desligado(s)"
            if unknown_count > 0:
                status_text += f" | ⚫ {unknown_count} desconhecido(s)"
            
            cls.set_status(status_text)

    @classmethod
    def toggle_auto_refresh(cls):
        """Ativa/desativa atualização automática"""
        if hasattr(cls, 'auto_refresh') and cls.auto_refresh:
            cls.win.after_cancel(cls.auto_refresh)
            cls.auto_refresh = None
        
        if cls.auto_var.get():
            cls.auto_refresh = cls.win.after(5000, cls.auto_refresh_callback)

    @classmethod
    def auto_refresh_callback(cls):
        """Callback para auto-refresh"""
        if cls.win and cls.win.winfo_exists() and cls.auto_var.get():
            # Consultar estados novamente
            cls._consultar_todos_estados()
            cls.auto_refresh = cls.win.after(5000, cls.auto_refresh_callback)

    @classmethod
    def set_status(cls, texto):
        """Atualiza texto de status"""
        if cls.status:
            cls.status.configure(text=texto)
