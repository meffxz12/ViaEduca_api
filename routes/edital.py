"""
routes/edital.py — cadastro e gerenciamento de editais (toggle do coordenador)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import edital as crud
from crud import programas as crud_programas
from dependencies import pegar_sessao, exigir_coordenador
from models import Usuario
from schemas.edital import EditalCreate, EditalUpdateStatus, EditalResponse

edital_router = APIRouter(tags=["Editais"])


def _exigir_dono_programa(db: Session, programa_id: int, usuario_logado: Usuario):
    programa = crud_programas.buscar_programa(db, programa_id)
    if programa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programa não encontrado")
    if programa.coordenador_id != usuario_logado.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não é o coordenador deste programa")
    return programa


# ------------------------------------------------------------------
# POST /programas/{programa_id}/editais — cria novo edital (fica "aberto")
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
# GET /programas/{programa_id}/editais — histórico de editais do programa
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
# PATCH /editais/{edital_id}/status — toggle abrir/encerrar
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