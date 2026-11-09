# Demostración · cinco minutos

## Preparación antes de entrar

1. Docker Desktop iniciado y `docker compose up -d` ejecutado.
2. Abrir http://localhost:8501 y verificar estado `healthy` con `docker compose ps`.
3. Mantener **Usar DeepSeek desactivado**, dentro de **Configuración de IA**. Resultados siguientes son de modo local, no de un LLM.
4. Verificar seis documentos iniciales. Si ya incorporaste fuente OMS de sarampión, puedes demostrar incorporación en otra copia del proyecto con un nombre de proyecto Compose diferente: `docker compose -p ensayo-limpio up -d`. Detén servicio anterior primero para liberar puerto. Cada nombre usa volumen independiente.
5. Tener esta guía abierta. Ejemplos se seleccionan en web; no hace falta escribirlos.
6. Internet solo es necesario para extracción en vivo. Copia de contingencia ofrece mismo paso de crecimiento, claramente identificada.

## Guion

### 0:00–0:35 · Problema y objetivo

> Recibimos mensajes sobre salud sin contexto. Verificarlos exige buscar y comprender publicaciones oficiales. SaludVerifica facilita ese contraste y muestra fuentes; cuando no puede concluir, lo indica.

### 0:35–1:05 · Respaldo

Elegir modo **Verificar un mensaje**, seleccionar **1 · Información en redes** y pulsar **Verificar mensaje**.

> La información errónea es información falsa que se difunde sin intención de engañar.

**Esperado:** RESPALDADA, ficha revisada, cita OMS, publicación 2024-02-06.

Explicar: conclusión tiene fragmento concreto, no solo nombre de institución.

### 1:05–1:45 · Refutación con alcance

Seleccionar **2 · Noticia de Chiapa de Corzo** y verificar.

> En Chiapa de Corzo falleció un niño por sarampión en el hospital.

**Esperado:** REFUTADA. Comunicado del 2026-01-27 informa PCR negativa.

Explicar: dictamen se refiere al caso específico del comunicado; no demuestra nada sobre otros fallecimientos. Abrir fragmento y señalar fecha y enlace.

### 1:45–2:20 · Abstención

Seleccionar **3 · Mensaje sobre vacunas** y verificar.

> La vacuna del sarampión causa magnetismo en el brazo de los niños en Tuxtla.

**Esperado:** EVIDENCIA INSUFICIENTE, aunque aparezcan documentos relacionados.

> Tener palabras en común con un comunicado no prueba afirmación. El prototipo original fallaba aquí; ahora separa recuperación de verificación.

### 2:20–3:45 · Plus: incorporar una fuente

1. Seleccionar **5 · Fuente nueva** y analizar antes de incorporarla.
2. **Esperado inicialmente:** EVIDENCIA INSUFICIENTE.
3. Ir a **Fuentes**. URL predeterminada:
   `https://www.who.int/es/news-room/fact-sheets/detail/measles`
4. Pulsar **Buscar publicación**. Mostrar título y texto. Si falla, abrir **Otras opciones**, pulsar **Usar copia local de contingencia** y explicar que es extracto guardado, no descarga en vivo.
5. Marcar casilla de revisión. Pulsar **Guardar fuente**.
6. Volver a **Verificar**, seleccionar ejemplo 5 y pulsar **Verificar mensaje**.

Texto exacto:

> La vacunación comunitaria es la forma más eficaz de prevenir el sarampión y debería extenderse a todos los niños.

**Esperado después:** RESPALDADA por **coincidencia literal con oración de fuente**, sin ficha precargada para este documento.

> El sistema ahora recupera una publicación que antes no tenía. Modo local demuestra coincidencia documental; contraste de paráfrasis requiere modo generativo u otra técnica evaluada.

### 3:45–4:15 · Seguridad y utilidad

Seleccionar **4 · Consulta clínica**:

> Tengo fiebre y manchas rojas, ¿qué medicamento puedo tomar en Chiapas?

**Esperado:** DERIVACIÓN CLÍNICA, sin tratamiento ni diagnóstico.

Si queda tiempo, descargar ficha de un caso anterior y explicar que contiene fuentes, no solo resultado.

### 4:15–5:00 · Arquitectura, crecimiento y cierre

> Python y Streamlit presentan evidencia; TF-IDF recupera fragmentos; reglas conservadoras y fichas revisadas cubren casos acotados. DeepSeek opcional incorpora contraste generativo con citas. SQLite conserva documentos y Docker reproduce entorno.
>
> Podemos crecer a otras regiones, ampliar fuentes y ofrecer revisión colaborativa a comunicadores y organizaciones. Antes de uso real, necesitamos ampliar evaluación con expertos y validar utilidad con usuarios.

## Preguntas probables

**¿Es un verificador universal?** No. Es un asistente de contraste con corpus acotado, alcance explícito y abstención.

**¿Dónde está RAG?** Recuperación documental alimenta contraste generativo al activar DeepSeek. Sin API, versión local utiliza recuperación y reglas; no se presenta como LLM.

**¿Memorizaron ejemplos?** Fichas revisadas resuelven casos específicos y su método se muestra. Incorporación de una fuente nueva demuestra recuperación dinámica; coincidencia literal es otra capacidad explícita. No afirmamos comprensión general en modo local.

**¿Por qué no responde todo?** Solo concluye dentro de evidencia y capacidades disponibles; ausencia en corpus no prueba falsedad.

**¿Tiene 100% de precisión?** No se afirma. Pruebas de regresión validan comportamientos concretos; falta conjunto representativo etiquetado por expertos.

**¿Qué venderían?** Ahorro de tiempo y trazabilidad para revisión de mensajes; posible servicio institucional con gestión y revisión de fuentes. Es hipótesis comercial por validar.

## Pruebas adicionales si jurado pregunta

### Nuevos ejemplos por tipo de búsqueda

**Verificar un mensaje**, sin API:

| Ejemplo | Resultado local esperado |
|---|---|
| 7 · VIH y contacto cotidiano | REFUTADA: compartir alimentos no transmite VIH |
| 8 · Gravedad del dengue | REFUTADA: puede haber casos graves |
| 9 · Vacunación contra el VPH | REFUTADA: vacuna preventiva, no tratamiento |
| 10 · Animales y rabia | REFUTADA: afecta a otros mamíferos |

**Consultar información:** seleccionar pregunta de VIH, dengue, VPH o rabia y pulsar **Consultar fuentes**. Estas preguntas tienen respuestas breves revisadas y respaldadas por las fuentes guardadas, disponibles sin API. Para preguntas no cubiertas, modo local muestra información parcial. Con DeepSeek genera explicación con citas; resultados del proveedor real deben comprobarse con clave antes de presentación.

La respuesta aparece a derecha de la consulta. Pestaña **Respuesta** muestra explicación y fuente principal; **Fuentes** muestra citas y publicaciones; **Método** explica técnica. No hace falta bajar por una lista de tarjetas para encontrar respuesta.

| Texto | Resultado local esperado |
|---|---|
| En Chiapa de Corzo el niño del comunicado del 27 de enero de 2026 no falleció por sarampión. | RESPALDADA; negación explícita revisada |
| En Chiapa de Corzo el niño no falleció por sarampión. | EVIDENCIA INSUFICIENTE; no aplica regla amplia |
| En Chiapa de Corzo falleció un niño por sarampión en el hospital. Además la vacuna produce magnetismo. | EVIDENCIA INSUFICIENTE; no extiende dictamen a afirmación compuesta |
| Los extraterrestres controlan los hospitales. | EVIDENCIA INSUFICIENTE |
| Campo vacío | Solicita ingresar afirmación |

No repetir análisis muchas veces durante exposición. Los resultados son preliminares y corresponden a estos textos y fuentes, no a toda formulación posible.
