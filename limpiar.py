import py_compile
import shutil
import sys
from pathlib import Path

OBJ = Path("stealer.py")
if not OBJ.exists():
    sys.exit("no existe stealer.py en esta carpeta")

original = OBJ.read_text(encoding="utf-8", errors="ignore")
shutil.copy2(OBJ, OBJ.with_suffix(".sucio"))

lineas = original.splitlines()
antes = len(lineas)
limpias = [l for l in lineas if not l.strip().startswith("```")]
quitadas = antes - len(limpias)
texto = "\n".join(limpias) + "\n"

pos, i = [], texto.find("STEALER v2.5")
while i != -1:
    pos.append(i)
    i = texto.find("STEALER v2.5", i + 1)

recortado = 0
if len(pos) > 1:
    texto = texto[:pos[1]]
    recortado = len(pos) - 1
    cola = texto.splitlines()
    while cola and cola[-1].strip() in ("", '"""', "```"):
        cola.pop()
    texto = "\n".join(cola) + "\n"

if "main()" not in texto.splitlines()[-3:]:
    sys.exit("el final del archivo no queda bien; no toco nada")

OBJ.write_text(texto, encoding="utf-8")
try:
    py_compile.compile(str(OBJ), doraise=True)
except Exception as e:
    OBJ.write_text(original, encoding="utf-8")
    sys.exit(f"no compila tras limpiar, restaurado: {e}")

print(f"fences quitadas  : {quitadas}")
print(f"copias eliminadas: {recortado}")
print(f"lineas           : {antes} -> {texto.count(chr(10))}")
print("OK, compila limpio")