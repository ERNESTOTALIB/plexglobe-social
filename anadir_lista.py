#!/usr/bin/env python3
"""
Anade el reel LISTA a salida/catalogo.json.

Se ejecuta DESPUES de generar.py, que reescribe el catalogo entero desde
contenido.json. Si esto corriera antes, generar.py se lo llevaria por delante.

Conserva el estado de aprobacion y publicacion si la pieza ya existia: si no,
cada render semanal borraria lo que Ernesto ya habia aprobado.
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(AQUI, "salida", "catalogo.json")
BASE = ("https://raw.githubusercontent.com/ERNESTOTALIB/"
        "plexglobe-social/main/salida/")
ARCHIVO = "REEL-lista-5-cosas_9x16.mp4"

PIE = (
    "Guardatelo antes de que se te olvide. Son cinco y las cinco cuestan dinero."
    "\n\n1 - El precio, a la vista. «Consultanos por privado» es probablemente la "
    "frase que mas clientes ha costado en la historia de internet. Quien se va "
    "porque le parece caro se iba a ir igual, solo que ahora se va despues de "
    "hacerte perder media hora."
    "\n\n2 - Reservar en dos toques. No un formulario de nueve campos que cae en un "
    "correo que se mira los martes. Tu cliente decide a las once de la noche desde "
    "el sofa. A esa hora nadie llama, y a la manana siguiente ya se le olvido."
    "\n\n3 - Que cargue en dos segundos. Si tarda cuatro, la mitad se va antes de "
    "ver nada. No es que no les gustes: es que nunca llegaron a verte."
    "\n\n4 - Que se vea en un movil viejo. Tu cliente no tiene el ultimo iPhone. Tu "
    "tampoco lo tenias hace tres anos."
    "\n\n5 - Espanol e ingles. Aqui elegir uno de los dos es renunciar a la mitad de "
    "la ciudad, y encima a la mitad que probablemente mas gasta."
    "\n\nNinguna de las cinco es cara. Ninguna es de diseno. Las cinco son "
    "decisiones sobre que ve una persona en los tres primeros segundos."
    "\n\n---\n\nSave this before you forget. Five things, and all five cost you "
    "money. Prices visible. Booking in two taps. Loads in two seconds. Works on an "
    "old phone. Spanish and English."
    "\n\nNone of them are expensive. None of them are about design."
    "\n\nAuditamos tu web gratis y te decimos cuales te faltan."
    "\n\nPlexglobe - Diseno web en Miami"
    "\n\n#miami #miamibeach #brickell #wynwood #coralgables #miamiflorida #miamifl "
    "#southflorida #doral #miamibusiness #smallbusinessmiami #localbusiness "
    "#miamientrepreneur #emprendedores #negociosenmiami #restaurantowner #barowner "
    "#salonowner #gymowner #hospitality #webdesign #webdesignmiami #disenowebmiami "
    "#paginasweb #webdesigner #uxui #seolocal #marketingdigital #brandidentity "
    "#plexglobe")

ENTRADA = {
    "id": "R-LISTA-01",
    "semana": 1,
    "dia": "martes",
    "idioma": "en+es",
    "alternativa": False,
    "serie": "",
    "formato": "Reel",
    "plantilla": "STORY",
    "medida": "1080x1920",
    "diapositivas": 1,
    "imagen_url": BASE + ARCHIVO.replace(".mp4", ".jpg"),
    "imagenes": [BASE + ARCHIVO.replace(".mp4", ".jpg")],
    "video_url": BASE + ARCHIVO,
    "caption": PIE,
}


def main():
    cat = json.load(open(CAT, encoding="utf-8")) if os.path.exists(CAT) else []
    por_id = {c["id"]: c for c in cat}
    viejo = por_id.get(ENTRADA["id"], {})
    nuevo = dict(ENTRADA)
    # no pisar lo que ya estaba decidido
    nuevo["aprobado"] = viejo.get("aprobado", "")
    nuevo["publicado_ig"] = viejo.get("publicado_ig", "")
    nuevo["publicado_fb"] = viejo.get("publicado_fb", "")
    por_id[nuevo["id"]] = nuevo
    salida = sorted(por_id.values(), key=lambda c: (c.get("semana", 9), c["id"]))
    json.dump(salida, open(CAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("catalogo: " + str(len(salida)) + " piezas")


if __name__ == "__main__":
    main()
