"""
Sistema de tooltips reutilizável para o Assistente Virtual.
Uso:
    from tooltip import Tooltip
    Tooltip(widget, "Texto de ajuda")
"""
import tkinter as tk
import customtkinter as ctk


class Tooltip:
    """
    Tooltip simples que aparece ao passar o rato sobre um widget.
    Compatível com tkinter e customtkinter.
    """

    def __init__(self, widget, texto: str, delay: int = 600):
        """
        Args:
            widget:  Widget ao qual associar o tooltip
            texto:   Texto a mostrar
            delay:   Atraso em ms antes de aparecer (padrão 600ms)
        """
        self.widget = widget
        self.texto = texto
        self.delay = delay
        self._job = None
        self._win = None

        widget.bind("<Enter>",  self._agendar, add="+")
        widget.bind("<Leave>",  self._cancelar, add="+")
        widget.bind("<Button>", self._cancelar, add="+")

    def _agendar(self, event=None):
        self._cancelar()
        self._job = self.widget.after(self.delay, self._mostrar)

    def _cancelar(self, event=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        self._esconder()

    def _mostrar(self):
        if self._win:
            return

        # Posição: logo abaixo do widget
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except Exception:
            return

        self._win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # sem barra de título
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        # Cor conforme tema
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            bg, fg, border = "#2b2b2b", "#ffffff", "#555555"
        else:
            bg, fg, border = "#ffffe0", "#000000", "#aaaaaa"

        frame = tk.Frame(tw, background=border, bd=1)
        frame.pack()

        lbl = tk.Label(
            frame,
            text=self.texto,
            background=bg,
            foreground=fg,
            font=("Segoe UI", 10),
            padx=8,
            pady=4,
            justify="left",
            wraplength=280,
        )
        lbl.pack()

    def _esconder(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
