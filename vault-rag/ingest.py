"""Full re-index of the Obsidian vault into ChromaDB. Safe to re-run (idempotent)."""
import os
import re

import chromadb
import ollama
import yaml

VAULT_PATH = os.environ.get(
    "VAULT_PATH",
    "/Users/michaelsmith/Desktop/Vault/MR Smith's Vault/",
)
DB_PATH = os.path.expanduser("~/hermes-agents/vault-rag/chroma_db/")
COLLECTION_NAME = "vault"
EMBED_MODEL = "nomic-embed-text"
MAX_CHUNK_TOKENS = 400

HEADER_RE = re.compile(r"^(#{2,3})\s+(.*)$", re.MULTILINE)


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def parse_frontmatter(content: str):
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 4:].lstrip("\n")
    try:
        frontmatter = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        frontmatter = {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, body


def should_ignore(frontmatter: dict) -> bool:
    value = frontmatter.get("rag-ignore", False)
    return str(value).strip().lower() == "true"


def normalize_tags(frontmatter: dict):
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not isinstance(tags, list):
        tags = []
    return ",".join(str(t) for t in tags)


def split_by_headers(content: str):
    matches = list(HEADER_RE.finditer(content))
    if not matches:
        body = content.strip()
        return [("Untitled", body)] if body else []

    sections = []
    if matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        if preamble:
            sections.append(("Untitled", preamble))

    for i, match in enumerate(matches):
        header = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if body:
            sections.append((header, body))
    return sections


def split_long_section(text: str, max_tokens: int = MAX_CHUNK_TOKENS):
    if estimate_tokens(text) <= max_tokens:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    pieces = []
    current, current_tokens = [], 0
    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if current and current_tokens + para_tokens > max_tokens:
            pieces.append("\n\n".join(current))
            current, current_tokens = [para], para_tokens
        else:
            current.append(para)
            current_tokens += para_tokens
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def build_chunks(filename: str, content: str):
    chunks = []
    for header, body in split_by_headers(content):
        for piece in split_long_section(body):
            text = f"[{filename}] > [{header}]\n\n{piece}"
            chunks.append((header, text))
    return chunks


def embed_text(text: str):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def iter_markdown_files(vault_path: str):
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if d != ".obsidian"]
        for name in files:
            if name.endswith(".md"):
                yield os.path.join(root, name)


def get_collection():
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def is_up_to_date(collection, rel_path: str, mtime: float) -> bool:
    existing = collection.get(where={"source_file": rel_path}, limit=1)
    metadatas = existing.get("metadatas") or []
    return bool(metadatas) and metadatas[0].get("last_modified") == mtime


def ingest_file(collection, vault_path: str, file_path: str):
    rel_path = os.path.relpath(file_path, vault_path)
    mtime = os.path.getmtime(file_path)

    if is_up_to_date(collection, rel_path, mtime):
        print(f"[skip] {rel_path} (unchanged)")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    frontmatter, content = parse_frontmatter(raw)
    if should_ignore(frontmatter):
        print(f"[skip] {rel_path} (rag-ignore)")
        return

    chunks = build_chunks(os.path.basename(file_path), content)
    if not chunks:
        print(f"[skip] {rel_path} (empty)")
        return

    tags = normalize_tags(frontmatter)
    collection.delete(where={"source_file": rel_path})

    ids, embeddings, documents, metadatas = [], [], [], []
    for i, (header, text) in enumerate(chunks):
        ids.append(f"{rel_path}::{i}")
        embeddings.append(embed_text(text))
        documents.append(text)
        metadatas.append(
            {
                "source_file": rel_path,
                "header": header,
                "tags": tags,
                "last_modified": mtime,
            }
        )

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    print(f"[indexed] {rel_path} ({len(chunks)} chunks)")


def remove_stale_files(collection, current_rel_paths: set):
    all_metadatas = collection.get(include=["metadatas"]).get("metadatas") or []
    indexed_paths = {m["source_file"] for m in all_metadatas if "source_file" in m}
    stale = indexed_paths - current_rel_paths
    for rel_path in stale:
        collection.delete(where={"source_file": rel_path})
        print(f"[removed] {rel_path} (deleted from vault)")


def main():
    os.makedirs(DB_PATH, exist_ok=True)
    collection = get_collection()

    rel_paths = set()
    for file_path in iter_markdown_files(VAULT_PATH):
        rel_paths.add(os.path.relpath(file_path, VAULT_PATH))
        ingest_file(collection, VAULT_PATH, file_path)

    remove_stale_files(collection, rel_paths)
    print("Done.")


if __name__ == "__main__":
    main()
