
import os
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from services import storage

arquivos_router = APIRouter(tags=["Arquivos"])

_NOME_OK = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9]+$")


@arquivos_router.get("/arquivos/editais/{nome}")
def baixar_arquivo(nome: str):
    if not _NOME_OK.match(nome):
        raise HTTPException(404, "Arquivo não encontrado")

    local = os.path.join(storage.PASTA_LOCAL, nome)
    if os.path.isfile(local):
        return FileResponse(local)

    if storage.supabase_ativo():
        return RedirectResponse(storage.url_publica(nome), status_code=307)

    raise HTTPException(404, "Arquivo não encontrado")
