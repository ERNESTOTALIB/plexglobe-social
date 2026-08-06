#!/usr/bin/env python3
"""
Plexglobe · motor de vídeo (reels 9:16).

Genera frames con Pillow y los mete por stdin a ffmpeg. No escribe PNGs
intermedios: 500 frames a 1080x1920 en disco son 1,5 GB y el repo es publico.

Salida: MP4 H.264 + pista AAC silenciosa, moov al principio (faststart),
que es exactamente lo que pide la API de Instagram para reels
(modulo instagram-business:CreateAReelPost en Make).

Uso:
    python3 video.py                  # todos los reels del banco
    python3 video.py --solo intro     # solo uno
"""
import argparse
import math
import os
import subprocess
import sys

from PIL import Image
from PIL import ImageDraw as ID

import plexglobe_render as R
from plexglobe_render import (CREAM, INK, CLAY, CREAM_DIM, STORY,
                              grotesk, manrope, serif_it, mono,
                              rich_lines, draw_rich, tracked, badge_pg)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "salida")

FPS = 30
W, H = STORY


# ---------------------------------------------------------------- easing
def clamp(t):
    return 0.0 if t < 0 else (1.0 if t > 1 else t)


def out_cubic(t):
    return 1 - (1 - clamp(t)) ** 3


def out_quint(t):
    return 1 - (1 - clamp(t)) ** 5


def out_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def in_out(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def tramo(f, inicio, dur):
    """Progreso 0..1 de un tramo que empieza en el segundo `inicio`."""
    return clamp((f / FPS - inicio) / dur)


# ---------------------------------------------------------------- pintura
def lienzo(bg=INK):
    return Image.new("RGB", (W, H), bg)


def fundido(img, capa, alpha):
    """Compone una capa RGBA sobre el frame con opacidad global 0..1."""
    if alpha <= 0:
        return
    if alpha < 1:
        a = capa.getchannel("A").point(lambda v: int(v * alpha))
        capa = capa.copy()
        capa.putalpha(a)
    img.paste(Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB"), (0, 0))


def capa():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def texto_sube(img, xy, texto, font, color, p, salto=48):
    """Aparece subiendo: el gesto de marca para todo el texto del reel."""
    if p <= 0:
        return
    c = capa()
    ID.Draw(c).text((xy[0], xy[1] + salto * (1 - out_quint(p))), texto,
                    font=font, fill=color + (255,))
    fundido(img, c, out_cubic(p * 1.4))


def red_animada(img, p, color=CREAM, n=30, semilla=11):
    """El motivo de marca construyendose: primero las aristas, luego los nodos."""
    import random
    random.seed(semilla)
    pts = [(random.randint(80, W - 80), random.randint(200, H - 200)) for _ in range(n)]
    c = capa()
    d = ID.Draw(c)
    for i, a in enumerate(pts):
        pa = clamp((p - i / n * 0.55) * 2.6)
        if pa <= 0:
            continue
        for b in sorted(pts, key=lambda q: (q[0] - a[0]) ** 2 + (q[1] - a[1]) ** 2)[1:3]:
            k = out_cubic(pa)
            d.line([a, (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)],
                   fill=color + (46,), width=2)
        r = 5 * out_back(pa)
        if r > 0:
            d.ellipse([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=color + (105,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), c).convert("RGB"), (0, 0))


def barra(d, x, y, w, h, color, radio=8):
    if h < 1:
        return
    d.rounded_rectangle([x, y - h, x + w, y], radius=min(radio, h // 2), fill=color)


_CACHE = {}


def tarjeta_foto(nombre, w, h, radio=20, foco=0.0):
    """Foto recortada a medida y con esquinas redondeadas. Se cachea: el reel
    la pide 100 veces y decodificar un webp por frame es carisimo."""
    clave = (nombre, w, h, radio, foco)
    if clave in _CACHE:
        return _CACHE[clave]
    im = Image.open(os.path.join(HERE, "fotos", nombre)).convert("RGB")
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x = (im.width - w) // 2
    y = int((im.height - h) * foco)
    im = im.crop((x, y, x + w, y + h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ID.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radio, fill=255)
    im.putalpha(mask)
    _CACHE[clave] = im
    return im


# ---------------------------------------------------------------- el reel
M = 96                    # margen lateral
Y_TECHO = 360             # por debajo del icono de la cuenta que pinta Instagram
Y_SUELO = H - 400         # por encima del pie/caption/botones del reel


def bloque_titular(img, texto, t0, size=118, italic=CLAY, sub=None, t_sub=None):
    """Titular grande centrado verticalmente, linea a linea, subiendo."""
    lines = rich_lines(ID.Draw(img), texto, W - M * 2, size)
    c = capa()
    y = H // 2 - len(lines) * size * 0.62
    for i, ln in enumerate(lines):
        pi = tramo_f(t0 + i * 0.14, 0.85)
        if pi <= 0:
            continue
        cl = capa()
        draw_rich(ID.Draw(cl), [ln], M,
                  int(y + i * size * 1.12 + 56 * (1 - out_quint(pi))),
                  size, CREAM + (255,), italic_color=italic + (255,))
        cl.putalpha(cl.getchannel("A").point(lambda v: int(v * out_cubic(pi * 1.3))))
        c = Image.alpha_composite(c, cl)
    if sub:
        ps = tramo_f(t_sub, 0.9)
        if ps > 0:
            cs = capa()
            ID.Draw(cs).text((M, y + len(lines) * size * 1.12 + 54), sub,
                             font=manrope(42, 500), fill=CREAM_DIM + (255,))
            cs.putalpha(cs.getchannel("A").point(lambda v: int(v * out_cubic(ps))))
            c = Image.alpha_composite(c, cs)
    return c


# `tramo` necesita el frame; se inyecta por escena para no arrastrarlo a mano
_F = [0]


def tramo_f(inicio, dur):
    return tramo(_F[0], inicio, dur)


def frame_intro(f, dur_total):
    """
    Reel de presentacion. El gancho va PRIMERO y el logotipo al final: abrir
    con la marca es lo que hunde la retencion en los tres primeros segundos.

      0.0- 3.0  gancho    "No hacemos webs bonitas."
      3.0- 6.2  promesa   "Hacemos webs que funcionan."
      6.2- 9.8  prueba    Villa Oliva Nova, 20% -> 0% de comision
      9.8-13.2  servicio  diseno / desarrollo / SEO
     13.2-16.8  dato      las 6 auditorias reales de Miami
     16.8-19.8  cierre    CTA + PLEXGLOBE
    """
    _F[0] = f
    img = lienzo(INK)

    # --- 1 · gancho ------------------------------------------------------
    if tramo_f(2.6, 0.4) < 1:
        c = bloque_titular(img, "No hacemos webs *bonitas.*", 0.15,
                           italic=(150, 138, 124))
        fundido(img, c, 1 - tramo_f(2.6, 0.4))
        return img

    # --- 2 · promesa -----------------------------------------------------
    if tramo_f(5.8, 0.4) < 1:
        c = bloque_titular(img, "Hacemos webs que *funcionan.*", 3.1,
                           sub="Reservas. Llamadas. Ventas.", t_sub=4.4)
        fundido(img, c, 1 - tramo_f(5.8, 0.4))
        return img

    # --- 3 · prueba: un caso real ---------------------------------------
    if tramo_f(9.4, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "CASO REAL · VILLA OLIVA NOVA",
                mono(30), CLAY + (255,), 6)

        pf = tramo_f(6.35, 0.9)
        if pf > 0:
            fw, fh = W - M * 2, 560
            foto = tarjeta_foto("oliva-dashboard.webp", fw, fh, radio=22)
            e = out_cubic(pf)
            k = 0.94 + 0.06 * e
            fw2, fh2 = int(fw * k), int(fh * k)
            tmp = capa()
            tmp.paste(foto.resize((fw2, fh2), Image.LANCZOS),
                      (M + (fw - fw2) // 2, 440 + (fh - fh2) // 2))
            tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * e)))
            c = Image.alpha_composite(c, tmp)
            d = ID.Draw(c)

        pn = tramo_f(7.3, 1.1)
        if pn > 0:
            a = int(255 * out_cubic(pn))
            n = 20 - int(20 * out_quint(pn))          # 20% -> 0%
            d.text((M, 1080), f"{n}%", font=grotesk(180, 700), fill=CLAY + (a,))
        pt = tramo_f(8.0, 0.9)
        if pt > 0:
            a = int(255 * out_cubic(pt))
            d.text((M, 1320), "de comisión por reserva.",
                   font=grotesk(52, 700), fill=CREAM + (a,))
            d.text((M, 1392), "Antes pagaba 15-20% a los portales.",
                   font=manrope(38, 500), fill=CREAM_DIM + (a,))
        fundido(img, c, 1 - tramo_f(9.4, 0.4))
        return img

    # --- 4 · qué hacemos -------------------------------------------------
    if tramo_f(12.8, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "QUÉ HACEMOS", mono(30), CLAY + (255,), 7)
        filas = [("01", "Diseño", "Que se entienda en 3 segundos"),
                 ("02", "Desarrollo", "Rápido, en móvil, indexable"),
                 ("03", "SEO", "Que te encuentren, hoy y en la IA")]
        for i, (num, tit, sub) in enumerate(filas):
            pi = tramo_f(10.0 + i * 0.40, 0.85)
            if pi <= 0:
                continue
            e, a = out_quint(pi), int(255 * out_cubic(pi * 1.4))
            y = 520 + i * 300
            x = M - 80 * (1 - e)
            d.line([(x, y - 8), (x, y + 196)], fill=CLAY + (int(a * 0.85),), width=5)
            d.text((x + 40, y), num, font=mono(30), fill=CLAY + (a,))
            d.text((x + 40, y + 48), tit, font=grotesk(80, 700), fill=CREAM + (a,))
            d.text((x + 40, y + 148), sub, font=manrope(36, 500), fill=CREAM_DIM + (a,))
        fundido(img, c, 1 - tramo_f(12.8, 0.4))
        return img

    # --- 5 · el dato: 6 auditorías reales --------------------------------
    if tramo_f(16.4, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "6 AUDITORÍAS REALES · MIAMI",
                mono(30), CLAY + (255,), 6)

        pc = tramo_f(13.45, 1.0)
        if pc > 0:
            a = int(255 * out_cubic(pc))
            n = int(68 * out_quint(pc))
            d.text((M - 8, 440), f"{n}", font=grotesk(200, 700), fill=CREAM + (a,))
            d.text((M + 268, 570), "/ 100", font=grotesk(58, 700), fill=CREAM_DIM + (a,))
        pt = tramo_f(13.9, 0.8)
        if pt > 0:
            a = int(255 * out_cubic(pt))
            d.text((M, 700), "Nota media. Ninguna llegó al notable.",
                   font=manrope(42, 500), fill=CREAM + (a,))
            d.text((M, 758), "Y ninguna era cara de arreglar.",
                   font=manrope(42, 500), fill=CREAM_DIM + (a,))

        notas = [52, 61, 66, 71, 74, 76]
        base, alto_max, bw, gap = Y_SUELO, 440, 118, 28
        pb = tramo_f(14.3, 1.3)
        for i, n in enumerate(notas):
            pi = out_cubic(clamp((pb - i * 0.07) * 1.6))
            x = M + i * (bw + gap)
            barra(d, x, base, bw, (n / 100) * alto_max * pi, CLAY + (235,))
            if pi > 0.6:
                d.text((x + 24, base + 20), str(n), font=mono(30),
                       fill=CREAM_DIM + (int(255 * clamp((pi - 0.6) * 3)),))
        pm = tramo_f(15.3, 0.8)
        if pm > 0:                                    # la linea de la media
            ym = base - (68 / 100) * alto_max
            d.line([(M, ym), (M + (W - M * 2) * out_cubic(pm), ym)],
                   fill=CREAM + (150,), width=3)
        fundido(img, c, 1 - tramo_f(16.4, 0.4))
        return img

    # --- 6 · cierre ------------------------------------------------------
    p6 = tramo_f(16.9, 1.0)
    red_animada(img, clamp(p6 * 1.6), n=22, semilla=4)
    c = capa()
    d = ID.Draw(c)
    lines = rich_lines(d, "Te decimos qué falla. *Gratis.*", W - M * 2, 104)
    yy = draw_rich(d, lines, M, 560 + int(46 * (1 - out_quint(p6))), 104,
                   CREAM + (255,), italic_color=CLAY + (255,))
    pcta = tramo_f(17.6, 0.8)
    if pcta > 0:
        w = int(560 * out_back(pcta))
        d.rounded_rectangle([M, yy + 70, M + w, yy + 180], radius=14, fill=CREAM + (255,))
        if pcta > 0.5:
            d.text((M + 42, yy + 98), "AUDITORÍA GRATIS", font=mono(34, bold=True),
                   fill=INK + (int(255 * clamp((pcta - 0.5) * 2)),))
    pfin = tramo_f(18.2, 0.9)
    if pfin > 0:
        a = int(255 * out_cubic(pfin))
        e = out_quint(pfin)
        yl = 1180 + int(30 * (1 - e))
        tracked(d, (M, yl), "PLEXGLOBE", grotesk(86, 700), CREAM + (a,), 10)
        d.line([(M, yl + 128), (M + int((W - M * 2) * e), yl + 128)],
               fill=CLAY + (a,), width=5)
        tracked(d, (M, yl + 170), "plexglobe.com", mono(34), CREAM_DIM + (a,), 5)
    fundido(img, c, out_cubic(p6 * 1.5))
    return img


def etiqueta_idioma(d, xy, texto, alpha=255):
    """Etiqueta EN / ES. Hace explicito que la pieza es bilingue."""
    f = mono(26, bold=True)
    w = int(d.textlength(texto, font=f)) + 30
    x, y = xy
    d.rounded_rectangle([x, y, x + w, y + 46], radius=8,
                        outline=CLAY + (alpha,), width=3)
    d.text((x + 15, y + 8), texto, font=f, fill=CLAY + (alpha,))
    return y + 46


def bloque_idioma(img, t0, etiqueta, texto, italic=CLAY, sub=None, t_sub=None,
                  size=112, y_base=None):
    """Un bloque de titular con su etiqueta de idioma delante."""
    c = capa()
    d = ID.Draw(c)
    lines = rich_lines(d, texto, W - M * 2, size)
    y = y_base if y_base is not None else int(H // 2 - len(lines) * size * 0.62) - 70

    pe = tramo_f(t0, 0.5)
    if pe > 0:
        etiqueta_idioma(d, (M, y), etiqueta, int(255 * out_cubic(pe)))

    for i, ln in enumerate(lines):
        pi = tramo_f(t0 + 0.22 + i * 0.13, 0.85)
        if pi <= 0:
            continue
        cl = capa()
        draw_rich(ID.Draw(cl), [ln], M,
                  int(y + 96 + i * size * 1.12 + 52 * (1 - out_quint(pi))),
                  size, CREAM + (255,), italic_color=italic + (255,))
        cl.putalpha(cl.getchannel("A").point(lambda v: int(v * out_cubic(pi * 1.3))))
        c = Image.alpha_composite(c, cl)

    if sub:
        ps = tramo_f(t_sub, 0.8)
        if ps > 0:
            cs = capa()
            ID.Draw(cs).text((M, y + 96 + len(lines) * size * 1.12 + 46), sub,
                             font=manrope(40, 500), fill=CREAM_DIM + (255,))
            cs.putalpha(cs.getchannel("A").point(lambda v: int(v * out_cubic(ps))))
            c = Image.alpha_composite(c, cs)
    return c


def frame_bilingue(f, dur_total):
    """
    Reel 2 · «One language» — bilingue de forma, no solo de pie de foto:
    cada idea aparece en ingles y acto seguido en espanol. La forma ES el
    mensaje, que es justo lo que vende Plexglobe en Miami.

    El dato del 67% es del censo (residentes de 5+ anios de Miami-Dade que
    hablan espanol en casa). Real, verificable, y local.

      0.0- 3.4  EN  "Your website speaks one language."
      3.4- 6.6  ES  "Tu web habla un idioma."
      6.6-10.4  dato 67%
     10.4-13.8  EN/ES  "Your customers speak two."
     13.8-17.2  "We build in both."
     17.2-20.2  cierre
    """
    _F[0] = f
    img = lienzo(INK)

    # --- 1 · el gancho, en ingles ---------------------------------------
    if tramo_f(3.0, 0.4) < 1:
        c = bloque_idioma(img, 0.15, "EN", "Your website speaks *one* language.")
        fundido(img, c, 1 - tramo_f(3.0, 0.4))
        return img

    # --- 2 · la misma frase, en espanol ---------------------------------
    if tramo_f(6.2, 0.4) < 1:
        c = bloque_idioma(img, 3.5, "ES", "Tu web habla *un* idioma.")
        fundido(img, c, 1 - tramo_f(6.2, 0.4))
        return img

    # --- 3 · el dato -----------------------------------------------------
    if tramo_f(10.0, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "MIAMI-DADE · U.S. CENSUS", mono(30), CLAY + (255,), 6)

        pc = tramo_f(6.75, 1.2)
        if pc > 0:
            a = int(255 * out_cubic(pc))
            n = int(67 * out_quint(pc))
            d.text((M - 10, 480), f"{n}%", font=grotesk(260, 700), fill=CREAM + (a,))
        pt = tramo_f(7.5, 0.9)
        if pt > 0:
            a = int(255 * out_cubic(pt))
            etiqueta_idioma(d, (M, 800), "EN", a)
            d.text((M, 872), "speak Spanish at home.", font=grotesk(58, 700),
                   fill=CREAM + (a,))
        pt2 = tramo_f(8.3, 0.9)
        if pt2 > 0:
            a = int(255 * out_cubic(pt2))
            etiqueta_idioma(d, (M, 1010), "ES", a)
            d.text((M, 1082), "hablan español en casa.", font=grotesk(58, 700),
                   fill=CREAM_DIM + (a,))
        fundido(img, c, 1 - tramo_f(10.0, 0.4))
        return img

    # --- 4 · el giro -----------------------------------------------------
    if tramo_f(13.4, 0.4) < 1:
        c = capa()
        for et, txt, y0, t0, col in (("EN", "Your customers speak *two.*", 470, 10.5, CLAY),
                                     ("ES", "Tus clientes hablan *dos.*", 1000, 11.5, CLAY)):
            c = Image.alpha_composite(
                c, bloque_idioma(img, t0, et, txt, italic=col, size=96, y_base=y0))
        fundido(img, c, 1 - tramo_f(13.4, 0.4))
        return img

    # --- 5 · lo que hacemos ---------------------------------------------
    if tramo_f(16.8, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "WHAT WE DO", mono(30), CLAY + (255,), 7)

        p = tramo_f(13.9, 1.0)
        if p > 0:
            lines = rich_lines(d, "We build in *both.*", W - M * 2, 118)
            draw_rich(d, lines, M, 520 + int(46 * (1 - out_quint(p))), 118,
                      CREAM + (255,), italic_color=CLAY + (255,))

        # interruptor EN|ES: los dos encendidos, que es el argumento
        pt = tramo_f(14.7, 0.9)
        if pt > 0:
            e = out_back(pt)
            wpill, hpill, y = 400, 118, 900
            d.rounded_rectangle([M, y, M + int(wpill * e), y + hpill],
                                radius=hpill // 2, fill=CREAM + (255,))
            if pt > 0.55:
                a = int(255 * clamp((pt - 0.55) * 2.4))
                fx = mono(46, bold=True)
                d.text((M + 46, y + 34), "EN", font=fx, fill=INK + (a,))
                d.text((M + 168, y + 34), "·", font=fx, fill=CLAY + (a,))
                d.text((M + 232, y + 34), "ES", font=fx, fill=INK + (a,))
        ps = tramo_f(15.4, 0.9)
        if ps > 0:
            a = int(255 * out_cubic(ps))
            d.text((M, 1090), "Same site. Both languages. One price.",
                   font=manrope(40, 500), fill=CREAM + (a,))
            d.text((M, 1148), "Una web. Los dos idiomas. Un precio.",
                   font=manrope(40, 500), fill=CREAM_DIM + (a,))
        fundido(img, c, 1 - tramo_f(16.8, 0.4))
        return img

    # --- 6 · cierre ------------------------------------------------------
    p6 = tramo_f(17.3, 1.0)
    red_animada(img, clamp(p6 * 1.6), n=22, semilla=4)
    c = capa()
    d = ID.Draw(c)
    lines = rich_lines(d, "Web design in Miami. *ES/EN.*", W - M * 2, 100)
    yy = draw_rich(d, lines, M, 560 + int(46 * (1 - out_quint(p6))), 100,
                   CREAM + (255,), italic_color=CLAY + (255,))
    pcta = tramo_f(18.0, 0.8)
    if pcta > 0:
        w = int(520 * out_back(pcta))
        d.rounded_rectangle([M, yy + 70, M + w, yy + 180], radius=14, fill=CREAM + (255,))
        if pcta > 0.5:
            d.text((M + 42, yy + 98), "FREE AUDIT", font=mono(34, bold=True),
                   fill=INK + (int(255 * clamp((pcta - 0.5) * 2)),))
    pfin = tramo_f(18.6, 0.9)
    if pfin > 0:
        a, e = int(255 * out_cubic(pfin)), out_quint(pfin)
        yl = 1180 + int(30 * (1 - e))
        tracked(d, (M, yl), "PLEXGLOBE", grotesk(86, 700), CREAM + (a,), 10)
        d.line([(M, yl + 128), (M + int((W - M * 2) * e), yl + 128)],
               fill=CLAY + (a,), width=5)
        tracked(d, (M, yl + 170), "plexglobe.com", mono(34), CREAM_DIM + (a,), 5)
    fundido(img, c, out_cubic(p6 * 1.5))
    return img


def frame_movil(f, dur_total):
    """
    Reel 3 · «Ábrela en el móvil» — EN ESPANOL, a proposito.

    No es una pieza mas del banco: es una REPLICA de las condiciones del reel 1
    (espanol, 9 hashtags, sin ubicacion), que saco 109 visualizaciones. Sirve
    para saber si aquello se repite o fue el empujon de la primera publicacion
    en una cuenta nueva.

    Arranca con una orden, no con una afirmacion: que el que mira haga algo
    es lo que retiene.

      0.0- 3.4  «Abre tu web en el móvil. Ahora.»
      3.4- 6.8  7 de cada 10
      6.8-11.0  las tres preguntas
     11.0-14.2  el remate
     14.2-17.2  cierre
    """
    _F[0] = f
    img = lienzo(INK)

    if tramo_f(3.0, 0.4) < 1:
        c = bloque_titular(img, "Abre tu web en el móvil. *Ahora.*", 0.15)
        fundido(img, c, 1 - tramo_f(3.0, 0.4))
        return img

    if tramo_f(6.4, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "DÓNDE ESTÁ TU CLIENTE", mono(30), CLAY + (255,), 6)
        pc = tramo_f(3.6, 1.1)
        if pc > 0:
            a = int(255 * out_cubic(pc))
            n = int(7 * out_quint(pc))
            d.text((M - 8, 520), f"{n}", font=grotesk(300, 700), fill=CREAM + (a,))
            d.text((M + 220, 700), "de cada 10", font=grotesk(72, 700), fill=CREAM + (a,))
        pt = tramo_f(4.6, 0.9)
        if pt > 0:
            a = int(255 * out_cubic(pt))
            d.text((M, 900), "visitas llegan desde el teléfono.",
                   font=manrope(44, 500), fill=CREAM_DIM + (a,))
        fundido(img, c, 1 - tramo_f(6.4, 0.4))
        return img

    if tramo_f(10.6, 0.4) < 1:
        c = capa()
        d = ID.Draw(c)
        tracked(d, (M, Y_TECHO), "TRES PREGUNTAS", mono(30), CLAY + (255,), 7)
        preg = ["¿El menú se toca bien\ncon el pulgar?",
                "¿El botón de llamar\nse ve sin buscarlo?",
                "¿El formulario pide\nmenos de cuatro datos?"]
        for i, q in enumerate(preg):
            pi = tramo_f(7.0 + i * 0.55, 0.85)
            if pi <= 0:
                continue
            e, a = out_quint(pi), int(255 * out_cubic(pi * 1.4))
            y = 520 + i * 290
            x = M - 70 * (1 - e)
            d.line([(x, y - 6), (x, y + 150)], fill=CLAY + (int(a * 0.85),), width=5)
            for k, ln in enumerate(q.split("\n")):
                d.text((x + 38, y + k * 68), ln, font=grotesk(58, 700), fill=CREAM + (a,))
        fundido(img, c, 1 - tramo_f(10.6, 0.4))
        return img

    if tramo_f(13.8, 0.4) < 1:
        c = bloque_titular(img, "Si has dudado en alguna, pierdes *clientes.*", 11.1,
                           sub="Y no lo ves en ninguna métrica.", t_sub=12.4, size=98)
        fundido(img, c, 1 - tramo_f(13.8, 0.4))
        return img

    p = tramo_f(14.3, 1.0)
    red_animada(img, clamp(p * 1.6), n=22, semilla=4)
    c = capa()
    d = ID.Draw(c)
    lines = rich_lines(d, "Te lo revisamos *gratis.*", W - M * 2, 104)
    yy = draw_rich(d, lines, M, 560 + int(46 * (1 - out_quint(p))), 104,
                   CREAM + (255,), italic_color=CLAY + (255,))
    pc = tramo_f(15.1, 0.8)
    if pc > 0:
        w = int(560 * out_back(pc))
        d.rounded_rectangle([M, yy + 70, M + w, yy + 180], radius=14, fill=CREAM + (255,))
        if pc > 0.5:
            d.text((M + 42, yy + 98), "AUDITORÍA GRATIS", font=mono(34, bold=True),
                   fill=INK + (int(255 * clamp((pc - 0.5) * 2)),))
    pf = tramo_f(15.7, 0.9)
    if pf > 0:
        a, e = int(255 * out_cubic(pf)), out_quint(pf)
        yl = 1180 + int(30 * (1 - e))
        tracked(d, (M, yl), "PLEXGLOBE", grotesk(86, 700), CREAM + (a,), 10)
        d.line([(M, yl + 128), (M + int((W - M * 2) * e), yl + 128)],
               fill=CLAY + (a,), width=5)
        tracked(d, (M, yl + 170), "plexglobe.com", mono(34), CREAM_DIM + (a,), 5)
    fundido(img, c, out_cubic(p * 1.5))
    return img


def hacer_frame_generico(post):
    """
    Convierte cualquier entrada del banco en un reel de 14 s sin escribir codigo
    nuevo por pieza. Tres tiempos:

        0.0- 5.0  kicker + titular
        5.0- 9.6  la carga util: `datos` (3 cifras), `dato` (una grande) o `sub`
        9.6-14.0  llamada a la accion + marca

    Existe porque los 8 huecos de «Post» estatico del banco eran el formato mas
    flojo: ni alcanzan como un reel ni enganchan como un carrusel.
    """
    kicker = post.get("kicker") or "PLEXGLOBE · MIAMI"
    titular = post["titular"]
    datos = post.get("datos")
    dato = post.get("dato")
    sub = post.get("sub") or post.get("pie")
    cta = post.get("cta") or "FREE AUDIT"

    def frame(f, dur_total):
        _F[0] = f
        img = lienzo(INK)

        # --- 1 · kicker + titular ---------------------------------------
        if tramo_f(4.6, 0.4) < 1:
            c = capa()
            d = ID.Draw(c)
            pk = tramo_f(0.1, 0.7)
            if pk > 0:
                tracked(d, (M, Y_TECHO), kicker[:34], mono(30),
                        CLAY + (int(255 * out_cubic(pk)),), 6)
            lines = rich_lines(d, titular, W - M * 2, 106)
            y = 560
            for i, ln in enumerate(lines):
                pi = tramo_f(0.5 + i * 0.15, 0.85)
                if pi <= 0:
                    continue
                cl = capa()
                draw_rich(ID.Draw(cl), [ln], M,
                          int(y + i * 106 * 1.12 + 54 * (1 - out_quint(pi))),
                          106, CREAM + (255,), italic_color=CLAY + (255,))
                cl.putalpha(cl.getchannel("A").point(lambda v: int(v * out_cubic(pi * 1.3))))
                c = Image.alpha_composite(c, cl)
            fundido(img, c, 1 - tramo_f(4.6, 0.4))
            return img

        # --- 2 · la carga util ------------------------------------------
        if tramo_f(9.2, 0.4) < 1:
            c = capa()
            d = ID.Draw(c)
            if datos:
                tracked(d, (M, Y_TECHO), "THE NUMBERS", mono(30), CLAY + (255,), 7)
                for i, (num, txt) in enumerate(datos[:3]):
                    pi = tramo_f(5.2 + i * 0.42, 0.9)
                    if pi <= 0:
                        continue
                    e, a = out_quint(pi), int(255 * out_cubic(pi * 1.4))
                    y = 560 + i * 300
                    x = M - 80 * (1 - e)
                    d.line([(x, y - 8), (x, y + 176)], fill=CLAY + (int(a * 0.85),), width=5)
                    d.text((x + 40, y), str(num), font=grotesk(104, 700), fill=CLAY + (a,))
                    d.text((x + 40, y + 130), str(txt), font=manrope(38, 500),
                           fill=CREAM_DIM + (a,))
            elif dato:
                pc = tramo_f(5.2, 1.1)
                if pc > 0:
                    a = int(255 * out_cubic(pc))
                    d.text((M - 10, 600), str(dato), font=grotesk(240, 700), fill=CREAM + (a,))
                if sub:
                    ps = tramo_f(6.2, 0.9)
                    if ps > 0:
                        a = int(255 * out_cubic(ps))
                        d.text((M, 960), sub.split("\n")[0], font=grotesk(56, 700),
                               fill=CREAM + (a,))
            elif sub:
                for i, ln in enumerate(sub.split("\n")[:3]):
                    pi = tramo_f(5.2 + i * 0.35, 0.9)
                    if pi <= 0:
                        continue
                    a = int(255 * out_cubic(pi))
                    e = out_quint(pi)
                    d.text((M, 640 + i * 110 + int(40 * (1 - e))), ln,
                           font=grotesk(64, 700), fill=CREAM + (a,))
            fundido(img, c, 1 - tramo_f(9.2, 0.4))
            return img

        # --- 3 · cierre ---------------------------------------------------
        p = tramo_f(9.7, 1.0)
        red_animada(img, clamp(p * 1.6), n=22, semilla=4)
        c = capa()
        d = ID.Draw(c)
        lines = rich_lines(d, "We tell you what's broken. *Free.*", W - M * 2, 96)
        yy = draw_rich(d, lines, M, 560 + int(46 * (1 - out_quint(p))), 96,
                       CREAM + (255,), italic_color=CLAY + (255,))
        pc = tramo_f(10.5, 0.8)
        if pc > 0:
            wp = int(500 * out_back(pc))
            d.rounded_rectangle([M, yy + 70, M + wp, yy + 180], radius=14, fill=CREAM + (255,))
            if pc > 0.5:
                d.text((M + 42, yy + 98), cta[:16], font=mono(34, bold=True),
                       fill=INK + (int(255 * clamp((pc - 0.5) * 2)),))
        pf = tramo_f(11.2, 0.9)
        if pf > 0:
            a, e = int(255 * out_cubic(pf)), out_quint(pf)
            yl = 1180 + int(30 * (1 - e))
            tracked(d, (M, yl), "PLEXGLOBE", grotesk(86, 700), CREAM + (a,), 10)
            d.line([(M, yl + 128), (M + int((W - M * 2) * e), yl + 128)],
                   fill=CLAY + (a,), width=5)
            tracked(d, (M, yl + 170), "plexglobe.com", mono(34), CREAM_DIM + (a,), 5)
        fundido(img, c, out_cubic(p * 1.5))
        return img

    return frame


REELS = {
    "intro": {
        "fn": frame_intro,
        "dur": 19.8,
        "titulo": "Quiénes somos",
    },
    "movil": {
        "fn": frame_movil,
        "dur": 17.2,
        "titulo": "Ábrela en el móvil (ES · réplica del reel 1)",
        "cortes": [3.4, 6.8, 11.0, 14.2],
    },
    "bilingue": {
        "fn": frame_bilingue,
        "dur": 20.2,
        "titulo": "One language / Un idioma",
        "cortes": [3.4, 6.6, 10.4, 13.8, 17.2],
    },
}


# ---------------------------------------------------------------- encode
def encode(nombre, spec):
    dur = spec["dur"]
    total = int(dur * FPS)
    destino = os.path.join(OUT, f"REEL-{nombre}_9x16.mp4")
    os.makedirs(OUT, exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        # pista de audio silenciosa: la API la prefiere y evita rarezas de reproduccion
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-level", "4.0",
        "-pix_fmt", "yuv420p", "-b:v", "4500k", "-maxrate", "5000k", "-bufsize", "9000k",
        "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        destino,
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(total):
        p.stdin.write(spec["fn"](f, dur).tobytes())
        if f % 60 == 0:
            print(f"    {f}/{total}", end="\r", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg fallo con {nombre}")
    mb = os.path.getsize(destino) / 1e6
    print(f"  ✓ REEL-{nombre}_9x16.mp4  ·  {dur:.1f}s  ·  {mb:.1f} MB")
    return destino


def portada(nombre, spec, segundo=None):
    """JPG de portada para la galeria de revision (el reel no se ve en <img>)."""
    f = int((segundo if segundo is not None else spec["dur"] * 0.36) * FPS)
    ruta = os.path.join(OUT, f"REEL-{nombre}_portada.jpg")
    spec["fn"](f, spec["dur"]).save(ruta, "JPEG", quality=90, subsampling=0)
    print(f"  ✓ REEL-{nombre}_portada.jpg")
    return ruta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo")
    args = ap.parse_args()
    items = {args.solo: REELS[args.solo]} if args.solo else REELS
    for nombre, spec in items.items():
        print(f"\n{nombre} · {spec['titulo']} · {spec['dur']}s")
        encode(nombre, spec)
        portada(nombre, spec)


if __name__ == "__main__":
    main()
