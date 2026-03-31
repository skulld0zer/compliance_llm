import os
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import re

URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689"


# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\w)- (\w)', r'\1\2', text)  # FIX broken words
    return text.strip()


# =========================
# EXTRACT REFERENCES
# =========================
def extract_reference(text):
    refs = []

    art = re.search(r'Article\s+\d+', text)
    if art:
        refs.append(art.group())

    annex = re.search(r'Annex\s+[IVX]+', text)
    if annex:
        refs.append(annex.group())

    recital = re.search(r'\((\d+)\)', text)
    if recital:
        refs.append(f"Recital {recital.group(1)}")

    return ", ".join(refs) if refs else "General Provision"


# =========================
# LOAD HTML CLEANLY
# =========================
def load_html():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    paragraphs = soup.find_all("p")

    data = []
    current_ref = "General"

    for i, p in enumerate(paragraphs):
        text = p.get_text()
        text = clean_text(text)

        if len(text) < 50:
            continue

        # detect headers like "Article X"
        if re.match(r"Article\s+\d+", text):
            current_ref = text

        data.append({
            "page": current_ref,
            "text": text
        })

    return data


# =========================
# CHUNKING (SAFE)
# =========================
def chunk_text(text, chunk_size=600, overlap=100):
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current = ""

    for s in sentences:
        if len(current) + len(s) < chunk_size:
            current += " " + s
        else:
            chunks.append(current.strip())
            current = s

    if current:
        chunks.append(current.strip())

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

    for item in data:
        chunks = chunk_text(item["text"])

        for chunk in chunks:
            ref = extract_reference(chunk)

            all_chunks.append(chunk)
            metadata.append({
                "page": item["page"],
                "reference": ref,
                "text": chunk
            })

    print("Embedding...")
    embeddings = model.encode(all_chunks, show_progress_bar=True)

    index = faiss.IndexFlatL2(len(embeddings[0]))
    index.add(embeddings)

    os.makedirs("data/index", exist_ok=True)

    faiss.write_index(index, "data/index/index.faiss")

    with open("data/index/metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ DONE – {len(all_chunks)} chunks")


if __name__ == "__main__":
    main()