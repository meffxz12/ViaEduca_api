from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import solicitacao_vinculo as crud
from dependencies import pegar_sessao, exigir_admin
from models import Usuario
from schemas.solicitacao_vinculo import SolicitacaoVinculoResponse, SolicitacaoVinculoRejeitar

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/solicitacoes", response_model=list[SolicitacaoVinculoResponse])
def listar_solicitacoes(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_admin),
):
    return crud.listar_pendentes(db)


@admin_router.post("/solicitacoes/{solicitacao_id}/aprovar", response_model=SolicitacaoVinculoResponse)
def aprovar_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_admin),
):
    solicitacao = crud.buscar(db, solicitacao_id)
    if solicitacao is None or solicitacao.status != "pendente":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada ou já decidida")
    return crud.aprovar(db, solicitacao, usuario_logado.id)


@admin_router.post("/solicitacoes/{solicitacao_id}/rejeitar", response_model=SolicitacaoVinculoResponse)
def rejeitar_solicitacao(
    solicitacao_id: int,
    dados: SolicitacaoVinculoRejeitar,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_admin),
):
    solicitacao = crud.buscar(db, solicitacao_id)
    if solicitacao is None or solicitacao.status != "pendente":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada ou já decidida")
    return crud.rejeitar(db, solicitacao, usuario_logado.id, dados.motivo)