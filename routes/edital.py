"""
routes/edital.py — cadastro e gerenciamento de editais (toggle do coordenador)
"""
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from crud import edital as crud
from crud import arquivo_edital as crud_arquivo
from crud import programas as crud_programas
from dependencies import pegar_sessao, exigir_coordenador
from models import Usuario
from schemas.edital import EditalCreate, EditalUpdateStatus, EditalResponse, EditalUpdate
from schemas.arquivo_edital import ArquivoEditalResponse

edital_router = APIRouter(tags=["Editais"])

UPLOAD_DIR = "uploads/editais"


def _exigir_dono_programa(db: Session, programa_id: int, usuario_logado: Usuario):
    programa = crud_programas.buscar_programa(db, programa_id)
    if programa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programa não encontrado")
    if programa.coordenador_id != usuario_logado.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não é o coordenador deste programa")
    return programa


# ------------------------------------------------------------------
# POST /programas/{programa_id}/editais
# ------------------------------------------------------------------
@edital_router.post(
    "/programas/{programa_id}/editais",
    response_model=EditalResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_edital(
    programa_id: int,
    dados: EditalCreate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    _exigir_dono_programa(db, programa_id, usuario_logado)
    return crud.criar_edital(db, programa_id, dados)


# ------------------------------------------------------------------
# GET /programas/{programa_id}/editais
# ------------------------------------------------------------------
@edital_router.get(
    "/programas/{programa_id}/editais",
    response_model=list[EditalResponse],
)
def listar_editais(
    programa_id: int,
    db: Session = Depends(pegar_sessao),
):
    return crud.listar_editais_por_programa(db, programa_id)


# ------------------------------------------------------------------
# PATCH /editais/{edital_id}/status
# ------------------------------------------------------------------
@edital_router.patch(
    "/editais/{edital_id}/status",
    response_model=EditalResponse,
)
def atualizar_status_edital(
    edital_id: int,
    dados: EditalUpdateStatus,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    if dados.status not in ("rascunho", "aberto", "encerrado"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Status inválido")

    return crud.atualizar_status(db, edital, dados.status)


# ------------------------------------------------------------------
# POST /editais/{edital_id}/arquivos — anexa arquivo (opcionalmente por etapa)
# ------------------------------------------------------------------
@edital_router.post(
    "/editais/{edital_id}/arquivos",
    response_model=ArquivoEditalResponse,
    status_code=status.HTTP_201_CREATED,
)
def anexar_arquivo(
    edital_id: int,
    titulo: str = Form(...),
    etapa_id: int | None = Form(None),
    alerta_sonoro: bool = Form(False),
    arquivo: UploadFile = File(...),
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")
    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    extensao = os.path.splitext(arquivo.filename or "")[1]
    nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
    caminho = os.path.join(UPLOAD_DIR, nome_arquivo)

    with open(caminho, "wb") as f:
        shutil.copyfileobj(arquivo.file, f)

    arquivo_url = f"/arquivos/editais/{nome_arquivo}"

    return crud_arquivo.criar_arquivo(
        db,
        edital_id=edital_id,
        etapa_id=etapa_id,
        titulo=titulo,
        arquivo_url=arquivo_url,
        alerta_sonoro=alerta_sonoro,
    )


# ------------------------------------------------------------------
# GET /editais/{edital_id}/arquivos — lista arquivos do edital
# ------------------------------------------------------------------
@edital_router.get(
    "/editais/{edital_id}/arquivos",
    response_model=list[ArquivoEditalResponse],
)
def listar_arquivos(
    edital_id: int,
    db: Session = Depends(pegar_sessao),
):
    return crud_arquivo.listar_por_edital(db, edital_id)

@edital_router.patch(
    "/editais/{edital_id}",
    response_model=EditalResponse,
)
def atualizar_edital(
    edital_id: int,
    dados: EditalUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    return crud.atualizar_edital(db, edital, dados)