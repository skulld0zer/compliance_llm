import os
import pickle
import re
from pathlib import Path

import faiss
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

URLS = [
    "https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32024R1689",
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689",
    "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
]
CACHE_PATH = Path("data/raw/eu_ai_act.html")
LOCAL_HTML_CANDIDATES = [
    Path("data/raw/OJ_L_202401689_EN_TXT.html"),
    CACHE_PATH,
]

ARTICLE_PATTERN = re.compile(r"^Article\s+(\d+[a-zA-Z]?)\b")
ANNEX_PATTERN = re.compile(r"^Annex\s+([IVXLC]+)\b", re.IGNORECASE)
RECITAL_PATTERN = re.compile(r"^\((\d+)\)")


# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(\w)- (\w)", r"\1\2", text)
    return text.strip()


# =========================
# LEGAL LOCATORS
# =========================
def parse_locator(text, current_locator):
    locator = current_locator.copy()

    article_match = ARTICLE_PATTERN.match(text)
    if article_match:
        article_no = article_match.group(1)
        locator.update({
            "reference": f"Article {article_no}",
            "page": f"Article {article_no}",
            "paragraph_counter": 0,
            "kind": "article",
        })
        return locator, True

    annex_match = ANNEX_PATTERN.match(text)
    if annex_match:
        annex_no = annex_match.group(1).upper()
        locator.update({
            "reference": f"Annex {annex_no}",
            "page": f"Annex {annex_no}",
            "paragraph_counter": 0,
            "kind": "annex",
        })
        return locator, True

    recital_match = RECITAL_PATTERN.match(text)
    if recital_match:
        recital_no = recital_match.group(1)
        locator.update({
            "reference": f"Recital {recital_no}",
            "page": f"Recital {recital_no}",
            "paragraph_counter": 0,
            "kind": "recital",
        })
        return locator, True

    return locator, False


# =========================
# FETCH HTML
# =========================
def fetch_html():
    for local_path in LOCAL_HTML_CANDIDATES:
        if local_path.exists() and local_path.stat().st_size > 1000:
            print(f"Using local HTML source: {local_path}")
            html = local_path.read_text(encoding="utf-8", errors="ignore")
            if html and len(html.strip()) >= 1000:
                if local_path != CACHE_PATH:
                    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                    CACHE_PATH.write_text(html, encoding="utf-8")
                return html

    session = requests.Session()
    # Ignore broken system proxy settings such as 127.0.0.1:9.
    session.trust_env = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    })

    try:
        html = None
        for url in URLS:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            candidate = response.text
            if candidate and len(candidate.strip()) >= 1000:
                html = candidate
                break

        if not html:
            raise RuntimeError("Downloaded HTML response was unexpectedly empty or too short.")

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(html, encoding="utf-8")
        return html
    except requests.RequestException as exc:
        if CACHE_PATH.exists() and CACHE_PATH.stat().st_size > 1000:
            print(f"Network fetch failed ({exc}). Falling back to cached HTML: {CACHE_PATH}")
            return CACHE_PATH.read_text(encoding="utf-8")
        raise RuntimeError(
            "Could not download the EU AI Act HTML and no local cache was found. "
            "Check your internet/proxy settings or place a copy at data/raw/eu_ai_act.html."
        ) from exc
    except RuntimeError as exc:
        if CACHE_PATH.exists() and CACHE_PATH.stat().st_size > 1000:
            print(f"Downloaded content was invalid ({exc}). Falling back to cached HTML: {CACHE_PATH}")
            return CACHE_PATH.read_text(encoding="utf-8")
        raise RuntimeError(
            "The EU AI Act download returned empty or invalid HTML, and no valid local cache was found. "
            "Delete any empty cache file and retry, or place a real HTML copy at data/raw/eu_ai_act.html."
        ) from exc


# =========================
# LOAD HTML CLEANLY
# =========================
def load_html():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")

    paragraphs = soup.find_all("p")
    if not paragraphs:
        paragraphs = soup.select("p, li, td")

    data = []
    current_locator = {
        "reference": "Preamble",
        "page": "Preamble",
        "paragraph_counter": 0,
        "kind": "preamble",
    }

    for p in paragraphs:
        text = clean_text(p.get_text(" ", strip=True))

        if len(text) < 40:
            continue

        current_locator, is_heading = parse_locator(text, current_locator)
        if is_heading:
            continue

        current_locator["paragraph_counter"] += 1
        paragraph_no = current_locator["paragraph_counter"]

        data.append({
            "page": current_locator["page"],
            "reference": current_locator["reference"],
            "paragraph": paragraph_no,
            "locator": f"{current_locator['reference']}, paragraph {paragraph_no}",
            "text": text,
        })

    if not data:
        raise ValueError(
            "The EU AI Act page was fetched, but no usable text blocks were extracted. "
            "The page structure may have changed, the response may be an error page, "
            "or the local cache may contain invalid HTML."
        )

    return data


# =========================
# CHUNKING
# =========================
def chunk_text(text, chunk_size=600):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) < chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence.strip()

    if current:
        chunks.append(current)

    return chunks


# =========================
# MAIN
# =========================
def main():
    print("Loading model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    all_chunks = []
    metadata = []

    print("Loading EU AI Act from HTML...")
    data = load_html()
    print(f"Loaded {len(data)} text blocks")

    for item in data:
        chunks = chunk_text(item["text"])

        for chunk_index, chunk in enumerate(chunks, start=1):
            all_chunks.append(chunk)
            metadata.append({
                "page": item["page"],
                "reference": item["reference"],
                "paragraph": item["paragraph"],
                "locator": item["locator"],
                "chunk": chunk_index,
                "text": chunk,
            })

    if not all_chunks:
        raise ValueError(
            "No chunks were created from the extracted text. "
            "Check the downloaded HTML structure and the chunking input."
        )

    print("Embedding...")
    embeddings = model.encode(all_chunks, show_progress_bar=True)

    index = faiss.IndexFlatL2(len(embeddings[0]))
    index.add(embeddings)

    os.makedirs("data/index", exist_ok=True)

    faiss.write_index(index, "data/index/index.faiss")

    with open("data/index/metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"DONE - {len(all_chunks)} chunks")


if __name__ == "__main__":
    main()
