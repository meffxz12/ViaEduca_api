
import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

log = logging.getLogger("storage")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = os.getenv("SUPABASE_BUCKET", "editais")
PASTA_LOCAL = "uploads/editais"

_TIPOS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def supabase_ativo() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def url_publica(nome: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{nome}"


def tipo_do_arquivo(nome: str) -> str:
    return _TIPOS.get(os.path.splitext(nome)[1].lower(), "application/octet-stream")


def enviar_supabase(nome: str, conteudo: bytes, upsert: bool = False) -> httpx.Response:
    return httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{nome}",
        content=conteudo,
        headers={
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
            "Content-Type": tipo_do_arquivo(nome),
            "x-upsert": "true" if upsert else "false",
        },
        timeout=60,
    )


def salvar_arquivo(nome: str, conteudo: bytes) -> None:
    """Salva o arquivo; levanta HTTPException 502 se o armazenamento falhar."""
    if supabase_ativo():
        try:
            resp = enviar_supabase(nome, conteudo)
        except httpx.HTTPError as e:
            log.error("Falha de rede no Supabase Storage: %s", e)
            raise HTTPException(502, "Não foi possível salvar o arquivo. Tente novamente.")
        if resp.status_code not in (200, 201):
            log.error("Supabase Storage recusou (%s): %s", resp.status_code, resp.text[:300])
            raise HTTPException(502, "Não foi possível salvar o arquivo. Tente novamente.")
        return

    os.makedirs(PASTA_LOCAL, exist_ok=True)
    with open(os.path.join(PASTA_LOCAL, nome), "wb") as f:
        f.write(conteudo)
