#!/usr/bin/env python3
"""
Reel LISTA - «5 cosas que le faltan a la web de tu negocio en Miami».

Se renderiza DENTRO del repositorio (GitHub Actions). No se sube ningun MP4 a
mano: el video nace ya publicado y su URL de raw.githubusercontent es publica,
asi que el panel lo ve y se puede aprobar al momento.

Las fotos NO viven en el repositorio: se descargan de Unsplash en tiempo de
ejecucion a fotos/sectores/. Asi el repositorio solo guarda codigo y no engorda
con binarios que ademas ya estan alojados en otro sitio.

Por que este formato y no un escaparate: el reel de la cocteleria hizo 100
visualizaciones en 40 minutos y 6 en las tres horas siguientes. 54 personas lo
vieron -casi la mitad dos veces- y no tocaron nada. Un escaparate solo interesa
a quien ya te conoce; a un desconocido hay que darle algo QUE QUIERA GUARDARSE.
Guardar es ademas la accion mas barata: no le expone ante nadie.

    python3 reel_lista.py
"""
import os
import subprocess
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import plexglobe_render as R

AQUI = os.path.dirname(os.path.abspath(__file__))
FOTOS = os.path.join(AQUI, "fotos", "sectores")
SALIDA = os.path.join(AQUI, "salida")
ARCHIVO = "REEL-lista-5-cosas_9x16.mp4"

W, H, FPS, DUR = 1080, 1920, 30, 13.0
TINTA, CREMA, CLAY = (12, 10, 11), (244, 238, 236), (192, 86, 44)

# Area que la cuadricula del perfil NO recorta: se come ~10% por lado.
SEGURO = (140, 430, 940, 1500)

# Fotos de Unsplash, licencia de uso comercial sin atribucion obligatoria.
#
# OJO con la URL: el endpoint /photos/<id>/download NO sirve desde un runner.
# Devuelve 401 porque redirige a una URL firmada que espera sesion de navegador.
# Hay que apuntar directamente al CDN images.unsplash.com, que es publico.
UNSPLASH = {
    "intro": "photo-1690335008679-1e319b9fa3d8",
    "p1": "photo-1597692493647-25bd4240a3f2",
    "p2": "photo-1621873495884-845a939892d1",
    "p3": "photo-1641337221253-fdc7237f6b61",
    "p4": "photo-1535579710123-3c0f261c474e",
    "p5": "photo-1770334597610-8335702e8ab1",
    "cierre": "photo-1634449571010-02389ed0f9b0",
}

PUNTOS = [
    ("1", "El precio, a la vista",
     ["«Consultanos» es la frase que mas", "clientes ha costado en internet."], "p1"),
    ("2", "Reservar en dos toques",
     ["No un formulario de nueve campos", "que cae en un correo."], "p2"),
    ("3", "Que cargue en dos segundos",
     ["Si tarda cuatro, la mitad se va", "antes de ver nada."], "p3"),
    ("4", "Que se vea en un movil viejo",
     ["Tu cliente no tiene el ultimo", "iPhone. Tu tampoco lo tenias."], "p4"),
    ("5", "Espanol e ingles",
     ["En Miami elegir uno de los dos", "es renunciar a la mitad."], "p5"),
]
T0, TP = 1.7, 2.0
CORTES = [T0 + TP * k for k in range(len(PUNTOS) + 1)]


def bajar():
    """Trae las fotos si no estan. Se salta las que ya existen."""
    os.makedirs(FOTOS, exist_ok=True)
    for clave, ident in UNSPLASH.items():
        destino = os.path.join(FOTOS, clave + ".jpg")
        if os.path.exists(destino):
            continue
        url = ("https://images.unsplash.com/" + ident +
               "?w=2400&q=85&fm=jpg&fit=max")
        req = urllib.request.Request(url, headers={"User-Agent": "plexglobe-bot"})
        with urllib.request.urlopen(req, timeout=60) as r, open(destino, "wb") as f:
            f.write(r.read())
        print("  bajada " + clave + " (" + str(os.path.getsize(destino) // 1024) + " KB)")


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def out_quint(t):
    return 1 - (1 - t) ** 5


def tramo(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else 0.0


_C = {}


def recortar(im, w, h):
    im = im.convert("RGB")
    rd, rs = w / h, im.width / im.height
    if rs > rd:
        nw = int(im.height * rd)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = int(im.width / rd)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    return im.resize((w, h), Image.LANCZOS)


def foto(clave, tam):
    k = (clave, tam)
    if k not in _C:
        im = Image.open(os.path.join(FOTOS, clave + ".jpg"))
        im.draft("RGB", (2400, 2400))
        _C[k] = recortar(im, *tam)
    return _C[k]


def fundido(im, color, a):
    return im if a <= 0 else Image.blend(im, Image.new("RGB", im.size, color), clamp(a))


def oscurecer(im, k):
    return ImageEnhance.Brightness(im).enhance(k)


_V = {}


def velo(im, y0, y1, fuerza=0.55):
    """Oscurece una banda para que el texto se lea. La mascara es constante: si se
    calcula por fotograma el render tarda diez veces mas."""
    clave = (im.size, y0, y1, fuerza)
    if clave not in _V:
        col = np.zeros(im.height, np.float32)
        t = np.arange(y0, y1, dtype=np.float32)
        col[y0:y1] = 255 * fuerza * ((t - y0) / (y1 - y0)) ** 0.85
        col[y1:] = 255 * fuerza
        _V[clave] = Image.fromarray(np.repeat(col[:, None], im.width, 1).astype(np.uint8), "L")
    return Image.composite(Image.new("RGB", im.size, TINTA), im, _V[clave])


def texto(d, xy, txt, fuente, color, centro=True, track=0):
    if track:
        x, y = xy
        anchos = [d.textlength(c, font=fuente) + track for c in txt]
        if centro:
            x -= sum(anchos) / 2
        for c, a in zip(txt, anchos):
            d.text((x, y), c, font=fuente, fill=color)
            x += a
        return
    d.text(xy, txt, font=fuente, fill=color, anchor="mm" if centro else "la")


def sello(im):
    """El mismo en todos los reels: es lo que da la sintonia de marca."""
    d = ImageDraw.Draw(im)
    x0 = W // 2 - 118
    d.rounded_rectangle([x0, H - 96, x0 + 236, H - 52], 22, fill=(26, 21, 23))
    d.rectangle([x0 + 14, H - 84, x0 + 34, H - 64], fill=CLAY)
    texto(d, (x0 + 46, H - 82), "MADE BY PLEXGLOBE", R.mono(15), (196, 186, 190),
          centro=False, track=1.1)


def filmar(im, k=0.28, semilla=1):
    """Textura de camara sobre un render: halacion, vineta y grano. Al 0.28.
    A plena potencia la aberracion deja los textos con reborde y parece pantalla
    rota, no metraje: medido comparando 0.35, 0.6 y 1.0 sobre el mismo fotograma."""
    a = np.asarray(im, np.float32)
    lum = a.mean(axis=2)
    alto = np.clip((lum - 205) / 50, 0, 1)[..., None] * a
    b = np.asarray(Image.fromarray(alto.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(26)), np.float32)
    a = np.clip(a + b * (0.42 * k / 0.28) * 0.28, 0, 255)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = a * (1 - 0.30 * k * np.clip(r - 0.35, 0, 1.6) ** 1.7)[..., None]
    rng = np.random.default_rng(semilla)
    peso = 1.25 - a.mean(axis=2, keepdims=True) / 255 * 0.85
    a = a + rng.normal(0, 5.2 * k, (h, w, 1)) * peso
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def esc_intro(t):
    im = fundido(oscurecer(foto("intro", (W, H)), 0.30), TINTA, 0.42)
    d = ImageDraw.Draw(im)
    a = tramo(t, 0.1, 0.7)
    texto(d, (W // 2, 520), "PLEXGLOBE · MIAMI", R.mono(21),
          tuple(int(c * a) for c in (178, 168, 164)), track=5)
    b = out_quint(tramo(t, 0.2, 1.0))
    d.text((W // 2, 760 + int((1 - b) * 40)), "5 cosas", font=R.grotesk(132, 300),
           fill=tuple(int(c * b) for c in CREMA), anchor="mm")
    c = out_quint(tramo(t, 0.45, 1.25))
    d.text((W // 2, 900 + int((1 - c) * 40)), "que le faltan", font=R.serif_it(120),
           fill=tuple(int(v * c) for v in CLAY), anchor="mm")
    e = tramo(t, 0.75, 1.4)
    texto(d, (W // 2, 1035), "a la web de tu negocio.", R.grotesk(64, 300),
          tuple(int(v * e) for v in CREMA))
    return im


def esc_punto(t, k):
    num, tit, sub, clave = PUNTOS[k]
    # El zoom recorta de una copia escalada UNA vez. Redimensionar la foto
    # original en cada fotograma multiplicaba por diez el tiempo de render.
    z = 1.0 + 0.045 * t
    base = foto(clave, (int(W * 1.10), int(H * 1.10)))
    cw, ch = int(W * 1.10 / z), int(H * 1.10 / z)
    x, y = (base.width - cw) // 2, (base.height - ch) // 2
    im = base.crop((x, y, x + cw, y + ch)).resize((W, H), Image.BILINEAR)
    im = velo(fundido(oscurecer(im, 0.46), TINTA, 0.26), 560, 1150)

    d = ImageDraw.Draw(im)
    a = out_quint(clamp(t / 0.35))
    d.text((W // 2, 640 + int((1 - a) * 26)), num, font=R.grotesk(150, 300),
           fill=tuple(int(v * a) for v in CLAY), anchor="mm")
    b = out_quint(clamp((t - 0.12) / 0.45))
    d.text((W // 2, 830 + int((1 - b) * 24)), tit, font=R.grotesk(72, 300),
           fill=tuple(int(v * b) for v in CREMA), anchor="mm")
    c = tramo(t, 0.35, 0.85)
    for i, ln in enumerate(sub):
        texto(d, (W // 2, 960 + i * 56), ln, R.manrope(40),
              tuple(int(v * c) for v in (206, 197, 192)))

    # Barra de avance: decir cuanto queda sostiene la retencion, que es la
    # senal numero uno del algoritmo.
    d.rounded_rectangle([180, 1330, 900, 1340], 5, fill=(50, 43, 40))
    ancho = int(720 * ((k + min(1.0, t / TP)) / len(PUNTOS)))
    if ancho > 8:
        d.rounded_rectangle([180, 1330, 180 + ancho, 1340], 5, fill=CLAY)
    return im


def esc_cierre(t):
    if "f" not in _C:
        f = oscurecer(foto("cierre", (W, H)), 0.20)
        _C["f"] = fundido(f.filter(ImageFilter.GaussianBlur(30)), TINTA, 0.66)
    im = _C["f"].copy()
    d = ImageDraw.Draw(im)
    a = out_quint(clamp(t / 0.45))
    d.text((W // 2, 810 + int((1 - a) * 30)), "Guardatelo.", font=R.grotesk(112, 300),
           fill=tuple(int(v * a) for v in CREMA), anchor="mm")
    b = out_quint(clamp((t - 0.2) / 0.5))
    d.text((W // 2, 940 + int((1 - b) * 30)), "Lo vas a necesitar.",
           font=R.serif_it(104), fill=tuple(int(v * b) for v in CLAY), anchor="mm")
    c = tramo(t, 0.6, 1.05)
    texto(d, (W // 2, 1080), "Auditamos tu web gratis. Sin compromiso.",
          R.manrope(38), tuple(int(v * c) for v in (204, 195, 190)))
    e = tramo(t, 0.85, 1.3)
    texto(d, (W // 2, 1290), "plexglobe.com", R.mono(30),
          tuple(int(v * e) for v in CLAY), track=7)
    return im


def cuadro(t):
    if t < T0:
        im = esc_intro(t)
    elif t < T0 + TP * len(PUNTOS):
        k = int((t - T0) // TP)
        im = esc_punto(t - T0 - TP * k, k)
    else:
        im = esc_cierre(t - T0 - TP * len(PUNTOS))
    for c in CORTES:
        if 0 <= t - c < 0.14:
            im = fundido(im, TINTA, 1 - (t - c) / 0.14)
    if t < 0.22:
        im = fundido(im, TINTA, 1 - t / 0.22)
    if t > DUR - 0.25:
        im = fundido(im, TINTA, (t - (DUR - 0.25)) / 0.25)
    sello(im)
    return filmar(im, 0.28, semilla=int(t * 7) % 97)


def validar(ruta):
    """Contra la especificacion real de la API. Si algo no cuadra el flujo falla
    AQUI y no en Instagram 24 horas despues, que es cuando el contenedor caduca y
    ya no sirve de nada saberlo."""
    import json
    d = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", ruta], capture_output=True, text=True).stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(d["format"]["duration"])
    fallos = []
    if (v["width"], v["height"]) != (W, H):
        fallos.append("resolucion")
    if v["codec_name"] != "h264" or v.get("pix_fmt") != "yuv420p":
        fallos.append("codec")
    if not 23 <= fps <= 60:
        fallos.append("fps")
    if not 3 <= dur <= 900:
        fallos.append("duracion")
    if not a or a["codec_name"] != "aac" or int(a["sample_rate"]) != 48000:
        fallos.append("audio")
    if fallos:
        raise SystemExit("NO CUMPLE: " + ", ".join(fallos))
    print("  OK " + str(v["width"]) + "x" + str(v["height"]) + " " +
          str(round(fps)) + "fps " + str(round(dur, 1)) + "s aac48k")


def main():
    R.asegurar_fuentes()
    bajar()
    os.makedirs(SALIDA, exist_ok=True)
    mudo = "/tmp/lista-mudo.mp4"
    wav = "/tmp/lista.wav"
    final = os.path.join(SALIDA, ARCHIVO)

    n = int(DUR * FPS)
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", str(W) + "x" + str(H), "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", "-g", "60",
         "-movflags", "+faststart", mudo], stdin=subprocess.PIPE)
    for i in range(n):
        if i % 60 == 0:
            print("  " + str(i) + "/" + str(n), flush=True)
        p.stdin.write(cuadro(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg fallo al escribir el video")

    subprocess.run([sys.executable, os.path.join(AQUI, "audio.py"),
                    "--dur", str(DUR), "--cortes", ",".join(str(c) for c in CORTES),
                    "--out", wav], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mudo, "-i", wav,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-shortest", "-movflags", "+faststart", final], check=True)
    validar(final)

    # Portada del segundo 0,9: el primer fotograma es negro y no dice nada.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.9", "-i", final,
                    "-frames:v", "1", "-q:v", "3",
                    os.path.join(SALIDA, ARCHIVO.replace(".mp4", ".jpg"))], check=True)
    print("-> " + final)


if __name__ == "__main__":
    main()
