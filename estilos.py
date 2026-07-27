#!/usr/bin/env python3
"""
Plexglobe · estilos visuales con foto.

Cuatro tratamientos que se van alternando a lo largo de la semana, sobre el
mismo sistema de marca del PDF. Conviven con las plantillas clasicas
(solo tipografia) de plexglobe_render.py.

  A  foto a sangre + degradado      4:5 y 9:16   necesita foto
  B  split: captura arriba + datos  4:5          necesita captura de producto
  C  dato gigante                   4:5 y 9:16   la foto es opcional
  D  duotono de marca + red         4:5 y 9:16   necesita foto
"""
import os
import random

from PIL import Image
from PIL import ImageDraw as ID

from plexglobe_render import (CREAM, INK, CLAY, FEED, STORY, SAFE_TOP, SAFE_BOTTOM,
                              grotesk, manrope, mono, rich_lines, draw_rich,
                              tracked, pill, badge_pg)

HERE = os.path.dirname(os.path.abspath(__file__))
FOTOS = os.path.join(HERE, "fotos")


# ---------------------------------------------------------------- utilidades
def foto(nombre, size=FEED, foco=0.35):
    """Carga y recorta al encuadre pedido sin deformar."""
    im = Image.open(os.path.join(FOTOS, nombre)).convert("RGB")
    tw, th = size
    r = max(tw / im.width, th / im.height)
    im = im.resize((max(tw, int(im.width * r + 1)), max(th, int(im.height * r + 1))), Image.LANCZOS)
    x = (im.width - tw) // 2
    y = int((im.height - th) * foco)
    return im.crop((x, y, x + tw, y + th)).convert("RGBA")


def grano(img, fuerza=13, opacidad=26):
    """Grano fino: le quita el aspecto de plantilla."""
    w, h = img.size
    r = Image.effect_noise((w, h), fuerza).convert("L")
    img.alpha_composite(Image.merge("RGBA", (r, r, r, Image.new("L", (w, h), opacidad))))


def scrim(img, desde=0.30, opacidad=238, color=(18, 15, 12)):
    """Degradado inferior para que el texto se lea sobre cualquier foto."""
    w, h = img.size
    g = Image.new("L", (1, h))
    for y in range(h):
        t = (y / h - desde) / (1 - desde)
        g.putpixel((0, y), 0 if t < 0 else min(255, int(opacidad * (t ** 1.5))))
    m = g.resize((w, h))
    img.alpha_composite(Image.merge("RGBA", (
        Image.new("L", (w, h), color[0]), Image.new("L", (w, h), color[1]),
        Image.new("L", (w, h), color[2]), m)))


def duotono(im, oscuro=(16, 13, 11), claro=(226, 210, 190), mezcla=0.92):
    """Duotono de marca: unifica fotos muy distintas bajo la misma paleta."""
    g = im.convert("L")
    pal = []
    for i in range(256):
        t = i / 255
        pal += [int(oscuro[c] + (claro[c] - oscuro[c]) * t) for c in range(3)]
    duo = g.convert("P")
    duo.putpalette(pal)
    return Image.blend(im.convert("RGB"), duo.convert("RGB"), mezcla).convert("RGBA")


def red_nodos(img, color, n=28, alpha=62, radio=5, semilla=7):
    """El motivo de marca dibujado como red, no como trama de puntos."""
    random.seed(semilla)
    w, h = img.size
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ID.Draw(capa)
    pts = [(random.randint(60, w - 60), random.randint(60, h - 60)) for _ in range(n)]
    for a in pts:
        for b in sorted(pts, key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)[1:3]:
            d.line([a, b], fill=color + (int(alpha * 0.45),), width=1)
    for (x, y) in pts:
        d.ellipse([x - radio, y - radio, x + radio, y + radio], fill=color + (alpha,))
    img.alpha_composite(capa)


def _pie_carrusel(d, size, pagina):
    """Flecha y paginacion, para cuando el estilo hace de portada de carrusel."""
    M = 84
    d.text((M, size[1] - M - 52), "→", font=grotesk(58, 600), fill=CLAY)
    if pagina:
        f = mono(24)
        tw = sum(d.textlength(c, font=f) + 5 for c in pagina)
        tracked(d, (size[0] - M - tw, size[1] - M - 30), pagina, f, (196, 182, 164), 5)


# ---------------------------------------------------------------- estilos
def estilo_a(titular, img_nombre, kicker=None, sub=None, pie=None,
             vertical=False, foco=0.15, pagina=None):
    """A · Foto a sangre. La mas vistosa: solo si la foto acompaña."""
    size = STORY if vertical else FEED
    im = foto(img_nombre, size, foco=foco)
    scrim(im, desde=0.24, opacidad=242)
    grano(im)
    d = ID.Draw(im)
    M = 90 if vertical else 84
    top = SAFE_TOP if vertical else 96

    if kicker:
        pill(d, (M, top), kicker, mono(24, bold=True), CLAY, (255, 255, 255), padx=22, pady=12)

    cuerpo = 118 if vertical else 114
    lines = rich_lines(d, titular, size[0] - M * 2, cuerpo)
    base = (SAFE_BOTTOM + 210) if vertical else 300
    y = draw_rich(d, lines, M, size[1] - base - int(len(lines) * cuerpo * 1.1),
                  cuerpo, CREAM, leading=1.1, italic_color=(255, 196, 160))
    y += 40

    for i, ln in enumerate((sub or "").split("\n")):
        if ln:
            d.text((M, y + i * 48), ln, font=manrope(33, 500), fill=(230, 220, 206))

    if pagina:
        _pie_carrusel(d, size, pagina)
    else:
        by = size[1] - (SAFE_BOTTOM if vertical else M) - 64
        badge_pg(d, (M, by), bg=CREAM, fg=INK)
        d.text((M + 86, by + 14), pie or "Plexglobe", font=manrope(32, 700), fill=CREAM)
    return im


def estilo_b(titular, img_nombre, datos, kicker="CASO", foco=0.0, pagina=None):
    """B · Captura del producto arriba + tres cifras abajo. Cero hueco muerto."""
    im = Image.new("RGBA", FEED, CREAM + (255,))
    im.paste(foto(img_nombre, (FEED[0], 700), foco=foco), (0, 0))
    d = ID.Draw(im)
    M = 84

    pill(d, (M, 62), kicker, mono(24, bold=True), INK, CREAM, padx=22, pady=12)

    cuerpo = 84
    lines = rich_lines(d, titular, FEED[0] - M * 2, cuerpo)
    y = draw_rich(d, lines, M, 762, cuerpo, INK, leading=1.12, italic_color=CLAY) + 54

    ancho = (FEED[0] - M * 2) // max(1, len(datos))
    for i, (num, txt) in enumerate(datos):
        x = M + i * ancho
        if i:
            d.line([(x - 24, y + 4), (x - 24, y + 128)], fill=(214, 203, 186), width=2)
        d.text((x, y), num, font=grotesk(62, 700), fill=CLAY)
        d.text((x, y + 82), txt, font=manrope(25, 500), fill=(110, 98, 86))

    if pagina:
        _pie_carrusel(d, FEED, pagina)
    else:
        badge_pg(d, (M, FEED[1] - M - 64))
        d.text((M + 86, FEED[1] - M - 50), "Plexglobe", font=manrope(32, 600), fill=INK)
    return im


def estilo_c(dato, titular, kicker="", img_nombre=None, pie="plexglobe.com",
             vertical=False, pagina=None):
    """C · El dato manda. Es el unico que se lee siendo una miniatura."""
    size = STORY if vertical else FEED
    im = Image.new("RGBA", size, CLAY + (255,))
    red_nodos(im, CREAM, n=30, alpha=58)
    grano(im, 10, 22)
    d = ID.Draw(im)
    M = 90 if vertical else 84
    top = SAFE_TOP if vertical else 118

    if kicker:
        tracked(d, (M, top), kicker, mono(25), (252, 231, 220), 7)

    # el numeral se escala para no salirse nunca del margen
    tam = 330
    while d.textlength(dato, font=grotesk(tam, 700)) > size[0] - M * 2 and tam > 120:
        tam -= 10
    d.text((M - int(tam * 0.05), top + 92), dato, font=grotesk(tam, 700), fill=CREAM)

    cuerpo = 72
    lines = rich_lines(d, titular, size[0] - M * 2, cuerpo)
    draw_rich(d, lines, M, top + 92 + int(tam * 1.18), cuerpo, CREAM,
              leading=1.14, italic_color=(255, 214, 190))

    if img_nombre:
        lado = 300
        mini = foto(img_nombre, (lado, lado), foco=0.2)
        mask = Image.new("L", (lado, lado), 0)
        ID.Draw(mask).rounded_rectangle([0, 0, lado - 1, lado - 1], radius=22, fill=255)
        im.paste(mini.convert("RGB"),
                 (size[0] - M - lado, size[1] - (SAFE_BOTTOM if vertical else M) - lado - 60), mask)

    if pagina:
        _pie_carrusel(d, size, pagina)
    else:
        by = size[1] - (SAFE_BOTTOM if vertical else M) - 40
        d.text((M, by), pie, font=manrope(30, 500), fill=(252, 231, 220))
    return im


def estilo_d(titular, img_nombre, kicker="ESTUDIO DIGITAL · EE.UU. → GLOBAL",
             sub=None, cta=None, vertical=False, foco=0.3, pagina=None):
    """D · Duotono de marca + red de nodos. Unifica fotos dispares."""
    size = STORY if vertical else FEED
    im = duotono(foto(img_nombre, size, foco=foco))
    im.alpha_composite(Image.new("RGBA", size, CLAY + (46,)))
    scrim(im, desde=0.10, opacidad=252)
    red_nodos(im, CREAM, n=26, alpha=64)
    grano(im, 12)
    d = ID.Draw(im)
    M = 90 if vertical else 84
    top = SAFE_TOP if vertical else 118

    d.ellipse([M, top + 6, M + 15, top + 21], fill=CLAY)
    tracked(d, (M + 32, top), kicker, mono(23), CREAM, 5)

    cuerpo = 118
    lines = rich_lines(d, titular, size[0] - M * 2, cuerpo)
    base = (SAFE_BOTTOM + 230) if vertical else 300
    y = draw_rich(d, lines, M, size[1] - base - int(len(lines) * cuerpo * 1.1),
                  cuerpo, CREAM, leading=1.1, italic_color=(255, 200, 168)) + 66

    if sub:
        d.text((M, y), sub, font=manrope(35, 500), fill=(228, 216, 202))
        y += 62
    if cta:
        pill(d, (M, y), cta, mono(26, bold=True), CREAM, INK)

    if pagina:
        _pie_carrusel(d, size, pagina)
    return im
