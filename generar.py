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
import estilos as E

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "salida")

REPO = os.environ.get("GITHUB_REPOSITORY", "ERNESTOTALIB/plexglobe-social")
RAMA = os.environ.get("GITHUB_REF_NAME", "main")
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/salida"


def semana_actual(total):
    return (dt.date.today().isocalendar()[1] - 1) % total + 1


TOPE_HASHTAGS = 5


def hashtags(banco, grupos):
    """Devuelve como mucho 5.

    Instagram limita a 5 por publicacion y pasar de ahi marca el post como de
    baja intencion: se muestra menos, no mas. Antes concatenabamos grupos y
    saliamos con 9-10, que era justo lo contrario de lo que hace falta.
    """
    tags = []
    for g in grupos:
        tags.extend(banco.get(g, []))
    return [t for t in dict.fromkeys(tags) if t.startswith("#")][:TOPE_HASHTAGS]


def render(post):
    """Si el post trae 'estilo', manda el estilo con foto. Si no, la plantilla clasica."""
    est = post.get("estilo")
    vert = post["plantilla"] == "STORY"
    suf = "9x16" if vert else "4x5"
    pag = post.get("pagina")

    if est == "A":
        return E.estilo_a(post["titular"], post["foto"], kicker=post.get("kicker"),
                          sub=post.get("sub"), vertical=vert,
                          foco=post.get("foco", 0.15), pagina=pag), suf
    if est == "B":
        return E.estilo_b(post["titular"], post["foto"], post["datos"],
                          kicker=post.get("kicker", "CASO"),
                          foco=post.get("foco", 0.0), pagina=pag), "4x5"
    if est == "C":
        return E.estilo_c(post["dato"], post["titular"], kicker=post.get("kicker", ""),
                          img_nombre=post.get("foto"), pie=post.get("pie", "plexglobe.com"),
                          vertical=vert, pagina=pag), suf
    if est == "E":
        return E.estilo_e_informe(post["titular"], post.get("sub"), post["url"],
                                  post["nota"], [tuple(l) for l in post["lineas"]],
                                  cta=post.get("cta", "FREE AUDIT · DM «AUDIT»"),
                                  pagina=pag), "4x5"
    if est == "D":
        return E.estilo_d(post["titular"], post["foto"],
                          kicker=post.get("kicker", "DIGITAL STUDIO · MIAMI → GLOBAL"),
                          sub=post.get("sub"), cta=post.get("cta"), vertical=vert,
                          foco=post.get("foco", 0.3), pagina=pag), suf

    t = post["plantilla"]
    if t == "A":
        return R.tpl_a_propuesta(post["titular"], post.get("sub", "")), "4x5"
    if t == "B":
        return R.tpl_b_caso(post["titulo_caso"], post.get("sub", ""), post["metrica"]), "4x5"
    if t == "D":
        return R.tpl_d_carrusel(post["titular"], kicker=post.get("kicker", "GOT A WEBSITE? READ THIS"),
                                page=post.get("pagina")), "4x5"
    if t == "E":
        return R.tpl_e_testimonial(post["titular"], post.get("autor"), post.get("sub")), "4x5"
    if t == "F":
        return R.tpl_f_auditoria(post["titular"],
                                 kicker=post.get("kicker", "NO COST · NO STRINGS"),
                                 cta=post.get("cta", "DM: «AUDIT»")), "4x5"
    if t == "STORY":
        return R.tpl_story(post["titular"], kicker=post.get("kicker", "BEHIND THE SCENES"),
                           foot=post.get("pie", "Swipe up → free audit")), "9x16"
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

    def guardar(img, nombre):
        img.convert("RGB").save(os.path.join(OUT, nombre), "JPEG", quality=92, subsampling=0)
        print(f"  ✓ {nombre}")
        return f"{BASE_URL}/{nombre}"

    for p in posts:
        img, sufijo = render(p)
        urls = [guardar(img, f"{p['id']}_{sufijo}.jpg")]

        # carrusel completo: portada + 3 puntos + cierre (estructura del PDF)
        slides = p.get("slides") or []
        total = len(slides) + 2 if slides else 1
        for s in slides:
            pag = f"{s['n'] + 1} / {total}"
            urls.append(guardar(
                R.tpl_carrusel_punto(s["n"], s["titulo"], s["cuerpo"], pagina=pag),
                f"{p['id']}-{s['n'] + 1}_4x5.jpg"))
        if slides:
            urls.append(guardar(
                R.tpl_carrusel_cierre(p.get("cierre", "A *free* check of your site"),
                                      pagina=f"{total} / {total} · LAST"),
                f"{p['id']}-{total}_4x5.jpg"))

        # si existe el mp4 de esa pieza, el catalogo lo enlaza: asi el
        # dashboard puede reproducirlo en vez de pintar solo la portada
        video = None
        for nombre in (f"REEL-P-{p['id']}_9x16.mp4", f"REEL-{p['id']}_9x16.mp4"):
            if os.path.exists(os.path.join(OUT, nombre)):
                video = f"{BASE_URL}/{nombre}"
                break

        catalogo.append({
            "id": p["id"],
            "semana": p["semana"],
            "dia": p["dia"],
            "idioma": p.get("idioma", "es"),
            "alternativa": bool(p.get("alternativa")),
            "serie": p.get("serie", ""),
            "formato": p["formato"],
            "plantilla": p["plantilla"],
            "medida": "1080×1350" if sufijo == "4x5" else "1080×1920",
            "diapositivas": len(urls),
            "imagen_url": urls[0],
            "imagenes": urls,
            "video_url": video,
            "caption": p["caption"].strip() + "\n\n" + " ".join(hashtags(data["hashtags"], p.get("tags", ["base"]))),
            "aprobado": "",
            "publicado_ig": "",
            "publicado_fb": "",
        })

    with open(os.path.join(OUT, "catalogo.json"), "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    # las alternativas (p. ej. la version en ingles) viven en la galeria para
    # que elijais, pero nunca entran en lo que publica Make automaticamente
    manifest = [c for c in catalogo if c["semana"] == sem and not c["alternativa"]]
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\ncatalogo.json → {len(catalogo)} piezas (las 4 semanas)")
    print(f"manifest.json → {len(manifest)} piezas (semana {sem}, la que publica Make)")
    print(f"URL base: {BASE_URL}")


if __name__ == "__main__":
    main()
