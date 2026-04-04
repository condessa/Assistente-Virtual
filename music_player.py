"""
Player de música com pygame e yt-dlp
"""
import os
import sys
import time
import re
import threading
import pygame
from typing import Callable, Optional, List, Dict
import tkinter as tk
import customtkinter as ctk
from difflib import SequenceMatcher

from constants import DOWNLOAD_DIR, resource_path, FFMPEG_DIR


# Configurar ffmpeg local
def _setup_ffmpeg():
    """Configura o caminho do ffmpeg local"""
    if FFMPEG_DIR and os.path.exists(FFMPEG_DIR):
        ffmpeg = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
        ffprobe = os.path.join(FFMPEG_DIR, "ffprobe.exe")
        
        if os.path.exists(ffmpeg):
            try:
                from pydub import AudioSegment
                AudioSegment.converter = ffmpeg
                if os.path.exists(ffprobe):
                    AudioSegment.ffprobe = ffprobe
                print(f"✅ FFmpeg configurado: {ffmpeg}")
            except ImportError:
                pass
            
            # Adiciona ao PATH
            os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
            return True
    return False


# Inicializa mixer pygame
def init_mixer():
    """Inicializa o mixer do pygame"""
    try:
        pygame.mixer.quit()
        time.sleep(0.1)
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.init()
        # Garantir canais suficientes para TTS (canal 7) + música
        pygame.mixer.set_num_channels(8)
        print(f"✅ Mixer inicializado - Frequência: {pygame.mixer.get_init()[0]} Hz")
        return True
    except Exception as e:
        print(f"⚠️ Erro no mixer: {e}")
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            print("✅ Mixer inicializado (config padrão)")
            return True
        except:
            return False

init_mixer()


class SelecaoMusicaDialog:
    """Diálogo para selecionar múltiplas músicas quando não há correspondência exata"""
    
    def __init__(self, parent, termo_pesquisa, resultados, callback):
        self.parent = parent
        self.termo = termo_pesquisa
        self.resultados = resultados
        self.callback = callback
        self.selecao = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Escolha uma versão")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        # Sem grab_set() — evita bloquear a janela principal se ocorrer erro
        
        # Centralizar
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Frame principal
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        ctk.CTkLabel(
            main_frame,
            text=f"🎵 Múltiplas versões encontradas para:",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(10, 0))
        
        ctk.CTkLabel(
            main_frame,
            text=f"'{termo_pesquisa}'",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 10))
        
        ctk.CTkLabel(
            main_frame,
            text="Escolhe a versão que pretendes:",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 5))
        
        # Frame para a lista com scrollbar
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Listbox simples
        self.listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 11),
            selectmode=tk.SINGLE,
            activestyle="dotbox",
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff",
            fg="#ffffff" if ctk.get_appearance_mode() == "Dark" else "#000000",
            selectbackground="#1f6aa5",
            selectforeground="#ffffff"
        )
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Preencher resultados
        for i, r in enumerate(self.resultados):
            titulo = r.get('title', 'Desconhecido')
            artista = r.get('artist', r.get('channel', 'Desconhecido'))
            duracao = r.get('duration', 0)
            
            if duracao:
                minutos = duracao // 60
                segundos = duracao % 60
                duracao_str = f"{minutos}:{segundos:02d}"
            else:
                duracao_str = "--:--"
            
            item_text = f"{titulo} - {artista} [{duracao_str}]"
            self.listbox.insert(tk.END, item_text)
        
        # Frame para botões
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="▶️ Tocar selecionada",
            command=self.tocar_selecionada,
            fg_color="#2e7d32",
            width=200
        ).pack(side="left", padx=5, expand=True)
        
        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self._fechar,
            fg_color="#666666",
            width=100
        ).pack(side="right", padx=5)
        
        # Fechar com X também liberta corretamente
        self.dialog.protocol("WM_DELETE_WINDOW", self._fechar)
        
        # Duplo clique toca
        self.listbox.bind("<Double-Button-1>", lambda e: self.tocar_selecionada())
    
    def _fechar(self):
        """Fecha o diálogo libertando recursos"""
        try:
            self.dialog.destroy()
        except Exception:
            pass

    def tocar_selecionada(self):
        """Toca a música selecionada"""
        selecao = self.listbox.curselection()
        if not selecao:
            return
        
        idx = selecao[0]
        if 0 <= idx < len(self.resultados):
            self.selecao = self.resultados[idx]
            selecao_copy = self.selecao
            self._fechar()
            if self.callback:
                self.callback(selecao_copy)


class MusicPlayer:
    """Player de música com suporte a download do YouTube"""
    
    def __init__(self):
        self.tocando: bool = False
        self.musica_atual: Optional[str] = None
        self.volume: float = 0.5
        self.pausado: bool = False
        self.gui = None  # Referência à GUI para mostrar diálogos
        self._indice_atual: int = -1  # posição na playlist local
        self._pos_segundos: float = 0.0   # posição atual em segundos
        self._duracao: float = 0.0        # duração total em segundos
        self._seek_pendente: Optional[float] = None  # seek pedido pelo slider
        self.on_progress: Optional[Callable[[float, float], None]] = None  # (pos, dur)
        
        # Callbacks para a UI
        self.on_state_change: Optional[Callable[[bool], None]] = None
        self.on_download_progress: Optional[Callable[[Optional[float], Optional[float], Optional[float]], None]] = None
        self.on_download_status: Optional[Callable[[str], None]] = None
        self.on_chat_message: Optional[Callable[[str], None]] = None  # mensagens para o chat
        
        # Configura volume inicial
        try:
            pygame.mixer.music.set_volume(self.volume)
        except:
            pass
        
        # Configura ffmpeg
        _setup_ffmpeg()
        
        # Criar pasta de downloads se não existir
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    def set_gui(self, gui):
        """Define a referência à GUI principal"""
        self.gui = gui
    
    def _notify_state(self, is_playing: bool):
        """Notifica mudança de estado de reprodução"""
        if self.on_state_change:
            try:
                self.on_state_change(is_playing)
            except Exception:
                pass
    
    def get_playlist(self) -> List[str]:
        """Retorna lista de músicas na pasta Download"""
        if not os.path.isdir(DOWNLOAD_DIR):
            return []
        try:
            files = [f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith(".mp3")]
            files.sort(key=str.lower)
            return files
        except:
            return []
    
    def _normalizar_nome(self, termo: str) -> str:
        """Normaliza o nome da música para usar como nome de ficheiro"""
        nome = re.sub(r'[^\w\s-]', '', termo.lower().strip())
        nome = re.sub(r'\s+', '_', nome)
        if len(nome) > 100:
            nome = nome[:100]
        return nome + ".mp3"
    
    def _extrair_artista_titulo(self, termo: str) -> tuple:
        """
        Extrai artista e título do termo de busca
        Retorna (titulo, artista)
        """
        # Padrões comuns: "titulo - artista" ou "artista - titulo"
        padroes = [
            r'^(.*?)\s*[-–—]\s*(.*)$',  # titulo - artista
            r'^(.*?)\s*por\s*(.*)$',     # titulo por artista
            r'^(.*?)\s*de\s*(.*)$',      # titulo de artista
        ]
        
        for padrao in padroes:
            match = re.match(padrao, termo, re.IGNORECASE)
            if match:
                parte1, parte2 = match.groups()
                return parte1.strip(), parte2.strip()
        
        # Se não encontrar padrão, retorna o termo completo como título
        return termo, None
    
    def _calcular_similaridade(self, a: str, b: str) -> float:
        """Calcula a similaridade entre duas strings (0-1)"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def _procurar_na_playlist(self, termo: str) -> Optional[str]:
        """
        Procura uma música na pasta Download que corresponda ao termo
        """
        titulo, artista = self._extrair_artista_titulo(termo)
        print(f"[DEBUG] A procurar: título='{titulo}', artista='{artista}'")
        
        musicas = self.get_playlist()
        melhores_correspondencias = []
        
        for musica in musicas:
            musica_lower = musica.lower()
            pontuacao = 0
            similaridade = 0
            
            # Verificar se título está no nome
            if titulo and titulo.lower() in musica_lower:
                pontuacao += 10
            
            # Verificar se artista está no nome
            if artista and artista.lower() in musica_lower:
                pontuacao += 20  # Artista tem peso maior
            
            # Verificar palavras do título
            if titulo:
                palavras_titulo = set(titulo.lower().split())
                palavras_musica = set(musica_lower.replace('_', ' ').split())
                titulo_match = palavras_titulo & palavras_musica
                pontuacao += len(titulo_match)
            
            # Calcular similaridade geral
            similaridade = self._calcular_similaridade(termo, musica)
            pontuacao += int(similaridade * 10)
            
            if pontuacao > 5:
                melhores_correspondencias.append((pontuacao, similaridade, musica))
        
        # Ordenar por pontuação (maior primeiro)
        melhores_correspondencias.sort(reverse=True)
        
        if melhores_correspondencias:
            melhor = melhores_correspondencias[0][2]
            caminho = os.path.join(DOWNLOAD_DIR, melhor)
            print(f"✅ Música encontrada: {melhor} (pontuação: {melhores_correspondencias[0][0]})")
            return caminho
        
        return None
    
    def _verificar_se_ja_existe(self, titulo: str, artista: str = None) -> Optional[str]:
        """
        Verifica se uma música já existe na playlist
        Retorna o caminho se existir, None caso contrário
        """
        musicas = self.get_playlist()
        
        # Criar termo de busca combinado
        if artista:
            termos_busca = [
                f"{artista} - {titulo}".lower(),
                f"{titulo} - {artista}".lower(),
                titulo.lower(),
                artista.lower()
            ]
        else:
            termos_busca = [titulo.lower()]
        
        for musica in musicas:
            musica_lower = musica.lower()
            
            # Verificar cada termo de busca
            for termo in termos_busca:
                if termo in musica_lower:
                    caminho = os.path.join(DOWNLOAD_DIR, musica)
                    print(f"✅ Música já existe: {musica}")
                    return caminho
                
                # Verificar similaridade alta (>0.8)
                similaridade = self._calcular_similaridade(termo, musica_lower)
                if similaridade > 0.8:
                    caminho = os.path.join(DOWNLOAD_DIR, musica)
                    print(f"✅ Música similar encontrada: {musica} (similaridade: {similaridade:.2f})")
                    return caminho
        
        return None
    
    def _pesquisar_yt(self, termo: str) -> List[Dict]:
        """
        Pesquisa no YouTube e retorna lista de resultados
        """
        try:
            from yt_dlp import YoutubeDL

            # extract_flat devolve metadados mínimos e em versões recentes do yt-dlp
            # pode não incluir 'duration'. Usar extract_flat='in_playlist' para obter
            # os campos essenciais sem fazer download completo de cada vídeo.
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'skip_download': True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                print(f"🔍 A pesquisar: {termo}")
                info = ydl.extract_info(f"ytsearch10:{termo}", download=False)

                resultados = []
                if info and 'entries' in info:
                    for entry in info['entries']:
                        if not entry:
                            continue

                        video_id = entry.get('id', '')
                        titulo = entry.get('title', '') or ''
                        duracao = entry.get('duration') or 0
                        canal = (
                            entry.get('channel')
                            or entry.get('uploader')
                            or entry.get('channel_id')
                            or 'Desconhecido'
                        )

                        # Ignorar entradas sem título ou sem id
                        if not titulo or not video_id:
                            continue

                        resultados.append({
                            'title': titulo,
                            'artist': canal,
                            'duration': int(duracao) if duracao else 0,
                            'url': f"https://youtube.com/watch?v={video_id}",
                            'id': video_id,
                        })

                print(f"🔍 {len(resultados)} resultado(s) encontrado(s)")
                return resultados

        except Exception as e:
            print(f"❌ Erro na pesquisa: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _encontrar_melhor_resultado(self, resultados, termo_original):
        """
        Encontra o resultado que melhor corresponde ao termo original
        """
        titulo, artista = self._extrair_artista_titulo(termo_original)
        
        if not artista:
            # Se não tem artista, retorna o primeiro resultado
            return resultados[0] if resultados else None
        
        melhor_resultado = None
        melhor_pontuacao = 0
        
        for r in resultados:
            pontuacao = 0
            titulo_resultado = r['title'].lower()
            artista_resultado = r['artist'].lower()
            
            # Verificar se o artista está no título ou artista do resultado
            if artista.lower() in artista_resultado:
                pontuacao += 30  # Correspondência exata do artista
            elif artista.lower() in titulo_resultado:
                pontuacao += 20  # Artista mencionado no título
            
            # Verificar palavras do título
            if titulo:
                palavras_titulo = set(titulo.lower().split())
                palavras_resultado = set(titulo_resultado.split())
                match = palavras_titulo & palavras_resultado
                pontuacao += len(match) * 2
            
            # Verificar similaridade geral
            similaridade = self._calcular_similaridade(termo_original, r['title'])
            pontuacao += int(similaridade * 20)
            
            if pontuacao > melhor_pontuacao:
                melhor_pontuacao = pontuacao
                melhor_resultado = r
        
        # Se encontrou uma boa correspondência (pontuação > 30), usa essa
        if melhor_pontuacao > 30:
            print(f"✅ Encontrada correspondência com pontuação {melhor_pontuacao}")
            return melhor_resultado
        
        # Caso contrário, retorna None para mostrar diálogo
        return None
    
    def tocar_url(self, url: str):
        """
        Descarrega e toca a partir de uma URL do YouTube diretamente.
        Suporta vídeos individuais e playlists.
        """
        def _processar():
            try:
                if self.on_download_status:
                    self.on_download_status(f"A obter informação da URL...")
                if self.on_chat_message:
                    self.on_chat_message(f"🔗 A processar URL...")

                from yt_dlp import YoutubeDL

                # Obter título sem fazer download
                ydl_opts_info = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'extract_flat': False,
                    'noplaylist': True,   # ignorar playlists, só o vídeo
                    'no_color': True,
                }
                import urllib.parse as _up
                parsed = _up.urlparse(url)
                params = _up.parse_qs(parsed.query)
                playlist_id = params.get('list', [None])[0]
                video_id    = params.get('v',    [None])[0]

                # Radio/mix playlists (RD, FL, LL, PL geradas) não são acessíveis
                # Usar SEMPRE só o video_id se existir — evita que yt-dlp tente a playlist
                if video_id:
                    url_efetiva = f"https://www.youtube.com/watch?v={video_id}"
                    playlist_id = None
                elif playlist_id and not playlist_id.startswith('RD'):
                    url_efetiva = f"https://www.youtube.com/playlist?list={playlist_id}"
                else:
                    url_efetiva = url
                    playlist_id = None

                with YoutubeDL(ydl_opts_info) as ydl:
                    info = ydl.extract_info(url_efetiva, download=False)

                # Se for playlist, pegar o primeiro entry
                if info.get('_type') == 'playlist' or 'entries' in info:
                    entries = list(info.get('entries', []))
                    if entries:
                        info = entries[0]

                titulo = info.get('title', 'Audio')
                artista = info.get('uploader', '')

                # Verificar se já existe
                caminho_existente = self._verificar_se_ja_existe(titulo, artista)
                if caminho_existente:
                    if self.on_chat_message:
                        self.on_chat_message(f"📂 Já existe na playlist. A tocar...")
                    self.tocar_arquivo(caminho_existente)
                    return

                # Construir nome do ficheiro
                nome_base = titulo
                nome_arquivo = self._normalizar_nome(nome_base)
                caminho = os.path.join(DOWNLOAD_DIR, nome_arquivo)

                if self.on_chat_message:
                    self.on_chat_message(f"⬇️ A descarregar: {titulo}")
                if self.on_download_status:
                    self.on_download_status(f"A descarregar: {titulo}")

                # Tentar URL original; se falhar e tiver playlist, tentar playlist
                sucesso = self._baixar_url_yt(url_efetiva, caminho)
                if not sucesso and playlist_id:
                    pl_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                    if self.on_download_status:
                        self.on_download_status(f"A tentar playlist...")
                    sucesso = self._baixar_url_yt(pl_url, caminho)

                if sucesso:
                    if self.on_chat_message:
                        self.on_chat_message(f"⬇️ Download concluído. A extrair faixas...")
                    threading.Thread(
                        target=self._extrair_e_tocar,
                        args=(caminho, nome_base),
                        daemon=True
                    ).start()
                else:
                    if self.on_chat_message:
                        self.on_chat_message("❌ Falha no download da URL.")
                    if self.on_download_status:
                        self.on_download_status("")

            except Exception as e:
                print(f"❌ Erro ao processar URL: {e}")
                if self.on_chat_message:
                    self.on_chat_message(f"❌ Erro ao processar URL: {e}")
                if self.on_download_status:
                    self.on_download_status("")

        threading.Thread(target=_processar, daemon=True).start()

    def tocar_musica(self, termo: str):
        """
        Toca uma música pelo nome
        """
        print(f"[DEBUG] A tocar: '{termo}'")
        
        def _processar():
            try:
                # Primeiro, verificar se já existe na playlist
                titulo, artista = self._extrair_artista_titulo(termo)
                caminho_existente = self._verificar_se_ja_existe(titulo, artista)
                
                if caminho_existente:
                    print(f"📂 Música já existe na playlist")
                    if self.on_download_status:
                        self.on_download_status("Música encontrada localmente")
                    if self.on_chat_message:
                        self.on_chat_message(f"🎵 A tocar: {os.path.basename(caminho_existente)}")
                    time.sleep(0.3)
                    self.tocar_arquivo(caminho_existente)
                    return
                
                # Se não existir, pesquisar no YouTube
                print(f"🌐 A pesquisar no YouTube: {termo}")
                if self.on_download_status:
                    self.on_download_status(f"A pesquisar: {termo}")
                
                resultados = self._pesquisar_yt(termo)
                
                if not resultados:
                    if self.on_download_status:
                        self.on_download_status("❌ Nenhum resultado encontrado")
                    return
                
                # Tentar encontrar o melhor resultado
                melhor_resultado = self._encontrar_melhor_resultado(resultados, termo)
                
                if melhor_resultado:
                    # Antes de fazer download, verificar novamente se já existe
                    titulo_resultado = melhor_resultado['title']
                    artista_resultado = melhor_resultado['artist']
                    
                    caminho_existente = self._verificar_se_ja_existe(titulo_resultado, artista_resultado)
                    
                    if caminho_existente:
                        print(f"📂 Música já existe (verificação final)")
                        self.tocar_arquivo(caminho_existente)
                    else:
                        # Fazer download
                        print(f"✅ A fazer download de: {melhor_resultado['title']}")
                        self._fazer_download(melhor_resultado, termo)
                else:
                    # Não encontrou correspondência exata
                    if not resultados:
                        print("❌ Nenhum resultado encontrado no YouTube")
                        if self.on_download_status:
                            self.on_download_status("❌ Nenhum resultado encontrado")
                        return

                    # Mostrar diálogo de escolha com os resultados disponíveis
                    print(f"⚠️ Múltiplas versões encontradas ({len(resultados)}), a mostrar diálogo")
                    if self.gui:
                        self.gui.after(0, lambda: self._mostrar_dialogo_escolha(resultados, termo))
                    else:
                        # Sem GUI, escolher o primeiro
                        self._fazer_download(resultados[0], termo)
                    
            except Exception as e:
                print(f"❌ Erro em tocar_musica: {e}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=_processar, daemon=True).start()
    
    def _mostrar_dialogo_escolha(self, resultados, termo_original):
        """Mostra diálogo para escolher entre múltiplos resultados"""
        if not self.gui:
            self._fazer_download(resultados[0], termo_original)
            return
        
        def callback(selecao):
            if selecao:
                # Correr em thread para não bloquear a UI
                def _processar():
                    titulo = selecao['title']
                    artista = selecao.get('artist', '')
                    caminho_existente = self._verificar_se_ja_existe(titulo, artista)
                    if caminho_existente:
                        print(f"📂 Música já existe")
                        self.tocar_arquivo(caminho_existente)
                    else:
                        self._fazer_download(selecao, termo_original)
                threading.Thread(target=_processar, daemon=True).start()
        
        SelecaoMusicaDialog(self.gui, termo_original, resultados, callback)
    
    def _fazer_download(self, resultado, termo_original):
        """Faz download do resultado selecionado"""
        titulo = resultado['title']
        artista = resultado.get('artist', '')
        
        # Construir nome do ficheiro de forma mais limpa
        if artista and artista not in titulo:
            # Remover " - Topic" ou outros sufixos comuns
            artista_limpo = re.sub(r'\s*[-–—]\s*Topic$', '', artista)
            titulo_limpo = re.sub(r'\s*\(.*?\)\s*$', '', titulo)
            nome_base = f"{artista_limpo} - {titulo_limpo}"
        else:
            nome_base = re.sub(r'\s*\(.*?\)\s*$', '', titulo)
        
        nome_arquivo = self._normalizar_nome(nome_base)
        caminho = os.path.join(DOWNLOAD_DIR, nome_arquivo)
        
        # Última verificação antes de download
        if os.path.exists(caminho):
            print(f"📂 Ficheiro já existe: {nome_arquivo}")
            self.tocar_arquivo(caminho)
            return
        
        print(f"📥 A fazer download: {nome_base}")
        if self.on_download_status:
            self.on_download_status(f"A descarregar: {nome_base}")
        if self.on_chat_message:
            self.on_chat_message(f"⬇️ A descarregar: {nome_base}")
        
        # Fazer download do áudio
        url = resultado.get('url')
        if url:
            sucesso = self._baixar_url_yt(url, caminho)
        else:
            sucesso = self._baixar_musica_yt(nome_base, caminho)
        
        if sucesso:
            print(f"✅ Download concluído: {nome_arquivo}")
            if self.on_chat_message:
                self.on_chat_message(f"⬇️ Download concluído. A extrair faixas...")
            if self.on_download_status:
                self.on_download_status("A extrair faixas...")
            # Tentar extração automática; se falhar, toca o ficheiro completo
            threading.Thread(
                target=self._extrair_e_tocar,
                args=(caminho, nome_base),
                daemon=True
            ).start()
        else:
            if self.on_download_status:
                self.on_download_status("❌ Falha no download")
            if self.on_chat_message:
                self.on_chat_message("❌ Falha no download. Tenta novamente.")
    
    def _extrair_e_tocar(self, caminho: str, nome_base: str):
        """
        Após download: extrai faixas automaticamente com ffmpeg silencedetect.
        Se a extração produzir faixas, toca a primeira.
        Se falhar ou não encontrar silêncios, toca o ficheiro completo.
        """
        import re as _re
        import subprocess as _sp

        # Criar subpasta com título limpo
        nome_limpo = _re.sub(r"[_\-]+", " ", os.path.splitext(os.path.basename(caminho))[0])
        nome_limpo = " ".join(w.capitalize() for w in nome_limpo.split()).strip()
        subpasta = os.path.join(DOWNLOAD_DIR, nome_limpo)
        os.makedirs(subpasta, exist_ok=True)

        print(f"✂️ A extrair faixas para: {subpasta}")

        try:
            # Detetar silêncios com ffmpeg
            cmd = ["ffmpeg", "-hide_banner", "-i", caminho,
                   "-af", "silencedetect=noise=-40dB:d=1.0",
                   "-f", "null", "-"]
            proc = _sp.run(cmd, capture_output=True, text=True)
            saida = proc.stderr

            # Parsear timestamps
            import re as _re2
            starts = [float(x) for x in _re2.findall(r"silence_start:\s*([\d.]+)", saida)]
            ends   = [float(x) for x in _re2.findall(r"silence_end:\s*([\d.]+)", saida)]

            # Obter duração total
            dur_match = _re2.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", saida)
            if dur_match:
                h, m, s = dur_match.groups()
                total = int(h)*3600 + int(m)*60 + float(s)
            else:
                total = 0

            # Construir lista de cortes (início/fim de cada faixa)
            cortes = [0.0]
            for e in ends:
                cortes.append(e)
            cortes.append(total if total > 0 else None)

            faixas = []
            for i in range(len(cortes) - 1):
                t_ini = cortes[i]
                t_fim = cortes[i + 1]
                if t_fim is None:
                    continue
                duracao = t_fim - t_ini
                if duracao >= 30:  # ignorar faixas < 30 segundos
                    faixas.append((t_ini, t_fim))

            if len(faixas) < 2:
                # Não encontrou faixas suficientes — tocar ficheiro completo
                print("⚠️ Sem silêncios detetados, a tocar ficheiro completo")
                if self.on_chat_message:
                    self.on_chat_message(f"🎵 A tocar: {nome_base}")
                if self.on_download_status:
                    self.on_download_status("")
                time.sleep(0.3)
                self.tocar_arquivo(caminho)
                return

            # Extrair cada faixa com ffmpeg
            primeira = None
            for i, (t_ini, t_fim) in enumerate(faixas, start=1):
                nome_faixa = f"{i:02d} - Faixa {i:02d}.mp3"
                destino = os.path.join(subpasta, nome_faixa)
                cmd_ext = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{t_ini:.3f}", "-to", f"{t_fim:.3f}",
                    "-i", caminho, "-vn", "-c:a", "libmp3lame", "-q:a", "2",
                    destino
                ]
                try:
                    _sp.run(cmd_ext, check=True)
                    if primeira is None:
                        primeira = destino
                    print(f"✅ Faixa {i}: {nome_faixa}")
                except Exception as e:
                    print(f"⚠️ Erro faixa {i}: {e}")

            if primeira:
                n = len(faixas)
                print(f"✅ {n} faixas extraídas para {subpasta}")
                if self.on_chat_message:
                    self.on_chat_message(f"✅ {n} faixas extraídas. A tocar faixa 1...")
                if self.on_download_status:
                    self.on_download_status("")
                # Notificar playlist_window da subpasta e abrir janela
                try:
                    from playlist_window import PlaylistWindow
                    PlaylistWindow._subpasta_atual = subpasta
                    if self.gui:
                        self.gui.after(800, lambda: PlaylistWindow.mostrar_playlist(self, self.gui))
                except Exception:
                    pass
                time.sleep(0.3)
                self.tocar_arquivo(primeira)
            else:
                # Extração falhou — tocar ficheiro completo
                if self.on_chat_message:
                    self.on_chat_message(f"🎵 A tocar: {nome_base}")
                if self.on_download_status:
                    self.on_download_status("")
                time.sleep(0.3)
                self.tocar_arquivo(caminho)

        except Exception as e:
            print(f"⚠️ Extração falhou: {e} — a tocar ficheiro completo")
            if self.on_chat_message:
                self.on_chat_message(f"🎵 A tocar: {nome_base}")
            if self.on_download_status:
                self.on_download_status("")
            time.sleep(0.3)
            self.tocar_arquivo(caminho)

    def _baixar_url_yt(self, url: str, caminho_musica: str) -> bool:
        """Download a partir de URL do YouTube"""
        try:
            from yt_dlp import YoutubeDL
            
            def _hook(d):
                try:
                    if d.get("status") == "downloading":
                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        done = d.get("downloaded_bytes", 0)
                        if total and self.on_download_progress:
                            percent = (done / total) * 100
                            self.on_download_progress(percent, d.get("speed"), d.get("eta"))
                    elif d.get("status") == "finished":
                        if self.on_download_status:
                            self.on_download_status("A converter para MP3...")
                except Exception:
                    pass
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'no_color': True,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'progress_hooks': [_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'keepvideo': False,
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Encontrar o MP3 mais recente
                time.sleep(1)
                mp3_encontrado = None
                tempo_atual = time.time()
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(DOWNLOAD_DIR, file)
                        if tempo_atual - os.path.getctime(file_path) < 120:
                            mp3_encontrado = file_path
                            break
                
                if mp3_encontrado:
                    if mp3_encontrado != caminho_musica:
                        if os.path.exists(caminho_musica):
                            os.remove(caminho_musica)
                        os.rename(mp3_encontrado, caminho_musica)
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Erro no download: {e}")
            return False
    
    def _baixar_musica_yt(self, termo: str, caminho_musica: str) -> bool:
        """Download a partir de pesquisa"""
        try:
            from yt_dlp import YoutubeDL
            
            def _hook(d):
                try:
                    if d.get("status") == "downloading":
                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        done = d.get("downloaded_bytes", 0)
                        if total and self.on_download_progress:
                            percent = (done / total) * 100
                            self.on_download_progress(percent, d.get("speed"), d.get("eta"))
                    elif d.get("status") == "finished":
                        if self.on_download_status:
                            self.on_download_status("A converter para MP3...")
                except Exception:
                    pass
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'progress_hooks': [_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'keepvideo': False,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch:{termo}"])
                
                # Encontrar o MP3 mais recente
                time.sleep(1)
                mp3_encontrado = None
                tempo_atual = time.time()
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(DOWNLOAD_DIR, file)
                        if tempo_atual - os.path.getctime(file_path) < 120:
                            mp3_encontrado = file_path
                            break
                
                if mp3_encontrado:
                    if mp3_encontrado != caminho_musica:
                        if os.path.exists(caminho_musica):
                            os.remove(caminho_musica)
                        os.rename(mp3_encontrado, caminho_musica)
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Erro no download: {e}")
            return False
    
    def tocar_arquivo(self, caminho_musica: str):
        """
        Toca um ficheiro de áudio local
        """
        try:
            if not os.path.exists(caminho_musica):
                print(f"❌ Ficheiro não existe: {caminho_musica}")
                return False
            
            print(f"▶️ A reproduzir: {os.path.basename(caminho_musica)}")
            
            # Para a música atual
            self.parar_musica()
            time.sleep(0.2)
            
            # Esconder status de download
            if self.on_download_status:
                self.on_download_status("")
            
            # Carregar e tocar com pygame.mixer.music
            try:
                pygame.mixer.music.load(caminho_musica)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()
                time.sleep(0.3)
                
                if pygame.mixer.music.get_busy():
                    print("✅ Música a tocar")
                    self.tocando = True
                    self.pausado = False
                    self.musica_atual = caminho_musica
                    # Atualizar índice na playlist
                    playlist = self.get_playlist()
                    nome = os.path.basename(caminho_musica)
                    if nome in playlist:
                        self._indice_atual = playlist.index(nome)
                    self._notify_state(True)
                    
                    # Obter duração com mutagen se disponível
                    self._pos_segundos = 0.0
                    self._duracao = 0.0
                    try:
                        from mutagen.mp3 import MP3
                        audio = MP3(caminho_musica)
                        self._duracao = audio.info.length
                    except Exception:
                        pass

                    # Monitora progresso e fim da música
                    def monitorar():
                        _inicio = time.time()
                        _offset = 0.0  # offset após seek
                        while pygame.mixer.music.get_busy() and self.tocando and not self.pausado:
                            # Verificar seek pendente
                            if self._seek_pendente is not None:
                                pos = self._seek_pendente
                                self._seek_pendente = None
                                try:
                                    pygame.mixer.music.set_pos(pos)
                                    _offset = pos
                                    _inicio = time.time()
                                except Exception:
                                    pass
                            # Calcular posição atual
                            self._pos_segundos = _offset + (time.time() - _inicio)
                            if self._duracao > 0:
                                self._pos_segundos = min(self._pos_segundos, self._duracao)
                            # Notificar GUI
                            if self.on_progress:
                                try:
                                    self.on_progress(self._pos_segundos, self._duracao)
                                except Exception:
                                    pass
                            time.sleep(0.5)
                        if self.tocando and not self.pausado:
                            print("⏹️ Música terminou")
                            self.tocando = False
                            self.pausado = False
                            self.musica_atual = None
                            self._pos_segundos = 0.0
                            if self.on_progress:
                                try:
                                    self.on_progress(0.0, self._duracao)
                                except Exception:
                                    pass
                            self._notify_state(False)

                    threading.Thread(target=monitorar, daemon=True).start()
                    return True
                else:
                    print("⚠️ Música não começou a tocar")
                    self._notify_state(False)
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao carregar música: {e}")
                self._notify_state(False)
                return False
            
        except Exception as e:
            print(f"❌ Erro ao tocar: {e}")
            self._notify_state(False)
            return False
    
    def pausar_musica(self) -> str:
        """Pausa a reprodução - só funciona se estiver a tocar"""
        if self.tocando and not self.pausado:
            try:
                pygame.mixer.music.pause()
                self.pausado = True
                print("⏸️ Música pausada")
                return "⏸️ Música pausada."
            except Exception as e:
                print(f"⚠️ Erro ao pausar: {e}")
                return "❌ Erro ao pausar."
        elif not self.tocando:
            return "⚠️ Não há música a tocar."
        elif self.pausado:
            return "⚠️ A música já está pausada."
        return "❌ Comando não disponível."

    def resumir_musica(self) -> str:
        """Retoma a reprodução - só funciona se estiver pausada"""
        if self.pausado:
            try:
                pygame.mixer.music.unpause()
                self.pausado = False
                print("▶️ Música retomada")
                return "▶️ Música retomada."
            except Exception as e:
                print(f"⚠️ Erro ao retomar: {e}")
                return "❌ Erro ao retomar."
        elif not self.tocando:
            return "⚠️ Não há música pausada para retomar. A música foi parada, não pausada."
        else:
            return "⚠️ A música não está pausada. Usa 'pausar' primeiro."

    def parar_musica(self) -> str:
        """Para a reprodução"""
        try:
            estava_tocando = self.tocando
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.tocando = False
            self.pausado = False
            self.musica_atual = None
            self._notify_state(False)
            print("⏹️ Música parada")
            if estava_tocando:
                return "⏹️ Música parada."
            else:
                return "⏹️ Música parada. (não havia música a tocar)"
        except Exception as e:
            print(f"⚠️ Erro ao parar: {e}")
            return "❌ Erro ao parar."

    def controlar_volume(self, nivel: int | float) -> str:
        """Ajusta o volume (0-100)"""
        try:
            val = float(nivel)
        except Exception:
            return "⚠️ Volume inválido. Usa um número entre 0 e 100."
        
        if val < 0 or val > 100:
            return "⚠️ Volume deve estar entre 0 e 100."
        
        self.volume = val / 100.0
        
        try:
            pygame.mixer.music.set_volume(self.volume)
            print(f"🔊 Volume: {int(round(self.volume * 100))}%")
            return f"🔊 Volume: {int(round(self.volume * 100))}%"
        except Exception as e:
            print(f"⚠️ Erro ao ajustar volume: {e}")
            return "❌ Erro ao ajustar volume."

    def limpar_playlist(self) -> str:
        """Remove todos os ficheiros MP3 da pasta Download"""
        if not os.path.isdir(DOWNLOAD_DIR):
            return "📂 Pasta de download não encontrada."
        
        count = 0
        for file in os.listdir(DOWNLOAD_DIR):
            if file.lower().endswith(".mp3"):
                try:
                    os.remove(os.path.join(DOWNLOAD_DIR, file))
                    count += 1
                except Exception:
                    pass
        
        print(f"🗑️ Playlist limpa ({count} ficheiros removidos).")
        if count > 0:
            return f"🗑️ Playlist limpa ({count} ficheiros removidos)."
        else:
            return "📂 Playlist já estava vazia."
