# SaludVerifica RAG

**Sistema inteligente de verificación de información sanitaria mediante RAG.**
Proyecto académico: contraste preliminar de mensajes con evidencia oficial, enfocado en salud y Chiapas.

## Ejecutar con Docker

Requisito: Docker Desktop iniciado, con contenedores Linux y Docker Compose.
Desde esta carpeta:

```bash
docker compose up --build -d
```

Abre **http://localhost:8501**. Primera construcción requiere internet para descargar imagen y dependencias; no hay modelos que descargar. Una vez construida la imagen, consultas locales no requieren internet ni API.

```bash
docker compose ps
docker compose logs --tail 50 web
docker compose down
docker compose up -d
```

`down` conserva el volumen de documentos. **No uses `down -v` si quieres conservar fuentes incorporadas.** El navegador debe abrirse en el mismo equipo; por defecto puerto solo está expuesto en localhost.

## Demostración de cinco minutos

Sigue [docs/DEMO_5_MINUTOS.md](docs/DEMO_5_MINUTOS.md). Los textos están precargados en el selector de ejemplos. Mantén DeepSeek desactivado para resultados reproducibles.

## DeepSeek opcional

**Opción rápida:** en la barra lateral abre **Configuración de IA**, pega solo la API key en el campo de contraseña y pulsa **Comprobar conexión**. Esa clave queda en memoria de la sesión, no se escribe en disco. Activa **Usar DeepSeek** para el contraste. Conexión aceptada no garantiza saldo suficiente para generar respuestas.

**Opción persistente con Docker:**

Crea un archivo `.env` junto a `compose.yaml`, tomando como referencia `.env.example`:

```dotenv
DEEPSEEK_API_KEY=tu_clave_real
APP_PORT=8501
```

Son **dos líneas separadas**. `DEEPSEEK_API_KEY=APP_PORT=8501` es incorrecto. Se necesita una clave real del portal de API de DeepSeek, no contraseña ni acceso al chat.

Después ejecuta `docker compose up -d --force-recreate` y activa el interruptor en la web. La API puede tener costo según cuenta y consumo. No es necesaria para demo. No se ha validado con una clave real incluida en este proyecto.

La afirmación y fragmentos se envían a DeepSeek únicamente al activar ese modo. No introducir datos personales. Los errores de API conservan el análisis local; no se muestran ni registran claves.

## Funcionamiento y límites

- **Recuperación:** TF-IDF de palabras y caracteres, similitud coseno, varios fragmentos. Es recuperación léxica; no embeddings semánticos.
- **Modo local:** fichas revisadas con citas, coincidencia literal de oraciones completas o abstención. Fichas iniciales tienen alcance deliberadamente limitado y visible; no son un clasificador general.
- **Modo generativo opcional:** DeepSeek recibe solo fragmentos recuperados y debe devolver citas literales comprobables. Comprobar citas no garantiza interpretación correcta; requiere supervisión.
- **Incorporación:** HTML de dominios oficiales admitidos; extracción, revisión previa y almacenamiento SQLite. No búsqueda automática en toda internet, PDF ni actualización programada.
- **Fechas:** publicación y consulta diferenciadas. Fecha no extraíble se muestra como desconocida. No se inventa.
- **Fuentes:** seis publicaciones iniciales con extractos atribuidos (comunicado local, desinformación, VIH, dengue, rabia y VPH) y una copia de contingencia adicional sobre sarampión. No se presenta copia local como descarga en vivo.
- **Seguridad clínica:** filtro heurístico, no exhaustivo. No diagnostica ni prescribe.
- **Sin evidencia** no significa falso; similitud no significa verdadero.
- **Evidencia conflictiva** es una salida posible del modo generativo, no una categoría simulada en modo local.

El panel de incorporación es de operador único para demo. Una publicación institucional necesita autenticación, permisos de revisión, cuotas y control de versiones antes de ofrecerse a terceros. No hay historial de consultas persistente: solo documentos.

### Dos tipos de búsqueda

- **Verificar un mensaje:** contrasta una afirmación. Ejemplos por tema incluyen VIH y contacto cotidiano, gravedad del dengue, VPH y rabia. Fichas locales revisadas cubren únicamente formulaciones indicadas.
- **Consultar información:** ofrece respuestas breves revisadas para preguntas cubiertas en `data/faq.json`, únicamente si su fuente y texto de respaldo están guardados. Para otras preguntas, sin IA presenta un extracto marcado como información parcial; con DeepSeek redacta respuesta limitada a las citas validadas. No genera un dictamen de veracidad sobre una pregunta.

Vista de escritorio en dos columnas: consulta a izquierda y resultado a derecha. El panel derecho tiene pestañas Respuesta, Fuentes y Método. La respuesta y referencia principal se ven primero; las citas completas y detalles se consultan sin desplazar toda la página. En móvil las columnas se apilan.

Al actualizar imagen, las nuevas fuentes iniciales se incorporan al volumen con `INSERT OR IGNORE`; publicaciones previas no se sobrescriben. URL sin esquema recibe HTTPS automáticamente; portada de portal se rechaza con explicación.

## Arquitectura

```text
streamlit_app.py   Interfaz, ejemplos y ficha descargable
app/core.py       Recuperación, reglas conservadoras y DeepSeek
app/sources.py    Extracción web y persistencia SQLite
data/seed.json    Extractos y fichas revisadas iniciales
data/demo_source.json  Extracto de contingencia (no incorporado inicialmente)
tests/           Comportamiento, persistencia, errores y flujo web
```

Dependencias directas fijadas en `requirements.txt`. Python 3.12 dentro del contenedor. SQLite y unittest pertenecen a biblioteca estándar. Las dependencias transitivas se resuelven al construir; para reproducir exactamente esta construcción, trasladar imagen Docker.

## Pruebas dentro de Docker

PowerShell, desde esta carpeta:

```powershell
docker run --rm --mount "type=bind,source=$($PWD.Path),target=/workspace,readonly" --workdir /workspace --env DATA_DIR=/tmp/saludverifica-tests saludverifica-rag:1.0 python -m unittest discover -s tests -v
```

Linux/macOS:

```bash
docker run --rm -v "$PWD:/workspace:ro" -w /workspace -e DATA_DIR=/tmp/saludverifica-tests saludverifica-rag:1.0 python -m unittest discover -s tests -v
```

Las pruebas no necesitan internet, no usan saldo y no modifican corpus de presentación.

## Trasladar a otro equipo

### Con repositorio publicado

```bash
git clone https://github.com/TU_USUARIO/sistema-verificacion-salud-rag.git
cd sistema-verificacion-salud-rag
docker compose up --build -d
```

URL anterior es una plantilla, no un repositorio publicado automáticamente. `.env` y documentos locales no se suben a Git. No hay que instalar Python en equipo destino.

### Llevar imagen sin reconstruir (equipos de misma arquitectura)

En origen:

```bash
docker save -o saludverifica-rag.tar saludverifica-rag:1.0
```

Lleva archivo junto con carpeta del proyecto. En destino:

```bash
docker load -i saludverifica-rag.tar
docker compose up -d --no-build
```

Esto incluye corpus inicial y copia de contingencia, **no el volumen de documentos agregados**. Para demo, incorpora la fuente de nuevo con botón de contingencia. Si arquitecturas difieren (por ejemplo ARM y x86), reconstruye en destino.

## Si algo falla

- Docker no conecta: abre Docker Desktop y espera inicio del motor Linux.
- Puerto ocupado: en `.env`, define `APP_PORT=8502` y recrea servicio; abre puerto 8502.
- URL da 404 o tarda: utiliza copia local de contingencia, identificada en interfaz.
- Web no muestra cambios de código: `docker compose up --build -d`.
- DeepSeek falla: desactiva interruptor; demo local sigue disponible.
- Primera carga: espera estado `healthy` con `docker compose ps`.

## Presentación y escalabilidad

Valor: menos tiempo buscando evidencia, explicación trazable y reconocimiento explícito de incertidumbre. Evolución: embeddings multilingües, evaluación con expertos, múltiples regiones, revisión colaborativa y reportes institucionales. Hipótesis comercial: servicio para medios y comunicación sanitaria; pendiente validación con usuarios.

Herramienta informativa: no sustituye consulta médica ni verificación oficial. Las publicaciones conservan autoría de instituciones originales; el repositorio incorpora extractos atribuidos para demostración académica.
