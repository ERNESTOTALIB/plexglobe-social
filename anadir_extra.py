#!/usr/bin/env python3
"""
Anade al catalogo las series hechas FUERA del generador (p. ej. los reels con
planos de Kling y la app animada, que no se pueden renderizar en Actions).

Lee cada extra/<serie>/serie.json (una lista de piezas con el mismo formato que
el catalogo) y las mete en salida/catalogo.json.

Se ejecuta DESPUES de generar.py y de anadir_lista.py: generar.py reescribe el
catalogo entero desde contenido.json, asi que si esto corriera antes, se lo
llevaria por delante cada domingo.

Conserva aprobado / publicado_ig / publicado_fb de las piezas que ya estaban:
si no, cada render semanal borraria lo que ya se hubiera decidido.
"""
import glob
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(AQUI, "salida", "catalogo.json")
ESTADO = ("aprobado", "publicado_ig", "publicado_fb")


def main():
    cat = json.load(open(CAT, encoding="utf-8")) if os.path.exists(CAT) else []
    por_id = {c["id"]: c for c in cat}
    n = 0
    for ruta in sorted(glob.glob(os.path.join(AQUI, "extra", "*", "serie.json"))):
        for pieza in json.load(open(ruta, encoding="utf-8")):
            viejo = por_id.get(pieza["id"], {})
            nuevo = dict(pieza)
            for k in ESTADO:
                nuevo[k] = viejo.get(k, pieza.get(k, ""))
            por_id[nuevo["id"]] = nuevo
            n += 1
    salida = sorted(por_id.values(), key=lambda c: (c.get("semana", 99), c["id"]))
    json.dump(salida, open(CAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("catalogo: %d piezas (%d de series extra)" % (len(salida), n))


if __name__ == "__main__":
    main()
