"""
crud/instituicoes.py — leitura de instituições

Sem cadastro por essa API por enquanto (assumindo que instituições são
inseridas via seed/admin, igual grandes_areas). Se você quiser permitir
o coordenador cadastrar uma instituição nova direto pelo app, me avisa
que eu adiciono o POST.
"""
from typing import Optional

from sqlalchemy.orm import Session

from models import Instituicao, ProgramaCapes

def listar_instituicoes(
    db: Session,
    busca: Optional[str] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
):
    query = db.query(Instituicao)

    if area_avaliacao_id or area_conhecimento_id:
        query = query.join(
            ProgramaCapes,
            ProgramaCapes.instituicao_id == Instituicao.id,
        )

        if area_avaliacao_id:
            query = query.filter(
                ProgramaCapes.area_avaliacao_id == area_avaliacao_id
            )

        if area_conhecimento_id:
            query = query.filter(
                ProgramaCapes.area_conhecimento_id == area_conhecimento_id
            )

        query = query.distinct()

    if busca:
        query = query.filter(
            (Instituicao.nome.ilike(f"%{busca}%")) |
            (Instituicao.sigla.ilike(f"%{busca}%"))
        )

    return query.order_by(Instituicao.nome).all()

def buscar_instituicao(db: Session, instituicao_id: int) -> Optional[Instituicao]:
    return db.query(Instituicao).filter(Instituicao.id == instituicao_id).first()

def remover_duplicados(dados):
    vistos = set()
    resultado = []

    for item in dados:
        if item.id_capes not in vistos:
            vistos.add(item.id_capes)
            resultado.append(item)

    return resultado