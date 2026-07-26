#!/usr/bin/env python3
"""
Plexglobe · generador de contenido social.

Renderiza TODAS las piezas del banco y escribe dos ficheros:

  salida/catalogo.json   las 4 semanas completas  -> alimenta la galeria de revision
  salida/manifest.json   solo la semana que toca  -> lo consume Make para publicar

Uso:
    python3 generar.py                 # todo, y el manifest de la semana en curso
    python3 generar.py --semana 3      # forzar que el manifest sea el de la semana 3
"""
import argparse
import datetime as dt
import json
import os

import plexglobe_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "salida")

REPO = os.environ.get("GITHUB_REPOSITORY", "ERNESTOTALIB/plexglobe-social")
RAMA = os.environ.get("GITHUB_REF_NAME", "main")
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/salida"


def semana_actual(total):
    return (dt.date.today().isocalendar()[1] - 1) % total + 1


def hashtags(banco, grupos):
    tags = []
    for g in grupos:
        tags.extend(banco.get(g, []))
    return list(dict.fromkeys(tags))


def render(post):
    t = post["plantilla"]
    if t == "A":
        return R.tpl_a_propuesta(post["titular"], post.get("sub", "")), "4x5"
    if t == "B":
        return R.tpl_b_caso(post["titulo_caso"], post.get("sub", ""), post["metrica"]), "4x5"
    if t == "D":
        return R.tpl_d_carrusel(post["titular"], kicker=post.get("kicker", "CARRUSEL · TIP"),
                                page=post.get("pagina")), "4x5"
    if t == "E":
        return R.tpl_e_testimonial(post["titular"], post.get("autor"), post.get("sub")), "4x5"
    if t == "F":
        return R.tpl_f_auditoria(post["titular"],
                                 kicker=post.get("kicker", "SIN COSTE · SIN COMPROMISO"),
                                 cta=post.get("cta", "DM: «AUDIT»")), "4x5"
    if t == "STORY":
        return R.tpl_story(post["titular"], kicker=post.get("kicker", "DETRÁS DE CÁMARAS"),
                           foot=post.get("pie", "Desliza arriba → auditoría gratis")), "9x16"
    raise ValueError(f"Plantilla desconocida: {t!r} en {post['id']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semana", type=int)
    args = ap.parse_args()

    with open(os.path.join(HERE, "contenido.json"), encoding="utf-8") as f:
        data = json.load(f)

    posts = data["posts"]
    semanas = sorted({p["semana"] for p in posts})
    sem = args.semana or semana_actual(len(semanas))

    os.makedirs(OUT, exist_ok=True)
    catalogo = []

    for p in posts:
        img, sufijo = render(p)
        nombre = f"{p['id']}_{sufijo}.jpg"
        img.convert("RGB").save(os.path.join(OUT, nombre), "JPEG", quality=92, subsampling=0)

        catalogo.append({
            "id": p["id"],
            "semana": p["semana"],
            "dia": p["dia"],
            "formato": p["formato"],
            "plantilla": p["plantilla"],
            "medida": "1080×1350" if sufijo == "4x5" else "1080×1920",
            "imagen_url": f"{BASE_URL}/{nombre}",
            "caption": p["caption"].strip() + "\n\n" + " ".join(hashtags(data["hashtags"], p.get("tags", ["base"]))),
            "aprobado": "",
            "publicado_ig": "",
            "publicado_fb": "",
        })
        print(f"  ✓ {nombre}")

    with open(os.path.join(OUT, "catalogo.json"), "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    manifest = [c for c in catalogo if c["semana"] == sem]
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\ncatalogo.json → {len(catalogo)} piezas (las 4 semanas)")
    print(f"manifest.json → {len(manifest)} piezas (semana {sem}, la que publica Make)")
    print(f"URL base: {BASE_URL}")


if __name__ == "__main__":
    main()
