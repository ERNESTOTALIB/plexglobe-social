# Plexglobe · contenido social automatizado

Genera las piezas de Instagram y Facebook a partir del sistema de diseño del PDF de marca,
las publica como imágenes accesibles por URL, y deja a Make la parte de publicar.

**Estado actual:** Página de Facebook creada · Instagram `@plexglobe` convertido a Empresa y vinculado · falta subir esto a GitHub y montar el escenario de Make.

---

## Por qué GitHub y no solo Make

Corrijo algo que dije antes: **Make no sustituye a GitHub Actions**. Hacen cosas distintas.

- Make **no puede ejecutar** el renderizador de Python. No genera imágenes.
- La documentación de Make lo dice literalmente: *"No puedes usar archivos de Google Drive aunque estén compartidos públicamente: la API de Instagram no puede descargar archivos de ahí."*

Así que hace falta un sitio que (1) ejecute Python y (2) sirva las imágenes por URL pública directa. GitHub hace las dos gratis:

| Pieza | Quién | Coste |
|---|---|---|
| Renderizar las 7 imágenes cada domingo | GitHub Actions | 0 € |
| Servirlas por URL pública | raw.githubusercontent.com | 0 € |
| Tu revisión y aprobación | Google Sheets | 0 € |
| Publicar en IG + FB | Make (plan Free) | 0 € |

---

## Contenido del repositorio

```
contenido.json              28 posts = 4 semanas, rotan solas
generar.py                  renderiza la semana que toca + escribe el manifest
plexglobe_render.py         motor de render (plantillas A, B, D, E, F, Story)
fonts/                      Space Grotesk · Instrument Serif · Manrope · Space Mono
salida/                     imágenes generadas + manifest.json
.github/workflows/semanal.yml   cron de los domingos a las 18:00 (Madrid)
```

---

## Puesta en marcha

### 1 · Subir a GitHub (10 min, una vez)

1. Crea una cuenta en github.com si no la tienes (gratis).
2. *New repository* → nombre `plexglobe-social` → **Público** (tiene que serlo: Instagram necesita descargar las imágenes sin autenticación).
3. *uploading an existing file* → arrastra **todo el contenido de esta carpeta**.
4. Pestaña **Actions** → *I understand my workflows, go ahead and enable them*.
5. **Settings → Actions → General → Workflow permissions** → marca **Read and write permissions** → *Save*. Sin esto el bot no puede subir las imágenes.
6. Actions → *Generar contenido semanal* → **Run workflow** para probarlo ya.

Comprueba que funciona abriendo en el navegador:
`https://raw.githubusercontent.com/TU_USUARIO/plexglobe-social/main/salida/manifest.json`

Si ves el JSON, está listo.

### 2 · Hoja de aprobación

Crea una hoja de Google llamada `Plexglobe · Cola de publicación` con estas columnas:

| id | dia | formato | imagen_url | caption | aprobado | publicado_ig | publicado_fb |
|---|---|---|---|---|---|---|---|

Tu Google ya está conectado en Make (`ernestotalib@gmail.com`).

### 3 · Escenario de Make

**Escenario A — «Plexglobe · cargar semana»** (domingos 18:30)

1. `Schedule` → semanal, domingo 18:30
2. `HTTP · Make a request` → GET a la URL del `manifest.json` de arriba
3. `JSON · Parse JSON`
4. `Iterator`
5. `Google Sheets · Add a row` → vuelca cada pieza en la hoja, con `aprobado` vacío
6. `Email` → aviso de que ya puedes revisar

**Escenario B — «Plexglobe · publicar»** (diario 09:30)

1. `Schedule` → diario 09:30
2. `Google Sheets · Search rows` → filtro: `dia` = hoy **y** `aprobado` = `SI` **y** `publicado_ig` vacío
3. `Router`
   - Rama IG: `Instagram for Business · Create a photo post` → Page `Plexglobe`, Image URL = `imagen_url`, Caption = `caption`
   - Rama FB: `Facebook Pages · Create a Post` → Page `Plexglobe`
4. `Google Sheets · Update a row` → marca `publicado_ig` / `publicado_fb` con la fecha

**La conexión de Meta la creas tú** dentro de Make: al añadir el módulo de Instagram, *Create a connection* → te lleva al dominio de Meta → autorizas. El token se queda en Make. Nadie más lo ve.

---

## Consumo del plan Free de Make

Verificado sobre tu licencia: 1.000 operaciones/mes, 2 escenarios activos, intervalo mínimo 15 min.

| | ops/mes |
|---|---|
| Escenario A (4 domingos × ~11 ops) | ~44 |
| Escenario B (30 días × ~5 ops) | ~150 |
| Margen para reintentos | ~50 |
| **Total** | **~244 de 1.000** |

Usas los 2 escenarios disponibles. Justo, pero entra.

---

## Avisos que conviene tener presentes

- **Cuentas Creator no valen.** La documentación de Make lo dice explícitamente. Por eso elegimos *Empresa*. Si alguien cambia el tipo de cuenta, la automatización deja de funcionar.
- **El repositorio tiene que ser público.** Si lo pones privado, `raw.githubusercontent.com` deja de servir las imágenes e Instagram no puede descargarlas.
- **Insights de Instagram no funcionan por debajo de 100 seguidores.** No es un fallo del montaje.
- **Límite de publicación de Meta:** la documentación indica 50 publicaciones por 24 h vía API. Con 1 al día no es un problema.
- **Los reels y los carruseles completos no están cubiertos aquí.** Esto genera portadas 4:5 y verticales 9:16. El vídeo real sigue siendo trabajo manual — no cambia por usar Make.
- **Arranca despacio.** Perfil vacío + cero seguidores + publicación automática diaria es el patrón que Meta mira con más lupa. Pon foto, bio y 3-4 publicaciones a mano antes de encender el cron.

---

## Uso local

```bash
pip install pillow
python3 generar.py             # la semana que toca
python3 generar.py --semana 2  # una semana concreta
python3 generar.py --todo      # las 4 semanas de golpe
```

## Añadir más contenido

Edita `contenido.json` y añade entradas con `"semana": 5`, `6`... El rotador se adapta solo
al número de semanas que encuentre. Plantillas disponibles:

| clave | plantilla | campos |
|---|---|---|
| `A` | Propuesta de valor | `titular`, `sub` |
| `B` | Caso / Resultado | `titulo_caso`, `sub`, `metrica` |
| `D` | Carrusel educativo | `titular`, `kicker`, `pagina` |
| `E` | Testimonial | `titular`, `autor`, `sub` |
| `F` | Auditoría gratis | `titular`, `kicker`, `cta` |
| `STORY` | Vertical 9:16 | `titular`, `kicker`, `pie` |

Los `*asteriscos*` alrededor de una palabra la ponen en Instrument Serif cursiva, como en el PDF.
