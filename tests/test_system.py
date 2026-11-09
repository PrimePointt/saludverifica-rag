import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest

from app.core import CLINICAL, DOCUMENTAL, analyze, check_connection, deepseek_verdict, export_markdown, key_problem, retrieve
from app.sources import ROOT, contingency, download, extract_html, list_documents, save_document, validate_url

SEED = json.loads((ROOT / "data/seed.json").read_text(encoding="utf-8"))
BACKED = "La información errónea es información falsa que se difunde sin intención de engañar."
RUMOR = "En Chiapa de Corzo falleció un niño por sarampión en el hospital."
NEW = "La vacunación comunitaria es la forma más eficaz de prevenir el sarampión y debería extenderse a todos los niños."


class VerificationTests(unittest.TestCase):
    def test_information_is_not_treated_as_a_truth_verdict(self):
        result = analyze("¿Cómo se transmite el VIH?", SEED, mode="question")
        self.assertEqual(result["category"], DOCUMENTAL)
        self.assertIn("revisada", result["method"])
        self.assertIn("No se transmite por abrazos", result["explanation"])
        self.assertTrue(any(e["document"]["id"] == "oms-vih" for e in result["evidence"]))
        self.assertIn("**Pregunta:**", export_markdown(result))
        self.assertEqual(analyze("Tengo fiebre, ¿qué tomo?", SEED, mode="question")["category"], CLINICAL)

    def test_informational_ai_requires_verifiable_citations(self):
        query = "¿Cómo se transmite el VIH?"
        evidence = retrieve(query, SEED)
        passage = next(e for e in evidence if e["document"]["id"] == "oms-vih")
        quote = "El VIH se transmite a través de líquidos corporales de la persona infectada, como la sangre, la leche materna, el semen o las secreciones vaginales, y también puede transmitirse al bebé durante el embarazo y el parto."
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": json.dumps({"category": DOCUMENTAL, "explanation": "El VIH se transmite por determinados líquidos corporales.", "quotes": [{"citation": passage["citation"], "quote": quote}]})}}]}
        with patch("app.core.requests.post", return_value=response):
            result = analyze(query, SEED, True, api_key="fake", mode="question")
            self.assertEqual(result["category"], DOCUMENTAL)
            self.assertIn("DeepSeek", result["method"])
            response.json.return_value["choices"][0]["message"]["content"] = json.dumps({"category": DOCUMENTAL, "explanation": "Sin cita", "quotes": []})
            fallback = analyze(query, SEED, True, api_key="fake", mode="question")
            self.assertTrue(fallback["notice"])
            self.assertIn("revisada", fallback["method"])

    def test_reviewed_information_needs_its_actual_source(self):
        faqs = json.loads((ROOT / "data/faq.json").read_text(encoding="utf-8"))
        for faq in faqs:
            with self.subTest(question=faq["questions"][0]):
                result = analyze(faq["questions"][0], SEED, mode="question")
                self.assertEqual(result["explanation"], faq["answer"])
                self.assertEqual(result["quotes"][0]["quote"], faq["quote"])
                self.assertFalse(result.get("partial", False))
                without_source = [d for d in SEED if d["url"] != faq["url"]]
                fallback = analyze(faq["questions"][0], without_source, mode="question")
                self.assertNotEqual(fallback["explanation"], faq["answer"])

    def test_unknown_question_does_not_claim_to_have_complete_answer(self):
        result = analyze("¿Cuáles son los efectos del dengue sobre la memoria?", SEED, mode="question")
        self.assertTrue(result.get("partial") or result["category"] == "EVIDENCIA INSUFICIENTE")

    def test_configuration_reports_mixed_variables(self):
        self.assertIn("Pega solo", key_problem("APP_PORT=8501"))
        self.assertIn("Pega solo", key_problem("DEEPSEEK_API_KEY=sk-test"))

    def test_provider_errors_are_specific_and_do_not_leak_key(self):
        for status, expected in [(401, "rechazó"), (402, "saldo insuficiente"), (429, "limitó")]:
            response = Mock()
            response.status_code = status
            response.raise_for_status.side_effect = requests.HTTPError(response=response)
            with patch("app.core.requests.get", return_value=response):
                ok, message = check_connection("sk-private-test")
                self.assertFalse(ok)
                self.assertIn(expected, message)
                self.assertNotIn("sk-private-test", message)

    def test_session_key_can_override_environment(self):
        evidence = retrieve(BACKED, SEED)
        quote = next(e for e in evidence if BACKED in e["text"])
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": json.dumps({"category": "RESPALDADA", "explanation": "La definición coincide con la OMS.", "quotes": [{"citation": quote["citation"], "quote": BACKED}]})}}]}
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "wrong-env"}), patch("app.core.requests.post", return_value=response) as post:
            result = analyze(BACKED, SEED, True, api_key="sk-session-test")
            self.assertIn("DeepSeek", result["method"])
            self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer sk-session-test")
            self.assertNotIn("sk-session-test", export_markdown(result))

    def test_curated_cases_have_source_quotes(self):
        for doc in SEED:
            for fact in doc.get("claims", []):
                for claim in fact["aliases"]:
                    with self.subTest(claim=claim):
                        result = analyze(claim, SEED)
                        self.assertEqual(result["category"], fact["category"])
                        self.assertIn(result["quotes"][0]["quote"], doc["text"])

    def test_magnetism_not_backed_by_related_words(self):
        result = analyze("La vacuna del sarampión causa magnetismo en el brazo de los niños en Tuxtla.", SEED)
        self.assertEqual(result["category"], "EVIDENCIA INSUFICIENTE")
        self.assertTrue(result["evidence"])

    def test_negation_does_not_trigger_refutation(self):
        result = analyze("En Chiapa de Corzo el niño no falleció por sarampión.", SEED)
        self.assertNotEqual(result["category"], "REFUTADA")

    def test_compound_and_changed_time_do_not_reuse_curated_verdict(self):
        for claim in [RUMOR + " Además la vacuna produce magnetismo.", RUMOR.replace("falleció", "falleció ayer")]:
            self.assertEqual(analyze(claim, SEED)["category"], "EVIDENCIA INSUFICIENTE")

    def test_clinical_accent_and_word_boundaries(self):
        for claim in ["Tengo síntomas de fiebre", "¿Qué medicamento puedo tomar?", "Mi hijo tiene fiebre"]:
            self.assertEqual(analyze(claim, SEED)["category"], CLINICAL)
        self.assertNotEqual(analyze("Los síntomas del sarampión incluyen fiebre", SEED)["category"], CLINICAL)

    def test_invalid_and_empty_corpus(self):
        for value in ["", "   ", "!!!", "x" * 2501]:
            with self.assertRaises(ValueError):
                analyze(value, SEED)
        result = analyze("Información sobre dengue", [])
        self.assertEqual(result["evidence"], [])

    def test_dynamic_source_changes_available_evidence(self):
        self.assertEqual(analyze(NEW, SEED)["category"], "EVIDENCIA INSUFICIENTE")
        result = analyze(NEW, SEED + [contingency()])
        self.assertEqual(result["category"], "RESPALDADA")
        self.assertIn("literal", result["method"])
        self.assertEqual(analyze("No " + NEW, SEED + [contingency()])["category"], "EVIDENCIA INSUFICIENTE")

    def test_missing_or_failed_api_preserves_local(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            result = analyze(BACKED, SEED, True)
            self.assertEqual(result["category"], "RESPALDADA")
            self.assertTrue(result["notice"])
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "fake"}), patch("app.core.requests.post", side_effect=requests.Timeout):
            result = analyze(RUMOR, SEED, True)
            self.assertEqual(result["category"], "REFUTADA")
            self.assertTrue(result["notice"])

    def test_llm_rejects_invented_quote(self):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": json.dumps({"category": "RESPALDADA", "explanation": "Sí", "quotes": [{"citation": "E1", "quote": "Texto inventado que no está en la fuente oficial"}]})}}]}
        with patch("app.core.requests.post", return_value=response):
            with self.assertRaises(ValueError):
                deepseek_verdict(BACKED, retrieve(BACKED, SEED), "fake")

    def test_llm_malformed_json_shape_falls_back(self):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "[]"}}]}
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "fake"}), patch("app.core.requests.post", return_value=response):
            result = analyze(RUMOR, SEED, True)
            self.assertEqual(result["category"], "REFUTADA")
            self.assertTrue(result["notice"])

    def test_export_contains_links_and_disclaimer(self):
        text = export_markdown(analyze(RUMOR, SEED))
        self.assertIn(SEED[0]["url"], text)
        self.assertIn("No sustituye", text)


class SourceTests(unittest.TestCase):
    def test_existing_import_gets_only_quote_backed_rules_without_overwrite(self):
        hiv = next(d for d in SEED if d["id"] == "oms-vih")
        imported = {**hiv, "id": "user-import-hiv", "title": "Mi publicación guardada", "claims": []}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATA_DIR": temp}):
            save_document(imported)
            docs = list_documents()
            preserved = next(d for d in docs if d["id"] == "user-import-hiv")
            self.assertEqual(preserved["title"], "Mi publicación guardada")
            self.assertEqual(preserved["text"], imported["text"])
            self.assertEqual(analyze("El VIH se transmite por compartir alimentos.", docs)["category"], "REFUTADA")
            self.assertEqual(len(docs), len(SEED))

    def test_missing_scheme_and_portal_home_have_useful_feedback(self):
        self.assertEqual(validate_url("www.who.int/es/test"), "https://www.who.int/es/test")
        with self.assertRaisesRegex(ValueError, "portada"):
            download("www.saludchiapas.gob.mx")

    def test_url_rejects_local_and_unofficial_targets(self):
        for url in ["http://www.who.int/x", "https://127.0.0.1/", "https://www.who.int.evil.test/", "https://www.who.int:9000/x", "https://user@www.who.int/x"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_extraction_preserves_article_not_navigation(self):
        content = f"<html><title>Test</title><body><nav>Menú falso</nav><article><h1>Fuente nueva</h1><p>{contingency()['text']}</p></article></body></html>"
        doc = extract_html(content, "https://www.who.int/test")
        self.assertNotIn("Menú falso", doc["text"])
        self.assertEqual(doc["published"], "")
        self.assertEqual(doc["title"], "Fuente nueva")

    def test_redirect_is_validated(self):
        response = Mock(status_code=302, headers={"Location": "http://127.0.0.1/private"})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        with patch("app.sources.requests.Session.get", return_value=response), self.assertRaises(ValueError):
            download("https://www.who.int/test")

    def test_persistence_and_duplicate_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATA_DIR": temp}):
            self.assertEqual(len(list_documents()), len(SEED))
            self.assertTrue(save_document(contingency()))
            modified = {**contingency(), "text": "Texto alterado " * 20}
            self.assertFalse(save_document(modified))
            docs = list_documents()
            self.assertEqual(len(docs), len(SEED) + 1)
            self.assertTrue(any(NEW in d["text"] for d in docs))


class WebTests(unittest.TestCase):
    def test_repeated_mode_changes_with_pending_example_callback(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATA_DIR": temp, "DEEPSEEK_API_KEY": ""}):
            app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
            for _ in range(3):
                # Batch both browser changes to exercise callback ordering.
                app.selectbox[0].select("2 · Noticia de Chiapa de Corzo")
                next(r for r in app.radio if r.label == "¿Qué necesitas hacer?").set_value("Consultar información").run()
                self.assertFalse(app.exception)
                self.assertEqual(app.text_area[0].value, "")
                self.assertEqual(app.selectbox[0].value, "Selecciona una pregunta…")
                app.selectbox[0].select("VIH · Vías de transmisión").run()
                self.assertIn("VIH", app.text_area[0].value)
                next(b for b in app.button if b.label == "Consultar fuentes").click().run()
                self.assertEqual(app.session_state["result"]["category"], DOCUMENTAL)
                next(r for r in app.radio if r.label == "¿Qué necesitas hacer?").set_value("Verificar un mensaje").run()
                self.assertFalse(app.exception)
                self.assertEqual(app.text_area[0].value, "")
                self.assertEqual(app.selectbox[0].value, "Selecciona un ejemplo…")
                self.assertNotIn("result", app.session_state)
            app.selectbox[0].select("2 · Noticia de Chiapa de Corzo").run()
            next(b for b in app.button if b.label == "Verificar mensaje").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["result"]["category"], "REFUTADA")

    def test_question_mode_examples_and_visible_evidence(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATA_DIR": temp, "DEEPSEEK_API_KEY": ""}):
            app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
            next(r for r in app.radio if r.label == "¿Qué necesitas hacer?").set_value("Consultar información").run()
            app.selectbox[0].select("VIH · Vías de transmisión").run()
            next(b for b in app.button if b.label == "Consultar fuentes").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["result"]["category"], DOCUMENTAL)
            self.assertTrue(any('class="source-card"' in m.value for m in app.markdown))
            self.assertFalse(any(e.label == "Ver fuentes consultadas" for e in app.expander))
            next(r for r in app.radio if r.label == "¿Qué necesitas hacer?").set_value("Verificar un mensaje").run()
            self.assertFalse(app.exception)
            self.assertNotIn("result", app.session_state)

    def test_session_key_enables_ai_and_connection_check(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATA_DIR": temp, "DEEPSEEK_API_KEY": ""}):
            app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
            self.assertTrue(app.toggle[0].disabled)
            next(i for i in app.text_input if i.label == "Clave de DeepSeek (opcional)").input("sk-session-test").run()
            self.assertFalse(app.exception)
            self.assertFalse(app.toggle[0].disabled)
            self.assertTrue(app.toggle[0].value)
            response = Mock()
            response.json.return_value = {"data": [{"id": "deepseek-chat"}]}
            with patch("app.core.requests.get", return_value=response):
                next(b for b in app.button if b.label == "Comprobar conexión").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["connection_status"][0])

    def test_web_example_and_source_import(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATA_DIR": temp, "DEEPSEEK_API_KEY": ""}):
            app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
            self.assertFalse(app.exception)
            app.selectbox[0].select("2 · Noticia de Chiapa de Corzo").run()
            next(b for b in app.button if b.label == "Verificar mensaje").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["result"]["category"], "REFUTADA")
            next(r for r in app.radio if r.label == "Ir a").set_value("Fuentes").run()
            next(b for b in app.button if b.label == "Usar copia local de contingencia").click().run()
            app.checkbox[0].check().run()
            next(b for b in app.button if b.label == "Guardar fuente").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(list_documents()), len(SEED) + 1)
            next(r for r in app.radio if r.label == "Ir a").set_value("Verificar").run()
            app.selectbox[0].select("5 · Fuente nueva").run()
            next(b for b in app.button if b.label == "Verificar mensaje").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["result"]["category"], "RESPALDADA")


if __name__ == "__main__":
    unittest.main()
