#!/usr/bin/env python3
"""
Plexglobe · base sonora original para los reels.

Por qué existe: @plexglobe es cuenta de EMPRESA, asi que Instagram la limita a
la Meta Sound Collection y las canciones de tendencia no estan disponibles.
Y la API de publicacion no puede adjuntar musica de ninguna forma. Sin esto,
todo reel automatizado sale mudo.

Esto es sintesis pura (senos + ruido filtrado). No hay ni una muestra de nadie:
la pista es 100% de Plexglobe, no la puede reclamar el fingerprint de Meta y
se puede reutilizar en anuncios sin licencia.

Uso:
    python3 audio.py --dur 19.8 --cortes 3.0,6.2,9.8,13.2,16.8 --out cama.wav
"""
import argparse
import numpy as np

SR = 48000            # 48 kHz: lo que pide la API de Instagram
BPM = 100.0
BEAT = 60.0 / BPM     # 0,6 s
BAR = BEAT * 4        # 2,4 s

# La menor con novena. Oscuro pero no lugubre: es una marca, no un funeral.
A1, A2, C4, E4, B4 = 55.00, 110.00, 261.63, 329.63, 493.88


def env(n, ataque, caida, curva=2.5):
    """Envolvente percusiva: sube rapido, cae exponencial."""
    t = np.arange(n) / SR
    a = np.clip(t / max(ataque, 1e-6), 0, 1)
    d = np.exp(-t / max(caida, 1e-6)) ** (1 / curva)
    return a * d


def poner(buf, inicio, trozo, gan=1.0):
    i = int(inicio * SR)
    j = min(len(buf), i + len(trozo))
    if i >= len(buf) or j <= i:
        return
    buf[i:j] += trozo[: j - i] * gan


def bombo(dur=0.34):
    """Seno con caida de tono: pega en el pecho sin ocupar la mezcla."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 58 * np.exp(-t * 26) + 42                 # 100 Hz -> 42 Hz
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return x * env(n, 0.001, 0.075, 1.6)


def tick(dur=0.055, brillo=7000):
    """Ruido filtrado paso alto, muy bajito. Marca el pulso sin cansar."""
    n = int(dur * SR)
    x = np.random.default_rng(4).normal(0, 1, n)
    # paso alto de un polo, suficiente y barato
    a = np.exp(-2 * np.pi * brillo / SR)
    y = np.zeros(n)
    prev_x = prev_y = 0.0
    for i in range(n):
        y[i] = a * (prev_y + x[i] - prev_x)
        prev_x, prev_y = x[i], y[i]
    return y * env(n, 0.0005, 0.018, 1.2)


def golpe(dur=1.6):
    """Acento de cambio de escena: subgrave + soplo que se abre."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (46 * np.exp(-t * 5) + 34) * t) * np.exp(-t / 0.42)
    aire = np.random.default_rng(9).normal(0, 1, n) * np.exp(-t / 0.14) * 0.11
    return (sub * 0.85 + aire) * env(n, 0.004, 0.5, 1.4)


def drone(dur):
    """Colchon grave continuo con respiracion lenta. Da cuerpo al silencio."""
    t = np.arange(int(dur * SR)) / SR
    resp = 0.78 + 0.22 * np.sin(2 * np.pi * t / 4.8)
    x = np.sin(2 * np.pi * A1 * t) * 0.62
    x += np.sin(2 * np.pi * A2 * t + 0.6) * 0.26
    x += np.sin(2 * np.pi * (A2 * 1.003) * t) * 0.12     # batido suave
    return x * resp


def pad(dur, notas=(C4, E4, B4)):
    """Acorde con entrada lenta. Se abre y se cierra por escena."""
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    for k, f in enumerate(notas):
        x += np.sin(2 * np.pi * f * t + k * 1.1) * (0.5 ** (k * 0.55))
        x += np.sin(2 * np.pi * f * 1.004 * t) * 0.18 * (0.5 ** (k * 0.55))
    return x / len(notas)


def cama(dur, cortes):
    n = int(dur * SR)
    mezcla = np.zeros(n)

    # --- graves y colchon -------------------------------------------------
    mezcla += drone(dur)[:n] * 0.26

    p = pad(dur)[:n]
    # el pad respira: se abre justo despues de cada corte de escena
    sobre = np.zeros(n)
    bordes = [0.0] + list(cortes) + [dur]
    for a, b in zip(bordes[:-1], bordes[1:]):
        i, j = int(a * SR), int(b * SR)
        m = j - i
        if m <= 0:
            continue
        t = np.linspace(0, 1, m)
        sobre[i:j] = np.sin(np.pi * t) ** 0.85
    mezcla += p * sobre * 0.15

    # --- pulso ------------------------------------------------------------
    k, b_ = bombo(), tick()
    compas = 0.0
    while compas < dur:
        poner(mezcla, compas, k, 0.52)                 # 1
        poner(mezcla, compas + BEAT * 2, k, 0.44)      # 3
        for e in range(8):                             # corcheas
            gan = 0.052 if e % 2 else 0.030
            poner(mezcla, compas + e * BEAT / 2, b_, gan)
        compas += BAR

    # --- acentos de escena ------------------------------------------------
    g = golpe()
    for c in cortes:
        poner(mezcla, c, g, 0.60)
    poner(mezcla, 0.0, g, 0.45)

    # --- salida -----------------------------------------------------------
    salida = int(1.5 * SR)                             # cierre limpio
    mezcla[-salida:] *= np.linspace(1, 0, salida) ** 1.6
    mezcla[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))

    # limitador blando: comprime picos sin achatar el cuerpo
    mezcla = np.tanh(mezcla * 1.15) / np.tanh(1.15)
    mezcla *= 0.82 / (np.abs(mezcla).max() + 1e-9)
    return mezcla


def escribir_wav(ruta, mono):
    import wave
    est = np.stack([mono, mono], axis=1)               # estereo, 2 canales
    pcm = (np.clip(est, -1, 1) * 32767).astype("<i2")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, default=19.8)
    ap.add_argument("--cortes", default="3.0,6.2,9.8,13.2,16.8")
    ap.add_argument("--out", default="cama.wav")
    a = ap.parse_args()
    cortes = [float(x) for x in a.cortes.split(",") if x.strip()]
    escribir_wav(a.out, cama(a.dur, cortes))
    print(f"✓ {a.out} · {a.dur}s · {BPM:.0f} BPM · acentos en {cortes}")


if __name__ == "__main__":
    main()
