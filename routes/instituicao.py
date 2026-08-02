"""
routes/instituicoes.py — dropdown de instituição (cadastro coordenador/programa)
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crud import instituicao as crud
from dependencies import pegar_sessao
from schemas.instituicao import InstituicaoResponse

instituicao_router = APIRouter(prefix="/instituicao", tags=["Instituições"])
    
@instituicao_router.get("", response_model=list[InstituicaoResponse])
def get_instituicao(
    busca: Optional[str] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
    db: Session = Depends(pegar_sessao),
):
    return crud.listar_instituicoes(
        db,
        busca=busca,
        area_avaliacao_id=area_avaliacao_id,
        area_conhecimento_id=area_conhecimento_id,
    )