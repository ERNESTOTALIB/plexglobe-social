#!/usr/bin/env python3
"""
Plexglobe · generador semanal de contenido social.

Lee contenido.json, renderiza las 7 piezas de la semana que toca y escribe
salida/manifest.json con la URL publica de cada imagen + el copy listo.

Ese manifest es lo que consume Make para publicar en Instagram y Facebook.

Uso:
    python3 generar.py                 # semana automatica (rota cada 4)
    python3 generar.py --semana 2      # forzar una semana concreta
    python3 generar.py --todo          # renderizar las 4 semanas de golpe
"""
import argparse
import datetime as dt
import json
import os
import sys

import plexglobe_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "salida")

# Se rellena desde la variable de entorno GITHUB_REPOSITORY en Actions.
REPO = os.environ.get("GITHUB_REPOSITORY", "USUARIO/plexglobe-social")
RAMA = os.environ.get("GITHUB_REF_NAME", "main")
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/salida"


def semana_actual(total_semanas):
    """Rota por numero de semana ISO: 1..total_semanas."""
    return (dt.date.today().isocalendar()[1] - 1) % total_semanas + 1


def construir_hashtags(banco, grupos):
    tags = []
    for g in grupos:
        tags.extend(banco.get(g, []))
    # sin duplicados, conservando orden
    return list(dict.fromkeys(tags))


def render(post):
    """Devuelve (imagen, sufijo) segun la plantilla indicada en el JSON."""
    t = post["plantilla"]

    if t == "A":
        return R.tpl_a_propuesta(post["titular"], post.get("sub", "")), "4x5"
    if t == "B":
        return R.tpl_b_caso(post["titulo_caso"], post.get("sub", ""),
                            post["metrica"]), "4x5"
    if t == "D":
        return R.tpl_d_carrusel(post["titular"],
                                kicker=post.get("kicker", "CARRUSEL · TIP"),
                                page=post.get("pagina")), "4x5"
    if t == "E":
        return R.tpl_e_testimonial(post["titular"], post.get("autor"),
                                   post.get("sub")), "4x5"
    if t == "F":
        return R.tpl_f_auditoria(post["titular"],
                                 kicker=post.get("kicker", "SIN COSTE · SIN COMPROMISO"),
                                 cta=post.get("cta", "DM: «AUDIT»")), "4x5"
    if t == "STORY":
        return R.tpl_story(post["titular"],
                           kicker=post.get("kicker", "DETRÁS DE CÁMARAS"),
                           foot=post.get("pie", "Desliza arriba → auditoría gratis")), "9x16"

    raise ValueError(f"Plantilla desconocida: {t!r} en el post {post['id']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semana", type=int)
    ap.add_argument("--todo", action="store_true")
    args = ap.parse_args()

    with open(os.path.join(HERE, "contenido.json"), encoding="utf-8") as f:
        data = json.load(f)

    posts = data["posts"]
    semanas = sorted({p["semana"] for p in posts})

    if args.todo:
        elegidos = posts
        etiqueta = "todas"
    else:
        sem = args.semana or semana_actual(len(semanas))
        elegidos = [p for p in posts if p["semana"] == sem]
        etiqueta = f"semana {sem}"
        if not elegidos:
            sys.exit(f"No hay posts para la semana {sem}. Semanas disponibles: {semanas}")

    os.makedirs(OUT, exist_ok=True)
    manifest = []

    for p in elegidos:
        img, sufijo = render(p)
        nombre = f"{p['id']}_{sufijo}.jpg"
        ruta = os.path.join(OUT, nombre)
        img.convert("RGB").save(ruta, "JPEG", quality=92, subsampling=0)

        tags = construir_hashtags(data["hashtags"], p.get("tags", ["base"]))
        manifest.append({
            "id": p["id"],
            "semana": p["semana"],
            "dia": p["dia"],
            "formato": p["formato"],
            "plantilla": p["plantilla"],
            "imagen_url": f"{BASE_URL}/{nombre}",
            "caption": p["caption"].strip() + "\n\n" + " ".join(tags),
            "aprobado": "",          # <- lo rellenas tu en la hoja: SI / NO
            "publicado_ig": "",
            "publicado_fb": "",
        })
        print(f"  ✓ {nombre}")

    ruta_manifest = os.path.join(OUT, "manifest.json")
    with open(ruta_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n{len(manifest)} piezas generadas ({etiqueta})")
    print(f"manifest: {ruta_manifest}")
    print(f"URL base: {BASE_URL}")


if __name__ == "__main__":
    main()
