#!/usr/bin/env python3
"""
Plexglobe · motor de render de contenido social
Reproduce el sistema de diseno del PDF "Redes sociales Plexglobe Template".

Tokens de marca (del PDF):
  Cream #F4EDE2 · Ink #1C1813 · Clay #C0562C
  Space Grotesk (titulares) · Instrument Serif Italic (palabra clave)
  Manrope (texto) · Space Mono (etiquetas)

Uso:
  python3 plexglobe_render.py            -> genera las muestras en ./samples
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- tokens
CREAM = (244, 237, 226)
INK = (28, 24, 19)
CLAY = (192, 86, 44)
CREAM_DIM = (214, 203, 186)

FEED = (1080, 1350)      # 4:5
STORY = (1080, 1920)     # 9:16
SAFE_TOP = 250           # zona segura 9:16: la app tapa arriba
SAFE_BOTTOM = 340        # ...y abajo

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")

# Las fuentes no se guardan en el repositorio: se descargan de Google Fonts
# la primera vez. Asi el repo es solo texto y no hay binarios que mantener.
GOOGLE_FONTS = {
    "SpaceGrotesk.ttf": "ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "Manrope.ttf": "ofl/manrope/Manrope%5Bwght%5D.ttf",
    "InstrumentSerif-Italic.ttf": "ofl/instrumentserif/InstrumentSerif-Italic.ttf",
    "SpaceMono-Regular.ttf": "ofl/spacemono/SpaceMono-Regular.ttf",
    "SpaceMono-Bold.ttf": "ofl/spacemono/SpaceMono-Bold.ttf",
}


def asegurar_fuentes():
    """Descarga las tipografias de marca si no estan presentes."""
    import urllib.request
    os.makedirs(FONTS, exist_ok=True)
    base = "https://github.com/google/fonts/raw/main/"
    for nombre, ruta in GOOGLE_FONTS.items():
        destino = os.path.join(FONTS, nombre)
        if os.path.exists(destino) and os.path.getsize(destino) > 1000:
            continue
        print(f"  descargando {nombre} …")
        urllib.request.urlretrieve(base + ruta, destino)


asegurar_fuentes()


def grotesk(size, weight=700):
    f = ImageFont.truetype(os.path.join(FONTS, "SpaceGrotesk.ttf"), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def manrope(size, weight=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Manrope.ttf"), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def serif_it(size):
    return ImageFont.truetype(os.path.join(FONTS, "InstrumentSerif-Italic.ttf"), size)


def mono(size, bold=False):
    name = "SpaceMono-Bold.ttf" if bold else "SpaceMono-Regular.ttf"
    return ImageFont.truetype(os.path.join(FONTS, name), size)


# ---------------------------------------------------------------- motivo: nodos -> red
def node_grid(img, color, step=54, radius=2, alpha=48, connect=True):
    """Trama de puntos conectados: el sello visual de Plexglobe."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = img.size
    pts = [(x, y) for y in range(step, h, step) for x in range(step, w, step)]
    if connect:
        for (x, y) in pts:
            if (x // step + y // step) % 7 == 0 and x + step < w:
                d.line([(x, y), (x + step, y)], fill=color + (int(alpha * 0.5),), width=1)
    for (x, y) in pts:
        d.ellipse([x - radius, y - radius, x + radius, y + radius],
                  fill=color + (alpha,))
    img.alpha_composite(layer)


def diagonal_hatch(img, box, color, gap=14, alpha=60):
    """Trama diagonal: placeholder de foto (plantillas B y C)."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    for i in range(0, int((x1 - x0) + (y1 - y0)), gap):
        d.line([(x0 + i, y0), (x0, y0 + i)], fill=color + (alpha,), width=3)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=0, fill=255)
    img.alpha_composite(Image.composite(layer, Image.new("RGBA", img.size, (0, 0, 0, 0)), mask))


# ---------------------------------------------------------------- texto enriquecido
def rich_lines(draw, text, max_w, size, weight=700, italic_size_bump=1.06):
    """
    Parte el texto en lineas respetando max_w.
    Las palabras entre *asteriscos* se renderizan en Instrument Serif Italic.
    Devuelve [[(palabra, font, es_italica), ...], ...]
    """
    f_reg = grotesk(size, weight)
    f_it = serif_it(int(size * italic_size_bump))
    space = draw.textlength(" ", font=f_reg)

    tokens = []
    for raw in text.split():
        it = raw.startswith("*") or raw.endswith("*")
        clean = raw.strip("*")
        tokens.append((clean, f_it if it else f_reg, it))

    lines, cur, cur_w = [], [], 0
    for word, font, it in tokens:
        wlen = draw.textlength(word, font=font)
        add = wlen if not cur else space + wlen
        if cur and cur_w + add > max_w:
            lines.append(cur)
            cur, cur_w = [(word, font, it)], wlen
        else:
            cur.append((word, font, it))
            cur_w += add
    if cur:
        lines.append(cur)
    return lines


def draw_rich(draw, lines, x, y, size, color, leading=1.12, italic_color=None):
    """Dibuja el resultado de rich_lines. Devuelve la y final."""
    lh = int(size * leading)
    space = draw.textlength(" ", font=grotesk(size))
    for line in lines:
        cx = x
        for word, font, it in line:
            # la cursiva serif se asienta un poco mas abajo que el grotesk
            dy = int(size * 0.045) if it else 0
            draw.text((cx, y + dy), word, font=font,
                      fill=(italic_color if (it and italic_color) else color))
            cx += draw.textlength(word, font=font) + space
        y += lh
    return y


def tracked(draw, xy, text, font, fill, tracking=6):
    """Space Mono con letter-spacing, como las etiquetas del PDF."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def pill(draw, xy, text, font, bg, fg, padx=26, pady=14, tracking=4):
    x, y = xy
    tw = sum(draw.textlength(c, font=font) + tracking for c in text) - tracking
    th = font.size
    box = [x, y, x + tw + padx * 2, y + th + pady * 2]
    draw.rounded_rectangle(box, radius=(th + pady * 2) // 2, fill=bg)
    tracked(draw, (x + padx, y + pady - 2), text, font, fg, tracking)
    return box


def badge_pg(draw, xy, size=64, bg=INK, fg=CREAM):
    x, y = xy
    draw.rounded_rectangle([x, y, x + size, y + size], radius=14, fill=bg)
    f = mono(int(size * 0.34), bold=True)
    t = "PG"
    tw = draw.textlength(t, font=f)
    draw.text((x + (size - tw) / 2, y + size * 0.30), t, font=f, fill=fg)


def canvas(sz, bg):
    return Image.new("RGBA", sz, bg + (255,))


# ---------------------------------------------------------------- plantillas
def tpl_a_propuesta(headline, sub, eyebrow="DIGITAL STUDIO · MIAMI → GLOBAL"):
    """A · Propuesta de valor — fondo cream, trama de nodos."""
    img = canvas(FEED, CREAM)
    node_grid(img, INK, step=52, radius=2, alpha=38)
    d = ImageDraw.Draw(img)
    M = 84

    d.ellipse([M, 128, M + 14, 142], fill=CLAY)
    tracked(d, (M + 30, 122), eyebrow, mono(23), INK, 5)

    size = 118
    lines = rich_lines(d, headline, FEED[0] - M * 2, size)
    y = draw_rich(d, lines, M, 268, size, INK, leading=1.13, italic_color=CLAY)

    fb = manrope(34, 450)
    for i, ln in enumerate(sub.split("\n")):
        d.text((M, y + 46 + i * 48), ln, font=fb, fill=(70, 62, 54))

    badge_pg(d, (M, FEED[1] - M - 64))
    d.text((M + 86, FEED[1] - M - 50), "Plexglobe", font=manrope(32, 600), fill=INK)
    return img


def tpl_d_carrusel(headline, kicker="GOT A WEBSITE? READ THIS", page=None):
    """D · Carrusel educativo (portada) — fondo ink."""
    img = canvas(FEED, INK)
    node_grid(img, CREAM, step=52, radius=2, alpha=30)
    d = ImageDraw.Draw(img)
    M = 84

    tracked(d, (M, 122), kicker, mono(23), CLAY, 6)

    size = 112
    lines = rich_lines(d, headline, FEED[0] - M * 2, size)
    draw_rich(d, lines, M, 300, size, CREAM, leading=1.15, italic_color=CLAY)

    d.text((M, FEED[1] - M - 52), "→", font=grotesk(58, 600), fill=CLAY)
    if page:
        t = page
        f = mono(24)
        tw = sum(d.textlength(c, font=f) + 5 for c in t)
        tracked(d, (FEED[0] - M - tw, FEED[1] - M - 30), t, f, CREAM_DIM, 5)
    return img


def tpl_f_auditoria(headline, kicker="NO COST · NO STRINGS",
                    cta="DM: «AUDIT»", foot="plexglobe.com"):
    """F · Auditoria gratis (lead) — fondo clay."""
    img = canvas(FEED, CLAY)
    node_grid(img, CREAM, step=52, radius=2, alpha=34)
    d = ImageDraw.Draw(img)
    M = 84

    tracked(d, (M, 122), kicker, mono(23), (247, 226, 214), 6)

    size = 118
    lines = rich_lines(d, headline, FEED[0] - M * 2, size)
    draw_rich(d, lines, M, 286, size, CREAM, leading=1.13, italic_color=(255, 233, 220))

    pill(d, (M, FEED[1] - M - 200), cta, mono(26, bold=True), INK, CREAM)
    d.text((M, FEED[1] - M - 56), foot, font=manrope(30, 600), fill=(250, 232, 222))
    return img


def tpl_carrusel_punto(numero, titulo, cuerpo, pagina=None):
    """2/5 · 3/5 · 4/5 — fondo cream, numeral grande en clay (ver PDF p.7).

    El bloque se mide y se centra: colgarlo del borde superior dejaba media
    diapositiva vacia, que en la cuadricula del perfil se ve como un hueco."""
    img = canvas(FEED, CREAM)
    node_grid(img, INK, step=52, radius=2, alpha=26)
    d = ImageDraw.Draw(img)
    M, ancho = 84, FEED[0] - 84 * 2

    # --- medir antes de pintar ------------------------------------------
    fnum = grotesk(168, 700)
    num = str(numero).zfill(2)
    h_num = d.textbbox((0, 0), num, font=fnum)[3]

    lineas_tit = rich_lines(d, titulo, ancho, 76, weight=700)
    h_tit = len(lineas_tit) * 76 * 1.16

    fb = manrope(36, 450)
    lineas_cuerpo, linea = [], ""
    for w in cuerpo.split():
        prueba = (linea + " " + w).strip()
        if d.textlength(prueba, font=fb) > ancho and linea:
            lineas_cuerpo.append(linea)
            linea = w
        else:
            linea = prueba
    if linea:
        lineas_cuerpo.append(linea)
    h_cuerpo = len(lineas_cuerpo) * 52

    HUECO_NUM, HUECO_CUERPO = 52, 44
    alto = h_num + HUECO_NUM + h_tit + HUECO_CUERPO + h_cuerpo
    y = int((FEED[1] - alto) / 2) - 50          # centro optico, no geometrico

    # --- pintar ----------------------------------------------------------
    d.text((M - 6, y), num, font=fnum, fill=CLAY)
    y += h_num + HUECO_NUM
    y = draw_rich(d, lineas_tit, M, y, 76, INK, leading=1.16, italic_color=CLAY)
    y += HUECO_CUERPO
    for ln in lineas_cuerpo:
        d.text((M, y), ln, font=fb, fill=(90, 80, 70))
        y += 52

    d.text((M, FEED[1] - M - 52), "→", font=grotesk(58, 600), fill=CLAY)
    if pagina:
        f = mono(24)
        tw = sum(d.textlength(c, font=f) + 5 for c in pagina)
        tracked(d, (FEED[0] - M - tw, FEED[1] - M - 30), pagina, f, (150, 136, 120), 5)
    return img


def tpl_carrusel_cierre(headline, cta="DM: «AUDIT»", foot="plexglobe.com", pagina="5 / 5 · LAST"):
    """5/5 — fondo clay, cierre con llamada a la accion."""
    img = canvas(FEED, CLAY)
    node_grid(img, CREAM, step=52, radius=2, alpha=34)
    d = ImageDraw.Draw(img)
    M = 84

    tracked(d, (M, 122), pagina, mono(23), (247, 226, 214), 6)

    lines = rich_lines(d, headline, FEED[0] - M * 2, 96)
    draw_rich(d, lines, M, 300, 96, CREAM, leading=1.14, italic_color=(255, 233, 220))

    pill(d, (M, FEED[1] - M - 200), cta, mono(26, bold=True), INK, CREAM)
    d.text((M, FEED[1] - M - 56), foot, font=manrope(30, 600), fill=(250, 232, 222))
    return img


def tpl_e_testimonial(quote, autor=None, sub=None):
    """E · Testimonial — fondo cream, comillas clay."""
    img = canvas(FEED, CREAM)
    node_grid(img, INK, step=52, radius=2, alpha=30)
    d = ImageDraw.Draw(img)
    M = 84

    d.text((M - 6, 118), "”", font=serif_it(150), fill=CLAY)

    size = 74
    lines = rich_lines(d, quote, FEED[0] - M * 2, size, weight=600)
    y = draw_rich(d, lines, M, 330, size, INK, leading=1.22, italic_color=CLAY)

    if autor:
        d.text((M, y + 60), autor, font=manrope(32, 700), fill=INK)
    if sub:
        d.text((M, y + 104), sub, font=manrope(28, 450), fill=(110, 98, 86))

    badge_pg(d, (M, FEED[1] - M - 64))
    d.text((M + 86, FEED[1] - M - 50), "Plexglobe", font=manrope(32, 600), fill=INK)
    return img


def tpl_b_caso(title, sub, metric, tag="CASE"):
    """B · Caso / Resultado — foto arriba (trama), datos abajo."""
    img = canvas(FEED, CREAM)
    d = ImageDraw.Draw(img)
    M = 84
    photo = [0, 0, FEED[0], 620]
    d.rectangle(photo, fill=(226, 214, 196))
    diagonal_hatch(img, photo, (150, 132, 108), gap=16, alpha=70)
    d = ImageDraw.Draw(img)

    pill(d, (M, 74), tag, mono(24, bold=True), CLAY, CREAM, padx=22, pady=12)
    tracked(d, (M, 552), "FOTO · CAPTURA DEL SITIO", mono(20), (255, 255, 255), 4)

    d.text((M, 700), title, font=grotesk(72, 700), fill=INK)
    fb = manrope(32, 450)
    for i, ln in enumerate(sub.split("\n")):
        d.text((M, 806 + i * 46), ln, font=fb, fill=(90, 80, 70))

    d.text((M, FEED[1] - M - 130), metric, font=grotesk(76, 700), fill=CLAY)
    cx, cy, r = FEED[0] - M - 46, FEED[1] - M - 92, 46
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK)
    d.text((cx - 21, cy - 27), "→", font=grotesk(42, 600), fill=CREAM)
    return img


def tpl_story(headline, kicker="BEHIND THE SCENES", foot="Swipe up → free audit",
              bg=CLAY, fg=CREAM):
    """9:16 · portada de reel / story, respetando zona segura."""
    img = canvas(STORY, bg)
    node_grid(img, fg, step=58, radius=2, alpha=32)
    d = ImageDraw.Draw(img)
    M = 90

    tracked(d, (M, SAFE_TOP), kicker, mono(24), (247, 226, 214) if bg == CLAY else CLAY, 6)

    size = 124
    lines = rich_lines(d, headline, STORY[0] - M * 2, size)
    draw_rich(d, lines, M, STORY[1] // 2 - 260, size, fg, leading=1.13,
              italic_color=(255, 233, 220) if bg == CLAY else CLAY)

    # el pie tiene que TERMINAR antes de la zona que tapa la app, no empezar ahi
    d.text((M, STORY[1] - SAFE_BOTTOM - 58), foot, font=manrope(30, 500),
           fill=(250, 232, 222) if bg == CLAY else (90, 80, 70))
    return img


# ---------------------------------------------------------------- salida
def save(img, name, outdir):
    p = os.path.join(outdir, name)
    img.convert("RGB").save(p, "JPEG", quality=92, subsampling=0)
    return p


def main():
    out = os.path.join(HERE, "samples")
    os.makedirs(out, exist_ok=True)
    made = []

    made.append(save(tpl_a_propuesta(
        "Webs y contenido que *conectan.*",
        "Diseño, desarrollo y SEO hacia un\nobjetivo."), "A_propuesta_valor.jpg", out))

    made.append(save(tpl_b_caso(
        "Villa Oliva Nova",
        "Reservas directas · sincronizado\nBooking/Airbnb",
        "100% directas"), "B_caso_resultado.jpg", out))

    made.append(save(tpl_d_carrusel(
        "3 señales de que tu web te hace perder clientes",
        page="1 / 5 · START"), "D_carrusel_portada.jpg", out))

    made.append(save(tpl_f_auditoria(
        "A *free* check of your site"), "F_auditoria_lead.jpg", out))

    made.append(save(tpl_story(
        "Del nodo a la *red*"), "S_story_reel.jpg", out))

    for p in made:
        print(p)


if __name__ == "__main__":
    main()
