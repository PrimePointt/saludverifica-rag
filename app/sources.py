"""SQLite persistente e importación acotada de fuentes públicas oficiales."""
import hashlib
import json
import os
import re
import sqlite3
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"www.who.int": "Organización Mundial de la Salud", "www.paho.org": "Organización Panamericana de la Salud", "www.saludchiapas.gob.mx": "Secretaría de Salud de Chiapas", "www.gob.mx": "Gobierno de México"}


def connect():
    directory = Path(os.getenv("DATA_DIR", str(ROOT / "storage")))
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / "sources.db", timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)")
    return db


def seed():
    with connect() as db:
        for doc in json.loads((ROOT / "data/seed.json").read_text(encoding="utf-8")):
            db.execute("INSERT OR IGNORE INTO documents VALUES (?, ?, ?)", (doc["id"], doc["url"], json.dumps(doc, ensure_ascii=False)))
            # A URL may already have been imported by the user. Preserve its text,
            # metadata and identity; add reviewed rules only if their quote exists.
            row = db.execute("SELECT id, payload FROM documents WHERE url = ?", (doc["url"],)).fetchone()
            if row and row[0] != doc["id"]:
                existing = json.loads(row[1])
                facts = list(existing.get("claims", []))
                additions = [fact for fact in doc.get("claims", []) if fact["quote"] in existing["text"] and fact not in facts]
                if additions:
                    existing["claims"] = facts + additions
                    db.execute("UPDATE documents SET payload = ? WHERE id = ?", (json.dumps(existing, ensure_ascii=False), row[0]))


def list_documents():
    seed()
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM documents ORDER BY id")]


def save_document(doc):
    if len(doc.get("text", "").strip()) < 100:
        raise ValueError("Documento demasiado corto para incorporar.")
    # Web imports cannot introduce curated verdict rules.
    if doc.get("origin") != "seed":
        doc = {**doc, "claims": []}
    with connect() as db:
        existing = db.execute("SELECT id FROM documents WHERE url = ?", (doc["url"],)).fetchone()
        if existing:
            return False
        db.execute("INSERT INTO documents VALUES (?, ?, ?)", (doc["id"], doc["url"], json.dumps(doc, ensure_ascii=False)))
    return True


def validate_url(url):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED or parsed.port not in (None, 443) or parsed.username or parsed.password:
        raise ValueError("Usa HTTPS y un dominio admitido: " + ", ".join(ALLOWED))
    return url.split("#")[0]


def download(url):
    url = validate_url(url.strip())
    if urlparse(url).path in {"", "/"}:
        raise ValueError("Este enlace es la portada del portal. Abre una publicación y copia su enlace completo.")
    session = requests.Session()
    session.headers["User-Agent"] = "SaludVerifica-AcademicDemo/1.0"
    for _ in range(4):
        with session.get(url, timeout=(5, 15), allow_redirects=False, stream=True) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                url = validate_url(urljoin(url, response.headers.get("Location", "")))
                continue
            response.raise_for_status()
            if "text/html" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Solo se admiten páginas HTML; no PDF ni archivos binarios.")
            body = bytearray()
            for block in response.iter_content(32768):
                body.extend(block)
                if len(body) > 2_000_000:
                    raise ValueError("Página demasiado grande (máximo 2 MB).")
            return extract_html(bytes(body), url)
    raise ValueError("Demasiadas redirecciones.")


def extract_html(html, url):
    url = validate_url(url)
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    title = heading.get_text(" ", strip=True) if heading else (soup.title.get_text(" ", strip=True) if soup.title else "Publicación oficial")
    published = ""
    for attrs in [{"property": "article:published_time"}, {"name": "date"}, {"name": "DC.date.issued"}]:
        node = soup.find("meta", attrs=attrs)
        if node and node.get("content"):
            published = node["content"][:10]
            break
    time = soup.find("time")
    if not published and time:
        published = time.get("datetime", "")[:10]
    if published and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
        published = ""
    # Prefer article body to avoid navigation text in institutional templates.
    container = soup.select_one(".sf-detail-body-wrapper, [itemprop='articleBody'], .entry-content, article, main, #content") or soup.body
    if container is None:
        raise ValueError("Página sin cuerpo legible.")
    for node in container.select("script, style, nav, footer, header, form, aside, noscript"):
        node.decompose()
    blocks = [re.sub(r"\s+", " ", n.get_text(" ", strip=True)) for n in container.select("p, li, h2, h3")]
    text = "\n\n".join(dict.fromkeys(b for b in blocks if len(b) >= 30))
    if len(text) < 150:
        raise ValueError("No se extrajo suficiente contenido. Prueba otra publicación.")
    if len(text) > 60000:
        raise ValueError("Contenido demasiado extenso; utiliza una publicación más concreta.")
    return {"id": hashlib.sha256(url.encode()).hexdigest()[:16], "url": url,
            "title": title[:300], "institution": ALLOWED[urlparse(url).hostname],
            "published": published, "accessed": date.today().isoformat(),
            "jurisdiction": "No especificada", "text": text, "claims": [], "origin": "web"}


def contingency():
    doc = json.loads((ROOT / "data/demo_source.json").read_text(encoding="utf-8"))
    doc["origin"] = "Copia local de contingencia, no descarga en vivo"
    return doc
