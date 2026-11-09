import html
import os

import requests
import streamlit as st

from app.core import CLINICAL, DOCUMENTAL, DISCLAIMER, analyze, check_connection, export_markdown, key_problem
from app.sources import ALLOWED, contingency, download, list_documents, save_document

st.set_page_config(page_title="SaludVerifica", page_icon="🔎", layout="wide")
st.markdown("""<style>
html,body,[class*="css"] {font-family:Arial,sans-serif;}
.stApp {background:#f5f3ef;color:#333d37;}
[data-testid="stMainBlockContainer"] {max-width:1380px;padding-top:2.2rem;padding-bottom:1rem;}
[data-testid="stSidebar"] {background:#eceee7;border-right:1px solid #dce1d7;}
h1,h2,h3 {font-weight:500!important;letter-spacing:-.025em;}
.masthead {display:flex;align-items:center;gap:18px;border-bottom:1px solid #dcded5;padding:0 0 18px;margin-bottom:24px;}
.wordmark {font-family:Georgia,serif;font-size:2rem;letter-spacing:-1px;color:#394b40;}
.masthead small {color:#6e766e;border-left:1px solid #cdd4c8;padding-left:18px;font-size:.85rem;}
.section-label {color:#6c786d;font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;margin:6px 0 12px;}
.result {padding:16px 20px;border-radius:12px;border-left:4px solid var(--accent);background:#fffdfa;margin:0 0 12px;}
.result h2 {color:var(--accent);font-size:1.35rem;margin:0;}
.result p {color:#656e66;font-size:.85rem;margin:5px 0 0;}
.stButton>button[kind="primary"] {background:#526c59;border:0;border-radius:10px;}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-color:#dfe2d9!important;border-radius:14px!important;}
.source-card {padding:17px;border-radius:12px;background:#fffdfa;border:1px solid #e3e3da;margin:10px 0;}
.source-card h3 {font-size:1rem;margin:8px 0;color:#3c4e42;}
.source-card blockquote {border-left:2px solid #a4b59e;padding:8px 12px;margin:12px 0;background:#f0f3eb;color:#465347;white-space:pre-wrap;font-size:.9rem;}
.source-meta {color:#71776c;font-size:.78rem;}
.tag {display:inline-block;border-radius:6px;padding:3px 8px;background:#e9eee2;color:#4c634c;font-size:.7rem;}
.empty-state {padding:48px 24px;color:#6b786c;text-align:center;min-height:290px;}
.empty-state .shape {font-family:Georgia,serif;font-size:3.2rem;color:#aeb9a5;}
.empty-state h3 {font-family:Georgia,serif;color:#4c5a4c;font-size:1.5rem;}
@media(max-width:760px) {.masthead small{display:none;} .wordmark{font-size:1.65rem;}}
</style>""", unsafe_allow_html=True)

EXAMPLES = {
    "Selecciona un ejemplo…": "",
    "1 · Información en redes": "La información errónea es información falsa que se difunde sin intención de engañar.",
    "2 · Noticia de Chiapa de Corzo": "En Chiapa de Corzo falleció un niño por sarampión en el hospital.",
    "3 · Mensaje sobre vacunas": "La vacuna del sarampión causa magnetismo en el brazo de los niños en Tuxtla.",
    "4 · Consulta clínica": "Tengo fiebre y manchas rojas, ¿qué medicamento puedo tomar en Chiapas?",
    "5 · Fuente nueva": "La vacunación comunitaria es la forma más eficaz de prevenir el sarampión y debería extenderse a todos los niños.",
    "6 · Otra versión de la noticia": "En Chiapa de Corzo el niño del comunicado del 27 de enero de 2026 no falleció por sarampión.",
    "7 · VIH y contacto cotidiano": "El VIH se transmite por compartir alimentos.",
    "8 · Gravedad del dengue": "El dengue siempre es una enfermedad leve.",
    "9 · Vacunación contra el VPH": "La vacuna contra el VPH cura una infección que ya existe.",
    "10 · Animales y rabia": "La rabia solo afecta a los perros.",
}
QUESTIONS = {
    "Selecciona una pregunta…": "",
    "VIH · Vías de transmisión": "¿Cómo se transmite el VIH y qué contactos cotidianos no lo transmiten?",
    "Dengue · Prevención": "¿Cómo se pueden evitar los criaderos de mosquitos que transmiten el dengue?",
    "VPH · Objetivo de la vacuna": "¿La vacuna contra el VPH previene o trata una infección existente?",
    "Rabia · Animales afectados": "¿Qué animales pueden infectarse con el virus de la rabia?",
}


def select_example(widget_key, question_mode):
    # A pending callback from the previous mode can arrive in the same rerun.
    # Ignore it rather than applying a stale selection to the new input.
    active_question_mode = st.session_state.get("search_type") == "Consultar información"
    if active_question_mode != question_mode:
        return
    examples = QUESTIONS if question_mode else EXAMPLES
    selected = st.session_state.get(widget_key)
    if selected not in examples:
        return
    st.session_state["claim_input"] = examples[selected]
    st.session_state.pop("result", None)


def search_changed():
    # Separate stable widget keys avoid deleting state while callbacks run.
    st.session_state["example_verify"] = next(iter(EXAMPLES))
    st.session_state["example_question"] = next(iter(QUESTIONS))
    st.session_state.pop("result", None)
    st.session_state["claim_input"] = ""


def key_changed():
    st.session_state.pop("ai_enabled", None)
    st.session_state.pop("connection_status", None)
    st.session_state.pop("result", None)


documents = list_documents()
with st.sidebar:
    st.markdown("## 🔎 SaludVerifica")
    page = st.radio("Ir a", ["Verificar", "Fuentes"])
    with st.expander("Configuración de IA"):
        session_key = st.text_input("Clave de DeepSeek (opcional)", type="password", key="session_api_key", on_change=key_changed,
                                    placeholder="Pega solo tu API key")
        api_key = session_key.strip() or os.getenv("DEEPSEEK_API_KEY", "").strip()
        ai_available = not key_problem(api_key)
        st.caption("La clave de pantalla se mantiene solo en la sesión; no se guarda en documentos ni Git. Deja vacío para usar .env.")
        if api_key and not ai_available:
            st.warning(key_problem(api_key))
        use_ai = st.toggle("Usar DeepSeek", value=ai_available, disabled=not ai_available, key="ai_enabled")
        if st.button("Comprobar conexión", disabled=not ai_available):
            with st.spinner("Comprobando acceso…"):
                st.session_state["connection_status"] = check_connection(api_key)
        if "connection_status" in st.session_state:
            ok, message = st.session_state["connection_status"]
            (st.success if ok else st.warning)(message)
        st.caption("El análisis con IA envía mensaje y fragmentos a DeepSeek y puede consumir saldo.")
    with st.expander("Acerca del proyecto"):
        st.write("Ayuda a contrastar mensajes sanitarios con publicaciones oficiales antes de compartirlos.")
        st.caption("Proyecto académico · UNACH · Chiapas")
        st.caption("Modo local: búsqueda léxica, fichas revisadas y coincidencia literal. No verifica cualquier paráfrasis. Con DeepSeek se añade contraste generativo; las conclusiones requieren revisión.")
        st.caption("Puede crecer a más regiones, fuentes y revisión colaborativa. No realiza diagnósticos ni busca automáticamente en toda internet.")

st.markdown('<div class="masthead"><span class="wordmark">SaludVerifica<span style="color:#9aab91">.</span></span><small>Una pausa antes de compartir.</small></div>', unsafe_allow_html=True)

if page == "Verificar":
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.markdown('<div class="section-label">01 / Tu consulta</div>', unsafe_allow_html=True)
        search_type = st.radio("¿Qué necesitas hacer?", ["Verificar un mensaje", "Consultar información"], horizontal=True, key="search_type", on_change=search_changed)
        is_question = search_type == "Consultar información"
        st.subheader("Resuelve una duda." if is_question else "Antes de reenviarlo…")
        st.caption("Pregunta sobre salud general. La respuesta se basa en las publicaciones disponibles." if is_question else "Pega el mensaje que recibiste. Buscaremos evidencia para contrastarlo.")
        examples = QUESTIONS if is_question else EXAMPLES
        example_key = "example_question" if is_question else "example_verify"
        if st.session_state.get(example_key) not in examples:
            st.session_state[example_key] = next(iter(examples))
        st.selectbox("Ejemplos de consulta" if is_question else "Ejemplos de mensajes", list(examples), key=example_key,
                     on_change=select_example, args=(example_key, is_question))
        claim = st.text_area("Mensaje", key="claim_input", height=155, label_visibility="collapsed",
                             placeholder="¿Cómo se transmite el VIH?" if is_question else "Ejemplo: El dengue siempre es una enfermedad leve.", max_chars=2500)
        if st.button("Consultar fuentes" if is_question else "Verificar mensaje", type="primary", use_container_width=True):
            try:
                with st.spinner("Leyendo la evidencia…"):
                    st.session_state["result"] = analyze(claim, documents, use_ai, api_key=api_key, mode="question" if is_question else "verify")
            except ValueError as exc:
                st.session_state.pop("result", None)
                st.warning(str(exc))
        st.caption("Con DeepSeek · respuesta generativa con citas" if use_ai else "Sin API · respuestas revisadas y búsqueda documental")
        st.caption("Temas: VIH, dengue, VPH, rabia, desinformación y comunicado local de sarampión. Cobertura acotada.")
    with right:
        st.markdown('<div class="section-label">02 / Lo que dice la evidencia</div>', unsafe_allow_html=True)
        result = st.session_state.get("result")
        with st.container(border=True):
            if not result:
                st.markdown('<div class="empty-state"><div class="shape">↗</div><h3>La respuesta, aquí.</h3><p>Escribe a la izquierda o elige un ejemplo.<br>Verás la explicación y sus fuentes en este espacio.</p></div>', unsafe_allow_html=True)
            else:
                if result["claim"] != claim:
                    st.warning("Editaste la consulta. Vuelve a enviarla para actualizar esta respuesta.")
                colors = {"RESPALDADA": "#526f57", "REFUTADA": "#9b5d55", "EVIDENCIA INSUFICIENTE": "#947747", CLINICAL: "#677c91", "EVIDENCIA CONFLICTIVA": "#81718a", DOCUMENTAL: "#526f57"}
                labels = {"RESPALDADA": "Hay respaldo documental", "REFUTADA": "La evidencia lo contradice",
                          "EVIDENCIA INSUFICIENTE": "Aún no podemos concluir", CLINICAL: "Consulta a un profesional",
                          "EVIDENCIA CONFLICTIVA": "Las fuentes difieren", DOCUMENTAL: "Respuesta a tu consulta"}
                title = "Información parcial" if result.get("partial") else labels[result["category"]]
                st.markdown(f'<div class="result" style="--accent:{colors[result["category"]]}"><h2>{html.escape(title)}</h2></div>', unsafe_allow_html=True)
                response_tab, evidence_tab, details_tab = st.tabs(["Respuesta", "Fuentes", "Método"])
                with response_tab:
                    if result["notice"]:
                        st.warning(result["notice"])
                    explanation = result["explanation"]
                    if result.get("partial") and len(explanation) > 600:
                        explanation = explanation[:600] + "…"
                    st.write(explanation)
                    if result["category"] == "EVIDENCIA INSUFICIENTE":
                        st.caption("No significa que sea falso. Revisa Fuentes o agrega una publicación que cubra el tema.")
                    cited = next((e for e in result["evidence"] if e["citation"] in {q["citation"] for q in result["quotes"]}), None)
                    if cited:
                        doc = cited["document"]
                        st.markdown(f'<div class="source-card"><span class="tag">De dónde sale esta respuesta</span><h3>{html.escape(doc["title"])}</h3><div class="source-meta">{html.escape(doc["institution"])} · {html.escape(doc["published"] or "Fecha no disponible")}</div></div>', unsafe_allow_html=True)
                        st.link_button("Leer publicación original ↗", doc["url"])
                    st.download_button("Guardar ficha", export_markdown(result), file_name="saludverifica-ficha.md", mime="text/markdown")
                with evidence_tab:
                    if not result["evidence"]:
                        st.caption("No se recuperaron fuentes para esta consulta.")
                    else:
                        st.caption("Citada: usada en la explicación. Relacionada: encontrada, pero no prueba el mensaje.")
                        with st.container(height=360, border=False):
                            used = {q["citation"] for q in result["quotes"]}
                            for e in sorted(result["evidence"], key=lambda e: e["citation"] not in used):
                                d = e["document"]
                                quotes = [q["quote"] for q in result["quotes"] if q["citation"] == e["citation"]]
                                excerpt = "\n\n".join(quotes) if quotes else e["text"]
                                badge = "Citada" if quotes else "Relacionada"
                                st.markdown(f'<div class="source-card"><span class="tag">{badge} · {html.escape(e["citation"])}</span><h3>{html.escape(d["title"])}</h3><div class="source-meta">{html.escape(d["institution"])} · {html.escape(d["published"] or "Fecha no disponible")}</div><blockquote>{html.escape(excerpt)}</blockquote></div>', unsafe_allow_html=True)
                                st.link_button(f"Publicación [{e['citation']}] ↗", d["url"])
                with details_tab:
                    st.write(result["method"])
                    st.caption(f"Categoría: {result['category']}")
                    st.caption("Una cita comprobada no garantiza interpretación correcta. La relevancia de búsqueda no es probabilidad de verdad.")
                    for e in result["evidence"]:
                        if e["score"] is not None:
                            st.caption(f"[{e['citation']}] Relevancia léxica: {e['score']:.3f} / 1")
    st.caption(DISCLAIMER)

elif page == "Fuentes":
    st.subheader("¿Con qué información verificamos?")
    st.write("Las fuentes son publicaciones oficiales que el sistema consulta como evidencia. Aquí no se pegan rumores: se agregan los documentos que permiten contrastarlos.")
    with st.expander("Ejemplo práctico: ampliar lo que podemos comprobar"):
        st.write("1. En Verificar, elige «5 · Fuente nueva». Si no guardaste la ficha de sarampión, faltará evidencia.")
        st.write("2. Aquí descarga la publicación de OMS con el enlace de abajo, revisa el texto y guarda la fuente.")
        st.write("3. Vuelve a Verificar y repite el mensaje. Ahora la publicación forma parte de la búsqueda.")
        st.caption("Agregar una fuente no vuelve verdaderos todos los mensajes sobre su tema: el texto debe apoyar o contradecir el hecho concreto.")
    st.subheader("Agregar una publicación oficial")
    st.caption("1. Pega un enlace oficial · 2. Revisa la publicación · 3. Guarda")
    url = st.text_input("URL de publicación oficial", value="https://www.who.int/es/news-room/fact-sheets/detail/measles")
    if st.button("Buscar publicación", type="primary", use_container_width=True):
        st.session_state.pop("preview", None)
        try:
            with st.spinner("Descargando publicación oficial…"):
                st.session_state["preview"] = download(url)
        except ValueError as exc:
            st.error(str(exc))
        except requests.RequestException:
            st.error("No se pudo descargar publicación. Revisa conexión y que el enlace exista; puedes usar copia local.")
    with st.expander("Otras opciones"):
        if st.button("Usar copia local de contingencia", use_container_width=True):
            st.session_state["preview"] = contingency()
        st.caption("Copia guardada para demostración; no es una descarga en vivo.")
        st.caption("Dominios admitidos: " + ", ".join(ALLOWED))
        st.caption("Panel de operador único. Requiere autenticación antes de exponerlo como administración pública.")
    preview = st.session_state.get("preview")
    if preview:
        st.markdown(f"### {preview['title']}")
        st.caption(f"Origen: {preview.get('origin', 'web')} · Publicación: {preview['published'] or 'no disponible'}")
        st.text_area("Texto extraído (revisión previa)", preview["text"], height=250, disabled=True)
        reviewed = st.checkbox("Revisé que el contenido corresponde a la publicación y no es navegación del portal.", key=f"review-{preview['id']}")
        if st.button("Guardar fuente", disabled=not reviewed, type="primary"):
            if save_document(preview):
                st.session_state.pop("result", None)
                st.success("Fuente guardada. Ya puedes usarla en Verificar.")
            else:
                st.info("Esta URL ya está incorporada. No se duplicó ni sobrescribió contenido.")
            documents = list_documents()
    st.divider()
    st.subheader(f"Fuentes guardadas ({len(documents)})")
    st.caption("Estas publicaciones se usan automáticamente al verificar un mensaje. No se busca en todo internet: agrega fuentes si necesitas cubrir otro tema.")
    for d in documents:
        with st.container(border=True):
            st.markdown(f"**{d['title']}**")
            st.caption(f"{d['institution']} · {d['published'] or 'fecha no disponible'} · {d.get('origin', 'Extracto inicial revisado')}")
            st.write(d["text"][:240] + ("…" if len(d["text"]) > 240 else ""))
            st.link_button("Consultar publicación", d["url"])
            with st.expander("Texto guardado completo"):
                st.write(d["text"])
