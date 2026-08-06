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


def estilo_b(titular, img_nombre, datos, kicker="CASE", foco=0.0, pagina=None):
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


def estilo_d(titular, img_nombre, kicker="DIGITAL STUDIO · MIAMI → GLOBAL",
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


# ---------------------------------------------------------------- E · informe
def _dial(d, cx, cy, r, valor, grosor=26, fondo=(58, 50, 42)):
    """Anillo de puntuacion. El arco se pinta con arc(), no con pieslice, para
    que el hueco central quede limpio sin tener que tapar nada encima."""
    caja = [cx - r, cy - r, cx + r, cy + r]
    d.arc(caja, 0, 360, fill=fondo, width=grosor)
    fin = -90 + 360 * (valor / 100)
    d.arc(caja, -90, fin, fill=CLAY, width=grosor)


def estilo_e_informe(titular, sub, url, nota, lineas, cta="FREE AUDIT · DM «AUDIT»",
                     pagina=None):
    """
    E · Informe — titular arriba, maqueta de informe en el centro, barra de CTA
    abajo. Es la estructura que mejor funciona en el feed: se entiende entera en
    miniatura, sin leer una palabra.

    `lineas` = [(etiqueta, valor 0-100), ...]  maximo 4.
    """
    img = Image.new("RGBA", FEED, INK + (255,))
    red_nodos(img, CREAM, n=26, alpha=30, semilla=3)
    d = ID.Draw(img)
    M, W, H = 84, FEED[0], FEED[1]

    PANEL = (360, 1120)          # el panel manda: todo lo demas se ajusta a el
    CTA_Y = H - 160

    # --- titular ---------------------------------------------------------
    badge_pg(d, (W - M - 56, 92), size=56, bg=CREAM, fg=INK)
    lines = rich_lines(d, titular, W - M * 2 - 90, 84)
    y = draw_rich(d, lines, M, 88, 84, CREAM, leading=1.1, italic_color=CLAY)
    if sub:
        d.text((M, y + 12), sub, font=manrope(34, 500), fill=(186, 174, 160))

    # --- panel del informe ----------------------------------------------
    px0, px1, py0, py1 = M, W - M, PANEL[0], PANEL[1]
    d.rounded_rectangle([px0, py0, px1, py1], radius=26, fill=(38, 33, 27))
    bx0, bx1 = px0 + 30, px1 - 30

    by0 = py0 + 28                                   # barra de direccion
    d.rounded_rectangle([bx0, by0, bx1, by0 + 62], radius=12, fill=(52, 45, 38))
    d.ellipse([bx0 + 20, by0 + 24, bx0 + 34, by0 + 38], outline=(150, 138, 124), width=2)
    d.text((bx0 + 52, by0 + 14), url, font=manrope(30, 500), fill=(206, 195, 180))

    cx, cy, r = W // 2, by0 + 62 + 30 + 100, 100     # dial
    _dial(d, cx, cy, r, nota, grosor=24)
    fn = grotesk(96, 700)
    d.text((cx - d.textlength(str(nota), font=fn) / 2, cy - 68), str(nota), font=fn, fill=CREAM)
    fs = manrope(32, 500)
    d.text((cx - d.textlength("/100", font=fs) / 2, cy + 30), "/100", font=fs, fill=(160, 148, 134))
    fe = mono(23)
    et = "OVERALL SCORE"
    tw = sum(d.textlength(c, font=fe) + 5 for c in et)
    tracked(d, (cx - tw / 2, cy + r + 18), et, fe, (150, 138, 124), 5)

    ly = cy + r + 66                                  # desglose
    for etiqueta, val in lineas[:4]:
        d.rounded_rectangle([bx0, ly, bx1, ly + 76], radius=12, fill=(48, 42, 35))
        d.text((bx0 + 24, ly + 20), etiqueta, font=manrope(33, 600), fill=(214, 203, 186))
        col = CLAY if val < 70 else (126, 176, 122)
        fv = grotesk(36, 700)
        d.text((bx1 - 24 - d.textlength(str(val), font=fv), ly + 16), str(val), font=fv, fill=col)
        ly += 86

    # --- barra de llamada a la accion ------------------------------------
    d.rectangle([0, CTA_Y, W, H], fill=CLAY)
    f = mono(38, bold=True)
    tw = sum(d.textlength(c, font=f) + 7 for c in cta) - 7
    tracked(d, ((W - tw) / 2, CTA_Y + 54), cta, f, CREAM, 7)

    if pagina:
        _pie_carrusel(d, FEED, pagina)
    return img


# ---------------------------------------------------------------- F · oferta
def _icono(d, cx, cy, tipo, color, r=26):
    """Iconos de linea, dibujados a mano: nada de librerias ni emojis."""
    if tipo == "pantalla":
        d.rounded_rectangle([cx - r, cy - r + 4, cx + r, cy + r - 10], radius=5,
                            outline=color, width=3)
        d.line([(cx - 12, cy + r - 2), (cx + 12, cy + r - 2)], fill=color, width=3)
    elif tipo == "ojo":
        d.ellipse([cx - r, cy - r * 0.62, cx + r, cy + r * 0.62], outline=color, width=3)
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=color, width=3)
    elif tipo == "escudo":
        d.polygon([(cx, cy - r), (cx + r * 0.82, cy - r * 0.5), (cx + r * 0.62, cy + r * 0.7),
                   (cx, cy + r), (cx - r * 0.62, cy + r * 0.7), (cx - r * 0.82, cy - r * 0.5)],
                  outline=color, width=3)
        d.line([(cx - 10, cy), (cx - 2, cy + 9), (cx + 12, cy - 9)], fill=color, width=4)
    elif tipo == "billete":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
        f = mono(30, bold=True)
        d.text((cx - d.textlength("$", font=f) / 2, cy - 17), "$", font=f, fill=color)


def _resplandor(img, cx, cy, r, color, alpha=70):
    """Halo radial. Es lo que le da profundidad a los anuncios que funcionan:
    sin caida de luz, un fondo plano se ve barato."""
    from PIL import ImageFilter
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ID.Draw(capa).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(r * 0.55)))


def _navegador(img, xy, w, h, foto, url, radio=16, recorte_der=0.0):
    """Marco de navegador alrededor de una captura real. La barra superior es
    lo que hace que el cerebro lea «esto es una web», no «esto es una foto»."""
    x, y = xy
    barra = 46
    marco = Image.new("RGBA", (w, h), (250, 246, 240, 255))
    d = ID.Draw(marco)
    d.rectangle([0, 0, w, barra], fill=(228, 221, 210))
    for k, c in enumerate(((236, 118, 100), (240, 190, 96), (140, 200, 128))):
        d.ellipse([20 + k * 26, barra / 2 - 7, 34 + k * 26, barra / 2 + 7], fill=c)
    d.rounded_rectangle([120, 11, w - 24, barra - 11], radius=9, fill=(243, 239, 233))
    d.text((136, 15), url, font=manrope(20, 500), fill=(120, 110, 98))

    cap = Image.open(os.path.join(FOTOS, foto)).convert("RGB")
    if recorte_der:                        # la captura de origen trae el boton
        cap = cap.crop((0, 0, int(cap.width * (1 - recorte_der)), cap.height))
    ih = h - barra
    r = w / cap.width                       # ajustar a lo ancho: nada de recorte lateral
    cap = cap.resize((w, max(ih, int(cap.height * r + 1))), Image.LANCZOS)
    marco.paste(cap.crop((0, 0, w, ih)), (0, barra))

    mask = Image.new("L", (w, h), 0)
    ID.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radio, fill=255)
    marco.putalpha(mask)
    img.alpha_composite(marco, (x, y))


def estilo_f_oferta(titular, sub, pasos, garantias, cta="DM THE WORD DEMO",
                    captura=("tripcazador.webp", "tripcazador.com"), pie_captura=None,
                    recorte=0.088, pagina=None):
    """
    F · Oferta — captura real arriba, titular, mecanismo en tres pasos y barra
    de reversion de riesgo. Es la estructura que de verdad vende: se entiende
    entera en miniatura y demuestra antes de prometer.

    `pasos`     = [(n, texto), ...]  tres
    `garantias` = [(icono, arriba, abajo), ...]  cuatro
    """
    img = Image.new("RGBA", FEED, (22, 19, 15, 255))
    _resplandor(img, 780, 240, 520, CLAY, 46)          # calor arriba a la derecha
    _resplandor(img, 200, 900, 460, (90, 70, 120), 26)  # frio abajo: da volumen
    red_nodos(img, CREAM, n=24, alpha=22, semilla=5)
    d = ID.Draw(img)
    M, W, H = 76, FEED[0], FEED[1]
    BARRA = 1150

    # --- prueba: algo construido de verdad -------------------------------
    if captura:
        _navegador(img, (M, 84), W - M * 2, 452, captura[0], captura[1],
                   recorte_der=recorte)
        d = ID.Draw(img)
        txt = pie_captura or f"{captura[1]} · built by Plexglobe"
        tracked(d, (M, 552), txt.upper(), mono(21), (150, 138, 124), 4)
    badge_pg(d, (W - M - 52, 544), size=52, bg=CREAM, fg=INK)

    # --- titular ---------------------------------------------------------
    y0 = 606
    lines = rich_lines(d, titular, W - M * 2, 80)
    y = draw_rich(d, lines, M, y0, 80, CREAM, leading=1.08, italic_color=CLAY)
    if sub:
        d.text((M, y + 8), sub, font=manrope(33, 500), fill=(190, 178, 164))
        y += 8 + 42

    # --- el mecanismo ----------------------------------------------------
    y += 22
    for n, txt in pasos[:3]:
        d.ellipse([M, y + 2, M + 46, y + 48], outline=CLAY, width=3)
        fn = grotesk(28, 700)                       # antes eran mono diminutos
        d.text((M + 23 - d.textlength(str(n), font=fn) / 2, y + 11), str(n),
               font=fn, fill=CLAY)
        d.text((M + 68, y + 2), txt, font=grotesk(42, 700), fill=CREAM)
        y += 70

    pill(d, (M, y + 14), cta, mono(28, bold=True), CLAY, CREAM, padx=28, pady=15)

    # --- barra de reversion de riesgo ------------------------------------
    d.rectangle([0, BARRA, W, H], fill=(31, 27, 22))
    d.line([(0, BARRA), (W, BARRA)], fill=(74, 63, 52), width=2)
    anchura = W // 4
    for i, (ico, arr, abj) in enumerate(garantias[:4]):
        cx = anchura * i + anchura // 2
        if i:
            d.line([(anchura * i, BARRA + 34), (anchura * i, H - 36)],
                   fill=(60, 52, 43), width=2)
        _icono(d, cx, BARRA + 66, ico, CLAY, r=23)
        for j, (t, f, c) in enumerate(((arr, mono(20, bold=True), CREAM),
                                       (abj, manrope(20, 500), (156, 144, 130)))):
            d.text((cx - d.textlength(t, font=f) / 2, BARRA + 108 + j * 28), t, font=f, fill=c)

    if pagina:
        _pie_carrusel(d, FEED, pagina)
    return img
