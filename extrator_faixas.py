# -*- coding: utf-8 -*-
"""
Extrator de Faixas — UI Moderna (Discogs)
-----------------------------------------
Deteta faixas por:
 - Silêncio (FFmpeg silencedetect)  [modo padrão]
 - Avançada (sem silêncio) usando análise de conteúdo (librosa)

Permite editar/selecionar, extrai MP3s e grava ID3.
Títulos das faixas: via Discogs (token opcional) ou colando um tracklist.

Requisitos:
    pip install customtkinter pydub requests mutagen
    (para o modo avançado) pip install librosa soundfile numpy

Necessário no PATH (ou embutido na versão portátil):
    ffmpeg, ffprobe

Guarda preferências em: extrator_config.json
"""

import os, sys, re, json, time, queue, threading, subprocess, shutil
from typing import List, Optional

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

from pydub import AudioSegment
import requests
from mutagen.id3 import ID3, TIT2, TALB, TRCK, ID3NoHeaderError

# tentativa de import avançado (librosa); só usado se o utilizador escolher o modo "Avançada"
try:
    import numpy as _np  # usado pelo modo avançado
    import librosa as _librosa
    _HAVE_LIBROSA = True
except Exception:
    _HAVE_LIBROSA = False

APP_TITLE = "Extrator de Faixas — UI Moderna (Discogs)"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "extrator_config.json")

# --- janela oculta para subprocess no Windows (sem console) ---
_WIN_NO_WINDOW = {}
if os.name == "nt":
    _si = subprocess.STARTUPINFO()
    _si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _WIN_NO_WINDOW = {"startupinfo": _si, "creationflags": 0x08000000}  # CREATE_NO_WINDOW


# ---------------------- util ----------------------
def safe_name(txt: str) -> str:
    txt = re.sub(r'[\\/:*?"<>|]', "_", txt or "")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt or "Sem_Titulo"


def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------- modelo ----------------------
class Track:
    def __init__(self, number: int, start_ms: int, end_ms: int, duration_s: float, title: Optional[str] = None):
        self.number = number
        self.start = start_ms
        self.end = end_ms
        self.duration = duration_s
        self.title = title or f"Faixa {number:02d}"


# ---------------------- worker ----------------------
class Worker(threading.Thread):
    def __init__(
        self,
        mode: str,                 # "detect", "detect_adv", "extract"
        audio_file: str,
        threshold_db: int,
        min_silence_ms: int,
        min_track_s: int,
        pad_ms: int,
        tracks: Optional[List[Track]],
        out_dir: Optional[str],
        album: Optional[str],
        write_id3: bool,
        log_q: "queue.Queue[str]",
        prog_q: "queue.Queue[float]",
        res_q: "queue.Queue[dict]",
    ):
        super().__init__(daemon=True)
        self.mode = mode
        self.audio_file = audio_file
        self.threshold_db = threshold_db
        self.min_silence_ms = min_silence_ms
        self.min_track_s = min_track_s
        self.pad_ms = pad_ms
        self.tracks = tracks or []
        self.out_dir = out_dir
        self.album = album
        self.write_id3 = write_id3
        self.log_q = log_q
        self.prog_q = prog_q
        self.res_q = res_q
        self.stop_evt = threading.Event()

    def stop(self):
        self.stop_evt.set()

    def log(self, msg: str):
        self.log_q.put(msg)

    def prog(self, p: float):
        p = max(0.0, min(1.0, p))
        self.prog_q.put(p)

    def _probe_duration(self, path) -> float:
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", path],
                stderr=subprocess.STDOUT,
                text=True,
                **_WIN_NO_WINDOW,
            )
            return float(out.strip())
        except Exception:
            try:
                return len(AudioSegment.from_file(path)) / 1000.0
            except Exception:
                return 0.0

    def run(self):
        try:
            if self.mode == "detect":
                self.detect()
            elif self.mode == "detect_adv":
                self.detect_advanced()
            elif self.mode == "extract":
                self.extract()
        except Exception as e:
            self.log(f"❌ Erro: {e}")
            self.res_q.put({"type": "error", "error": str(e)})
        finally:
            self.prog(1.0)

    # ------------ deteção com silencedetect + fallback ------------
    def detect(self):
        self.log("🔎 Deteção (FFmpeg silencedetect)...")
        total_s = self._probe_duration(self.audio_file)
        if total_s <= 0:
            self.log("⚠️ Duração desconhecida por ffprobe; a usar fallback pydub.")
            return self.detect_fallback()

        noise = f"{self.threshold_db}dB"
        dur = self.min_silence_ms / 1000.0
        cmd = ["ffmpeg", "-hide_banner", "-i", self.audio_file, "-af", f"silencedetect=noise={noise}:d={dur}", "-f", "null", "-"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **_WIN_NO_WINDOW,
            )
        except FileNotFoundError:
            self.log("⚠️ ffmpeg não encontrado; fallback pydub.")
            return self.detect_fallback()

        silences = []
        st = None
        time_re = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
        while True:
            if self.stop_evt.is_set():
                self.res_q.put({"type": "detected", "tracks": []})
                return
            line = proc.stderr.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            if "silence_start" in line:
                try:
                    st = float(line.split("silence_start:")[1].strip())
                except Exception:
                    st = None
            elif "silence_end" in line:
                try:
                    en = float(line.split("silence_end:")[1].split()[0])
                    if st is not None:
                        silences.append((st, en))
                        st = None
                except Exception:
                    pass
            m = time_re.search(line)
            if m:
                hh, mm, ss = int(m.group(1)), int(m.group(2)), float(m.group(3))
                self.prog(min(1.0, (hh * 3600 + mm * 60 + ss) / total_s))
        if proc.wait() != 0:
            self.log("❌ silencedetect falhou; fallback pydub.")
            return self.detect_fallback()

        total_ms = int(total_s * 1000)
        silences_ms = [(0, 0)] + [(int(s * 1000), int(e * 1000)) for s, e in silences] + [(total_ms, total_ms)]
        silences_ms.sort()

        merged = []
        for s, e in silences_ms:
            if not merged or s > merged[-1][1]:
                merged.append([s, e])
            else:
                merged[-1][1] = max(merged[-1][1], e)

        # metadados
        album = None
        chapters = []
        try:
            info = subprocess.check_output(
                ["ffprobe", "-v", "error", "-print_format", "json", "-show_chapters", "-show_format", self.audio_file],
                text=True,
                **_WIN_NO_WINDOW,
            )
            meta = json.loads(info)
            album = (meta.get("format", {}).get("tags", {}) or {}).get("album")
            for ch in meta.get("chapters", []) or []:
                cs = int(float(ch.get("start_time", "0")) * 1000)
                ce = int(float(ch.get("end_time", "0")) * 1000)
                ct = (ch.get("tags", {}) or {}).get("title")
                chapters.append((cs, ce, ct))
        except Exception:
            pass

        tracks: List[Track] = []
        for i in range(len(merged) - 1):
            start = max(0, merged[i][1] - self.pad_ms)
            end = min(total_ms, merged[i + 1][0] + self.pad_ms)
            dur_s = (end - start) / 1000.0
            if end > start and dur_s >= self.min_track_s:
                tracks.append(Track(len(tracks) + 1, start, end, dur_s))

        if chapters:
            for tr in tracks:
                best = None
                ovbest = -1
                for cs, ce, ct in chapters:
                    ov = min(tr.end, ce) - max(tr.start, cs)
                    if ov > ovbest and ct:
                        ovbest = ov
                        best = ct
                if best:
                    tr.title = best

        self.log(f"✅ Deteção concluída: {len(tracks)} faixa(s).")
        self.res_q.put({"type": "detected", "tracks": tracks, "album": album})

    def detect_fallback(self):
        audio = AudioSegment.from_file(self.audio_file, format="mp3")
        total_ms = len(audio)
        frame = 50
        processed = 0
        in_seg = False
        seg_start = 0
        silence_run = 0
        rough = []
        while processed < total_ms:
            end = min(processed + frame, total_ms)
            ch = audio[processed:end]
            db = ch.dBFS if len(ch) > 0 and ch.rms > 0 else -120.0
            if db > self.threshold_db:
                if not in_seg:
                    in_seg = True; seg_start = processed
                silence_run = 0
            else:
                if in_seg:
                    silence_run += (end - processed)
                    if silence_run >= self.min_silence_ms:
                        if processed > seg_start:
                            rough.append([seg_start, processed])
                        in_seg = False; silence_run = 0
            processed = end
            self.prog(0.05 + 0.70 * (processed / total_ms))
        if in_seg:
            rough.append([seg_start, total_ms])

        gaps = []
        if rough:
            merged = []
            for s, e in rough:
                if not merged or s > merged[-1][1]:
                    merged.append([s, e])
                else:
                    merged[-1][1] = max(merged[-1][1], e)
            last = 0
            for s, e in merged:
                if s > last: gaps.append([last, s])
                last = e
            if last < total_ms: gaps.append([last, total_ms])
        else:
            gaps = [[0, total_ms]]

        tracks: List[Track] = []
        for i in range(len(gaps) - 1):
            start = max(0, gaps[i][1] - self.pad_ms)
            end = min(total_ms, gaps[i + 1][0] + self.pad_ms)
            dur = (end - start) / 1000.0
            if end > start and dur >= self.min_track_s:
                tracks.append(Track(len(tracks) + 1, start, end, dur))
        self.log(f"✅ Deteção (fallback) concluiu: {len(tracks)} faixa(s).")
        self.res_q.put({"type": "detected", "tracks": tracks})

    # ------------ deteção avançada (sem silêncio) ------------
    def detect_advanced(self):
        if not _HAVE_LIBROSA:
            self.log("❌ Modo avançado requer: pip install librosa soundfile numpy")
            self.res_q.put({"type": "detected", "tracks": []})
            return

        self.log("🧠 Deteção avançada (sem silêncio) — analisando conteúdo…")
        try:
            # carrega áudio mono sem reamostrar
            y, sr = _librosa.load(self.audio_file, sr=None, mono=True)
        except Exception as e:
            self.log(f"❌ Não consegui carregar com librosa: {e}")
            self.res_q.put({"type": "detected", "tracks": []})
            return

        total_s = _librosa.get_duration(y=y, sr=sr)
        self.prog(0.15)

        # curva de “novelty”: força de onsets (mudanças de espectro/energia)
        hop = 512
        try:
            env = _librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, aggregate=_np.median)
        except Exception:
            # fallback simples: energia por frames
            frame_len = 2048
            env = _np.array([_np.sqrt(_np.mean(y[i:i+frame_len]**2)) for i in range(0, len(y), hop)])

        # suaviza (média móvel)
        win = 9
        kernel = _np.ones(win) / win
        sm = _np.convolve(env, kernel, mode="same")

        # threshold relativo
        thr = 0.2 * (sm.max() if sm.size else 1.0)

        # picos espaçados: exigimos intervalo mínimo entre cortes (min_track_s)
        # converte min_track_s para frames
        min_frames = max(1, int((self.min_track_s * sr) / hop))

        # detetar picos: pico local onde sinal > vizinhança e > threshold
        # abordagem simples com máscara lógica (evita dependência extra)
        peaks = []
        for i in range(2, len(sm)-2):
            if sm[i] > thr and sm[i] > sm[i-1] and sm[i] > sm[i+1] and sm[i] > sm[i-2] and sm[i] > sm[i+2]:
                if not peaks or (i - peaks[-1]) >= min_frames:
                    peaks.append(i)

        # pontos de corte (segundos)
        cut_sec = _librosa.frames_to_time(_np.array(peaks), sr=sr, hop_length=hop) if peaks else _np.array([])

        # construir segmentos com base nos cortes espaçados por min_track_s
        tracks: List[Track] = []
        pad = self.pad_ms
        total_ms = int(total_s * 1000)
        pts = [0] + [int(t * 1000) for t in cut_sec if 0 < t < total_s] + [total_ms]
        pts = sorted(set(pts))

        # junta cortes demasiado próximos (< min_track_s) e gera faixas
        min_gap_ms = int(self.min_track_s * 1000)
        segs = []
        start = pts[0]
        for i in range(1, len(pts)):
            if pts[i] - start >= min_gap_ms:
                segs.append((start, pts[i]))
                start = pts[i]
        if segs and segs[-1][1] < total_ms:  # acrescenta final se sobrou
            if total_ms - segs[-1][1] >= min_gap_ms:
                segs.append((segs[-1][1], total_ms))
        elif not segs:
            segs = [(0, total_ms)]

        # aplica padding e cria Track
        out = []
        for s, e in segs:
            ss = max(0, s - pad)
            ee = min(total_ms, e + pad)
            dur_s = (ee - ss) / 1000.0
            if dur_s >= self.min_track_s:
                out.append((ss, ee, dur_s))

        for i, (s, e, d) in enumerate(out, start=1):
            tracks.append(Track(i, s, e, d))

        self.log(f"✅ Deteção avançada concluiu: {len(tracks)} faixa(s).")
        self.res_q.put({"type": "detected", "tracks": tracks})


    # ------------ extração ------------
    def _write_id3(self, out_path: str, title: str, album: Optional[str], n: int):
        if not self.write_id3:
            return
        try:
            try:
                tags = ID3(out_path)
            except ID3NoHeaderError:
                tags = ID3()
            tags.add(TIT2(encoding=3, text=title or ""))
            if album:
                tags.add(TALB(encoding=3, text=album))
            tags.add(TRCK(encoding=3, text=str(n)))
            tags.save(out_path)
        except Exception as e:
            self.log(f"⚠️ Não foi possível gravar ID3 em {os.path.basename(out_path)}: {e}")

    def extract(self):
        base = os.path.splitext(self.audio_file)[0]
        out = self.out_dir or f"{base}_faixas_extraidas"
        os.makedirs(out, exist_ok=True)
        self.log(f"📂 Pasta de saída: {out}")

        tot = max(1, len(self.tracks))
        done = 0
        for tr in self.tracks:
            if self.stop_evt.is_set(): break
            title = tr.title or f"Faixa {tr.number:02d}"
            fname = f"{tr.number:02d} - {safe_name(title)}.mp3"
            out_path = os.path.join(out, fname)
            cmd = [
                "ffmpeg","-y","-hide_banner","-loglevel","error",
                "-ss", f"{tr.start/1000.0:.3f}", "-to", f"{tr.end/1000.0:.3f}",
                "-i", self.audio_file, "-vn","-c:a","libmp3lame","-q:a","2", out_path
            ]
            try:
                subprocess.check_call(cmd, **_WIN_NO_WINDOW)
            except FileNotFoundError:
                seg = AudioSegment.from_file(self.audio_file, format="mp3")[tr.start:tr.end]
                seg.export(out_path, format="mp3")
            except subprocess.CalledProcessError as e:
                self.log(f"❌ ffmpeg falhou (Faixa {tr.number}): {e}")
                continue
            self._write_id3(out_path, title, self.album, tr.number)
            done += 1
            self.prog(done / tot)
            self.log(f"✅ Guardado: {os.path.basename(out_path)}")

        self.res_q.put({"type": "extracted", "output_dir": out})


# ---------------------- app ----------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(950, 600)
        ctk.set_appearance_mode("system")
        ctk.set_widget_scaling(0.8)  # 80%

        # estado
        self.cfg = load_config()
        self.audio_file = None
        self.output_dir = self.cfg.get("last_output_dir") or ""
        self.album_name = self.cfg.get("last_album") or ""
        self.discogs_token = self.cfg.get("discogs_token") or ""
        self.detect_mode = self.cfg.get("detect_mode", "Silêncio (FFmpeg)")  # novo

        self.tracks: List[Track] = []
        self.cb_vars: List[ctk.BooleanVar] = []
        self.title_vars: List[ctk.CTkEntry] = []

        self.log_q: queue.Queue[str] = queue.Queue()
        self.prog_q: queue.Queue[float] = queue.Queue()
        self.res_q: queue.Queue[dict] = queue.Queue()
        self.worker: Optional[Worker] = None

        # layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self.after(150, self._poll)

    # ---------- UI ----------
    def _build_sidebar(self):
        sb = ctk.CTkScrollableFrame(self, corner_radius=0, width=280)
        sb.grid(row=0, column=0, sticky="nsw")
        self.sb = sb

        ctk.CTkLabel(sb, text="🎧 Extrator de Faixas", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(14, 6), sticky="w"
        )

        self.file_lbl = ctk.CTkLabel(sb, text="Nenhum ficheiro selecionado", wraplength=220)
        self.file_lbl.grid(row=1, column=0, padx=16, sticky="w")
        ctk.CTkButton(sb, text="Selecionar MP3", command=self.on_select_mp3).grid(row=2, column=0, padx=16, pady=6, sticky="ew")

        # ---- Modo de deteção ----
        ctk.CTkLabel(sb, text="Modo de deteção").grid(row=3, column=0, padx=16, sticky="w")
        self.mode_opt = ctk.CTkOptionMenu(sb,
            values=["Silêncio (FFmpeg)", "Avançada (sem silêncio)"],
            command=lambda v: self._save_mode(v)
        )
        self.mode_opt.set(self.detect_mode)
        self.mode_opt.grid(row=4, column=0, padx=16, pady=(2, 6), sticky="ew")

        # ---- Sensibilidade + mostrador dB ----
        ctk.CTkLabel(sb, text="Sensibilidade ao silêncio (dB)").grid(row=5, column=0, padx=16, sticky="w")
        self.db_var = ctk.IntVar(value=int(self.cfg.get("last_db", -40)))

        row6 = ctk.CTkFrame(sb, fg_color="transparent")
        row6.grid(row=6, column=0, padx=16, sticky="ew")
        row6.grid_columnconfigure(0, weight=1)

        self.db_slider = ctk.CTkSlider(row6, from_=-60, to=-10, number_of_steps=50, variable=self.db_var)
        self.db_slider.grid(row=0, column=0, sticky="ew", pady=(2, 0))

        self.db_label = ctk.CTkLabel(row6, text=f"{self.db_var.get()} dB")
        self.db_label.grid(row=0, column=1, padx=(8, 0))

        def _upd_db(*_):
            self.db_label.configure(text=f"{self.db_var.get()} dB")
        self.db_var.trace_add("write", _upd_db)

        ctk.CTkLabel(sb, text="Duração mínima silêncio (ms)").grid(row=7, column=0, padx=16, sticky="w")
        self.min_sil_entry = ctk.CTkEntry(sb); self.min_sil_entry.insert(0, "900")
        self.min_sil_entry.grid(row=8, column=0, padx=16, sticky="ew")

        ctk.CTkLabel(sb, text="Duração mínima da faixa (s)").grid(row=9, column=0, padx=16, sticky="w")
        self.min_track_entry = ctk.CTkEntry(sb); self.min_track_entry.insert(0, "45")
        self.min_track_entry.grid(row=10, column=0, padx=16, sticky="ew")

        ctk.CTkLabel(sb, text="Padding nas bordas (ms)").grid(row=11, column=0, padx=16, sticky="w")
        self.pad_entry = ctk.CTkEntry(sb); self.pad_entry.insert(0, "200")
        self.pad_entry.grid(row=12, column=0, padx=16, sticky="ew")

        ctk.CTkLabel(sb, text="Pasta de saída").grid(row=13, column=0, padx=16, sticky="w")
        self.out_entry = ctk.CTkEntry(sb)
        self.out_entry.insert(0, self.output_dir)
        self.out_entry.grid(row=14, column=0, padx=16, sticky="ew")
        ctk.CTkButton(sb, text="Escolher pasta...", command=self.on_choose_out).grid(row=15, column=0, padx=16, pady=4, sticky="ew")

        self.album_ck = ctk.CTkCheckBox(sb, text="Criar subpasta com nome do álbum")
        self.album_ck.select()
        self.album_ck.grid(row=16, column=0, padx=16, pady=(6, 0), sticky="w")

        ctk.CTkLabel(sb, text="Álbum").grid(row=17, column=0, padx=16, sticky="w")
        self.album_entry = ctk.CTkEntry(sb); self.album_entry.insert(0, self.album_name)
        self.album_entry.grid(row=18, column=0, padx=16, sticky="ew")

        ctk.CTkLabel(sb, text="Discogs token (opcional)").grid(row=19, column=0, padx=16, sticky="w")
        self.token_entry = ctk.CTkEntry(sb)
        self.token_entry.insert(0, self.discogs_token)
        self.token_entry.grid(row=20, column=0, padx=16, sticky="ew")
        self.token_entry.bind("<FocusOut>", lambda e: self._persist_token())

        ctk.CTkButton(sb, text="Obter tracklist (Discogs)", command=self.on_discogs).grid(
            row=21, column=0, padx=16, pady=(6, 6), sticky="ew"
        )
        ctk.CTkButton(sb, text="Colar tracklist…", command=self.on_paste_tracklist).grid(
            row=22, column=0, padx=16, pady=(0, 6), sticky="ew"
        )

        ctk.CTkLabel(sb, text="Deteção inicia ao escolher a pasta").grid(row=23, column=0, padx=16, pady=(6, 2), sticky="w")
        self.btn_extract = ctk.CTkButton(sb, text="Extrair Selecionadas", command=self.on_extract, state="disabled")
        self.btn_extract.grid(row=24, column=0, padx=16, pady=4, sticky="ew")
        self.btn_open = ctk.CTkButton(sb, text="Abrir pasta destino", command=self.on_open_out, state="disabled")
        self.btn_open.grid(row=25, column=0, padx=16, pady=4, sticky="ew")
        self.btn_stop = ctk.CTkButton(sb, text="Parar", command=self.on_stop, state="disabled")
        self.btn_stop.grid(row=26, column=0, padx=16, pady=4, sticky="ew")

        self.id3_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sb, text="Gravar tags ID3 (título/álbum/nº)", variable=self.id3_var).grid(
            row=27, column=0, padx=16, pady=(6, 2), sticky="w"
        )
        ctk.CTkButton(sb, text="Sair", fg_color="#C62828", hover_color="#B71C1C", command=self.destroy).grid(
            row=28, column=0, padx=16, pady=8, sticky="ew"
        )

        # Aparência
        self.theme_opt = ctk.CTkOptionMenu(sb, values=["system", "light", "dark"], command=lambda v: ctk.set_appearance_mode(v))
        self.theme_opt.set("system"); self.theme_opt.grid(row=29, column=0, padx=16, pady=4, sticky="ew")
        self.scale_opt = ctk.CTkOptionMenu(sb, values=["80%", "90%", "100%", "110%", "125%", "150%"], command=self.on_scale)
        self.scale_opt.set(self.cfg.get("scale", "80%")); self.scale_opt.grid(row=30, column=0, padx=16, pady=(0, 10), sticky="ew")

    def _build_main(self):
        main = ctk.CTkFrame(self); main.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        main.grid_rowconfigure(2, weight=1); main.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(main, text="Pronto."); self.status.grid(row=0, column=0, sticky="w")
        self.pb = ctk.CTkProgressBar(main, mode="determinate"); self.pb.grid(row=1, column=0, sticky="ew"); self.pb.set(0)

        self.split = tk.PanedWindow(main, orient="vertical"); self.split.grid(row=2, column=0, sticky="nsew", pady=(6, 0))

        # tracks
        tf = ctk.CTkFrame(self.split); self.split.add(tf, stretch="always", minsize=200)
        hdr = ctk.CTkFrame(tf); hdr.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(hdr, text="Faixas Detetadas", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.sel_all_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(hdr, text="Selecionar todas", variable=self.sel_all_var, command=self.on_toggle_all).pack(side="right")
        self.track_area = ctk.CTkScrollableFrame(tf, label_text="")
        self.track_area.pack(fill="both", expand=True, padx=6, pady=6)

        # log
        lf = ctk.CTkFrame(self.split); self.split.add(lf, minsize=90)
        lh = ctk.CTkFrame(lf); lh.pack(fill="x")
        ctk.CTkLabel(lh, text="LOG", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=6, pady=4)
        self.log = ctk.CTkTextbox(lf, height=140); self.log.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ---------- persistência ----------
    def _save_mode(self, v: str):
        self.detect_mode = v
        self.cfg["detect_mode"] = v
        save_config(self.cfg)

    def _persist_token(self):
        self.discogs_token = self.token_entry.get().strip()
        self.cfg["discogs_token"] = self.discogs_token
        save_config(self.cfg)

    def _persist_output_album(self):
        self.cfg["last_output_dir"] = self.output_dir = self.out_entry.get().strip()
        self.cfg["last_album"] = self.album_name = self.album_entry.get().strip()
        self.cfg["last_db"] = int(self.db_var.get())
        save_config(self.cfg)

    # ---------- eventos ----------
    def on_scale(self, v):
        ctk.set_widget_scaling(int(v.replace("%", "")) / 100.0)
        self.cfg["scale"] = v; save_config(self.cfg)

    def on_select_mp3(self):
        f = filedialog.askopenfilename(filetypes=[("MP3", "*.mp3")])
        if not f: return
        self.audio_file = f
        self.file_lbl.configure(text=os.path.basename(f))
        if self.out_entry.get().strip():
            self.on_detect()

    def on_choose_out(self):
        d = filedialog.askdirectory()
        if not d: return
        self.out_entry.delete(0, "end"); self.out_entry.insert(0, d)
        self._persist_output_album()
        if self.audio_file:
            self.on_detect()

    def on_toggle_all(self):
        v = bool(self.sel_all_var.get())
        for var in self.cb_vars: var.set(v)

    def v_int(self, entry, lo, hi, msg) -> Optional[int]:
        try:
            x = int(entry.get().strip())
            if not (lo <= x <= hi): raise ValueError
            return x
        except Exception:
            messagebox.showwarning("Valor inválido", msg); return None

    def on_detect(self):
        if not self.audio_file: return
        # permite 50..10000 ms
        msl = self.v_int(self.min_sil_entry, 50, 10000, "Silêncio 50..10000")
        mtk = self.v_int(self.min_track_entry, 5, 3600, "Faixa 5..3600s")
        pad = self.v_int(self.pad_entry, 0, 5000, "Padding 0..5000ms")
        if None in (msl, mtk, pad): return
        self._persist_output_album()
        self._clear_tracks()
        self.status.configure(text="A detetar faixas…"); self.pb.set(0)

        if self.detect_mode == "Avançada (sem silêncio)":
            wmode = "detect_adv"
        else:
            wmode = "detect"

        self.worker = Worker(
            wmode, self.audio_file, self.db_var.get(), msl, mtk, pad,
            None, None, None, False, self.log_q, self.prog_q, self.res_q
        )
        self.btn_stop.configure(state="normal"); self.worker.start()

    def on_extract(self):
        selected = [t for t, v in zip(self.tracks, self.cb_vars) if v.get()]
        if not selected:
            messagebox.showinfo("Nada", "Nenhuma faixa selecionada."); return
        # aplicar títulos editados
        for t, ent in zip(self.tracks, self.title_vars):
            try:
                txt = ent.get().strip()
                if txt: t.title = txt
            except Exception: pass
        outdir = self.out_entry.get().strip() or None
        album = self.album_entry.get().strip()
        if self.album_ck.get() and album:
            outdir = os.path.join(outdir, safe_name(album)) if outdir else None
        self._persist_output_album()
        self.worker = Worker(
            "extract", self.audio_file, self.db_var.get(),
            self.v_int(self.min_sil_entry, 50, 10000, "Silêncio") or 900,
            self.v_int(self.min_track_entry, 5, 3600, "Faixa") or 45,
            self.v_int(self.pad_entry, 0, 5000, "Padding") or 200,
            selected, outdir, album, bool(self.id3_var.get()),
            self.log_q, self.prog_q, self.res_q
        )
        self.status.configure(text=f"A extrair {len(selected)} faixa(s)…"); self.pb.set(0)
        self.btn_stop.configure(state="normal"); self.worker.start()

    def on_open_out(self):
        p = self.cfg.get("last_output_dir") or self.out_entry.get().strip()
        if not p or not os.path.isdir(p): messagebox.showinfo("Pasta", "Sem pasta de destino."); return
        if sys.platform.startswith("win"): os.startfile(p)
        elif sys.platform == "darwin": os.system(f"open '{p}'")
        else: os.system(f"xdg-open '{p}'")

    def on_stop(self):
        if self.worker: self.worker.stop(); self.btn_stop.configure(state="disabled")

    # ---------- Discogs ----------
    def on_discogs(self):
        if not self.tracks:
            self.log_write("ℹ️ Deteta as faixas primeiro."); return
        album = self.album_entry.get().strip()
        if not album:
            self.log_write("ℹ️ Escreve o nome do álbum (ou cola o URL de uma release do Discogs)."); return
        self._persist_token()
        threading.Thread(target=self._discogs_worker, args=(album, self.discogs_token), daemon=True).start()

    def _discogs_worker(self, album_query: str, token: str):
        """Procura release no Discogs por nome (ou URL direta de release) e aplica títulos."""
        try:
            headers = {
                "User-Agent": "ExtratorFaixas/1.0 +https://discogs.com"
            }
            # URL de release?
            m = re.search(r"discogs\.com/.*/release/(\d+)", album_query, re.I)
            release_id = m.group(1) if m else None

            if not release_id:
                # tentar artista via ffprobe (se existir nos metadados)
                artist = None
                try:
                    info = subprocess.check_output(
                        ["ffprobe","-v","error","-print_format","json","-show_format", self.audio_file], text=True, **_WIN_NO_WINDOW
                    )
                    meta = json.loads(info)
                    artist = (meta.get("format",{}).get("tags",{}) or {}).get("artist")
                except Exception:
                    pass

                params = {"q": album_query, "type": "release"}
                if artist: params["artist"] = artist
                if token: params["token"] = token

                r = requests.get("https://api.discogs.com/database/search",
                                 params=params, headers=headers, timeout=25)
                data = r.json()
                results = data.get("results") or []
                if not results:
                    self.log_write("⚠️ Discogs: sem resultados para essa pesquisa."); return

                # escolher o melhor pelo nº de faixas previsto (se existirem já faixas detetadas)
                target = len(self.tracks)
                best = None; bestdiff = 10**9
                for it in results:
                    rid = it.get("id")
                    if not rid: continue
                    # pedir release para saber a tracklist
                    r2 = requests.get(f"https://api.discogs.com/releases/{rid}",
                                      params={"token": token} if token else None,
                                      headers=headers, timeout=25)
                    rel = r2.json()
                    n = len([t for t in (rel.get("tracklist") or []) if t.get("type_", "") == "track" or "title" in t])
                    if n>0 and abs(n-target) < bestdiff:
                        bestdiff = abs(n-target); best = rel
                    if bestdiff == 0: break
                if not best:
                    self.log_write("⚠️ Discogs: não encontrei release com nº de faixas útil."); return
                release = best
            else:
                r = requests.get(f"https://api.discogs.com/releases/{release_id}",
                                 params={"token": token} if token else None,
                                 headers=headers, timeout=25)
                release = r.json()

            titles = []
            for tr in release.get("tracklist", []) or []:
                if tr.get("type_", "track").lower() != "track":
                    continue
                ttl = tr.get("title")
                if ttl: titles.append(ttl)

            if not titles:
                self.log_write("⚠️ Discogs: release sem títulos de faixas disponíveis."); return

            n = min(len(self.tracks), len(titles))
            for i in range(n):
                t = titles[i]
                self.title_vars[i].delete(0, "end"); self.title_vars[i].insert(0, t)
                self.tracks[i].title = t

            alb_title = release.get("title")
            if alb_title:
                self.album_entry.delete(0, "end"); self.album_entry.insert(0, alb_title)

            self.log_write(f"✅ Tracklist (Discogs) aplicado a {n}/{len(self.tracks)} faixas.")
        except Exception as e:
            self.log_write(f"❌ Erro Discogs: {e}")

    # ---------- tracklist manual ----------
    def on_paste_tracklist(self):
        if not self.tracks:
            messagebox.showinfo("Info", "Deteta as faixas primeiro."); return
        top = ctk.CTkToplevel(self); top.title("Colar tracklist (uma linha por faixa ou URL do Discogs)")
        top.geometry("600x420"); top.grab_set()
        txt = ctk.CTkTextbox(top); txt.pack(fill="both", expand=True, padx=10, pady=10)
        btns = ctk.CTkFrame(top); btns.pack(fill="x", padx=10, pady=(0,10))

        def apply():
            raw = txt.get("1.0","end").strip()
            # se colar uma URL de release do Discogs, processa via API
            if "discogs.com" in raw and "/release/" in raw:
                top.destroy()
                self._persist_token()
                threading.Thread(target=self._discogs_worker, args=(raw, self.discogs_token), daemon=True).start()
                return

            lines = raw.splitlines()
            titles=[]
            for line in lines:
                s=line.strip()
                if not s: continue
                s=re.sub(r"^\s*\d+\s*[-.)]\s*", "", s)   # remove "01 - ", "1. "
                s=re.sub(r"^\s*Faixa\s*\d+\s*[-:]*\s*", "", s, flags=re.I)
                titles.append(s)
            n=min(len(titles), len(self.tracks))
            for i in range(n):
                self.title_vars[i].delete(0,"end"); self.title_vars[i].insert(0,titles[i])
                self.tracks[i].title = titles[i]
            self.log_write(f"📝 Tracklist manual aplicado a {n}/{len(self.tracks)} faixas.")
            top.destroy()

        ctk.CTkButton(btns, text="Aplicar", command=apply).pack(side="right")
        ctk.CTkButton(btns, text="Cancelar", command=top.destroy, fg_color="gray").pack(side="right", padx=8)

    # ---------- loop ----------
    def _poll(self):
        try:
            while True: self.log_write(self.log_q.get_nowait())
        except queue.Empty: pass
        try:
            p=None
            while True: p=self.prog_q.get_nowait()
        except queue.Empty: pass
        if p is not None: self.pb.set(p)
        try:
            while True:
                res=self.res_q.get_nowait(); t=res.get("type")
                if t=="detected":
                    self.tracks=res.get("tracks",[])
                    if res.get("album"):
                        self.album_entry.delete(0,"end"); self.album_entry.insert(0,res["album"])
                    self._populate_tracks()
                    self.btn_stop.configure(state="disabled")
                    self.status.configure(text=f"{len(self.tracks)} faixas detetadas.")
                elif t=="extracted":
                    out=res.get("output_dir")
                    if out:
                        self.cfg["last_output_dir"]=out; save_config(self.cfg)
                        self.btn_open.configure(state="normal")
                    self.status.configure(text="Extração concluída.")
                    self.btn_stop.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._poll)

    def _populate_tracks(self):
        self._clear_tracks()
        for tr in self.tracks:
            row=ctk.CTkFrame(self.track_area); row.pack(fill="x", padx=6, pady=2)
            left=ctk.CTkFrame(row); left.pack(side="left", fill="x", expand=True)
            right=ctk.CTkFrame(row, width=220); right.pack(side="right", fill="x")
            var=ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(left, text=f"✓  {tr.duration:.2f}", variable=var).pack(anchor="w")
            ent=ctk.CTkEntry(right); ent.insert(0,tr.title); ent.pack(fill="x", padx=4)
            self.cb_vars.append(var); self.title_vars.append(ent)
        self.sel_all_var.set(True); self.btn_extract.configure(state="normal" if self.tracks else "disabled")

    def _clear_tracks(self):
        for w in self.track_area.winfo_children(): w.destroy()
        self.cb_vars.clear(); self.title_vars.clear()

    def log_write(self, msg: str):
        self.log.insert("end", msg + "\n"); self.log.see("end")


if __name__ == "__main__":
    App().mainloop()
