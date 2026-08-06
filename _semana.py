#!/usr/bin/env python3
"""Renderiza los reels de una semana y arma la galeria de revision local."""
import json, io, os, sys
import video as V

SEM = int(sys.argv[1]) if len(sys.argv) > 1 else 1
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(io.open(f"{HERE}/contenido.json", encoding="utf-8"))
posts = [p for p in d["posts"] if p["semana"] == SEM and not p.get("alternativa")]

hechos = []
for p in posts:
    if "Reel" not in p["formato"] and p["plantilla"] != "STORY":
        continue
    if p["id"] in ("S1-M",):     # ya tiene reel propio hecho a mano
        pass
    spec = {"fn": V.hacer_frame_generico(p), "dur": 14.0, "titulo": p["titular"]}
    print(f"\n{p['id']} · {p['titular'][:46]}")
    V.encode(f"P-{p['id']}", spec)
    V.portada(f"P-{p['id']}", spec, 2.6)
    hechos.append(p["id"])
print("\nreels generados:", hechos)
