#!/usr/bin/env python3
"""
Plexglobe · banco de fondos abstractos de marca.

Genera imagenes de fondo unicas en la paleta de Plexglobe. Resuelve el problema
de fondo del banco de fotos: son infinitas, gratis, sin licencia que respetar y
nadie mas las tiene. Se usan igual que una foto en los estilos A, C y D.

  python3 fondos.py            -> genera el banco en fotos/
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

CREAM = (244, 237, 226)
INK = (28, 24, 19)
CLAY = (192, 86, 44)
ARENA = (214, 197, 172)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fotos")

FEED = (1080, 1350)
STORY = (1080, 1920)


def _mezcla(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def grano(img, fuerza=12, opacidad=22):
    w, h = img.size
    r = Image.effect_noise((w, h), fuerza).convert("L")
    img.alpha_composite(Image.merge("RGBA", (r, r, r, Image.new("L", (w, h), opacidad))))


# ---------------------------------------------------------------- generadores
def malla(size, base, acentos, semilla=1):
    """Degradado de malla: manchas de color desenfocadas. Suave y moderno."""
    random.seed(semilla)
    w, h = size
    im = Image.new("RGB", size, base)
    capa = Image.new("RGB", (w // 4, h // 4), base)
    d = ImageDraw.Draw(capa)
    for i in range(7):
        c = acentos[i % len(acentos)]
        cx, cy = random.randint(0, w // 4), random.randint(0, h // 4)
        r = random.randint(h // 16, h // 7)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    capa = capa.filter(ImageFilter.GaussianBlur(h // 26)).resize(size, Image.LANCZOS)
    im = Image.blend(im, capa, 0.82).convert("RGBA")
    grano(im)
    return im


def red(size, base, tinta, n=46, semilla=2):
    """Red de nodos a gran escala. El sello de marca, como protagonista."""
    random.seed(semilla)
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    capa = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    pts = [(random.randint(-40, w + 40), random.randint(-40, h + 40)) for _ in range(n)]
    for a in pts:
        for b in sorted(pts, key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)[1:4]:
            dist = math.hypot(a[0] - b[0], a[1] - b[1])
            op = max(0, int(90 * (1 - dist / (w * 0.6))))
            if op:
                d.line([a, b], fill=tinta + (op,), width=1)
    for (x, y) in pts:
        r = random.randint(3, 9)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tinta + (110,))
    im.alpha_composite(capa)
    grano(im)
    return im


def topografia(size, base, tinta, semilla=3):
    """Curvas de nivel. Sugiere profundidad y analisis sin decir nada."""
    random.seed(semilla)
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    capa = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    fases = [random.uniform(0, 6.28) for _ in range(4)]
    for k in range(26):
        pts = []
        for x in range(0, w + 12, 12):
            y = h * 0.5 + (k - 13) * (h / 30)
            for j, f in enumerate(fases):
                y += math.sin(x / (110 + j * 70) + f + k * 0.16) * (26 + j * 12)
            pts.append((x, y))
        d.line(pts, fill=tinta + (52 if k % 4 else 96,), width=2 if k % 4 == 0 else 1)
    im.alpha_composite(capa)
    grano(im)
    return im


def semitono(size, base, tinta, semilla=4):
    """Semitono: puntos que crecen con el degradado. Muy grafico, imprime bien."""
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    capa = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    paso = 26
    for y in range(paso, h, paso):
        for x in range(paso, w, paso):
            t = 1 - (y / h) * 0.95 - (x / w) * 0.12
            t = max(0.0, min(1.0, t))
            r = paso * 0.46 * t
            if r > 0.6:
                d.ellipse([x - r, y - r, x + r, y + r], fill=tinta + (200,))
    im.alpha_composite(capa)
    grano(im)
    return im


def orbitas(size, base, tinta, semilla=5):
    """Arcos concentricos descentrados. Da sensacion de sistema y movimiento."""
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    capa = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    cx, cy = int(w * 0.78), int(h * 0.24)
    for i in range(22):
        r = 90 + i * (max(w, h) / 15)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=tinta + (64 if i % 3 else 118,), width=2 if i % 3 == 0 else 1)
    im.alpha_composite(capa)
    grano(im)
    return im


def flujo(size, base, tinta, semilla=6):
    """Campo de flujo: lineas que siguen un ruido suave. Organico y unico."""
    random.seed(semilla)
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    capa = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)

    def angulo(x, y):
        return (math.sin(x / 190 + semilla) + math.cos(y / 150 - semilla)) * 1.35

    for _ in range(210):
        x, y = random.uniform(0, w), random.uniform(0, h)
        pts = [(x, y)]
        for _ in range(90):
            a = angulo(x, y)
            x += math.cos(a) * 7
            y += math.sin(a) * 7
            if not (-60 < x < w + 60 and -60 < y < h + 60):
                break
            pts.append((x, y))
        if len(pts) > 6:
            d.line(pts, fill=tinta + (44,), width=1)
    im.alpha_composite(capa)
    grano(im)
    return im


def prisma(size, base, tinta, semilla=7):
    """Rejilla en perspectiva. Habla de estructura y construccion."""
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    capa = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    hz = h * 0.34
    for i in range(-14, 30):
        x = w * 0.5 + i * (w / 13)
        d.line([(x, h), (w * 0.5 + i * 16, hz)], fill=tinta + (58,), width=1)
    y, paso = hz, 6.0
    while y < h:
        d.line([(0, y), (w, y)], fill=tinta + (52,), width=1)
        paso *= 1.22
        y += paso
    im.alpha_composite(capa)
    grano(im)
    return im


# ---------------------------------------------------------------- banco
PALETAS = [
    ("clay", CLAY, CREAM, [_mezcla(CLAY, INK, .45), _mezcla(CLAY, CREAM, .28), CLAY]),
    ("ink", INK, CREAM, [_mezcla(INK, CLAY, .40), _mezcla(INK, ARENA, .22), INK]),
    ("cream", CREAM, INK, [_mezcla(CREAM, CLAY, .30), ARENA, _mezcla(CREAM, INK, .12)]),
]

RECETAS = [
    ("malla", lambda s, base, tinta, acc, sem: malla(s, base, acc, sem)),
    ("red", lambda s, base, tinta, acc, sem: red(s, base, tinta, semilla=sem)),
    ("topografia", lambda s, base, tinta, acc, sem: topografia(s, base, tinta, sem)),
    ("semitono", lambda s, base, tinta, acc, sem: semitono(s, base, tinta, sem)),
    ("orbitas", lambda s, base, tinta, acc, sem: orbitas(s, base, tinta, sem)),
    ("flujo", lambda s, base, tinta, acc, sem: flujo(s, base, tinta, sem)),
    ("prisma", lambda s, base, tinta, acc, sem: prisma(s, base, tinta, sem)),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for nombre, fn in RECETAS:
        for pal, base, tinta, acc in PALETAS:
            for etiqueta, size in (("4x5", FEED), ("9x16", STORY)):
                im = fn(size, base, tinta, acc, abs(hash(nombre + pal)) % 97 + 1)
                f = f"fondo-{nombre}-{pal}-{etiqueta}.webp"
                im.convert("RGB").save(os.path.join(OUT, f), "WEBP", quality=88, method=5)
                n += 1
    print(f"{n} fondos de marca generados en fotos/")
    print(f"{len(RECETAS)} texturas × {len(PALETAS)} paletas × 2 formatos")


if __name__ == "__main__":
    main()
