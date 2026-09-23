"""
crud/areas.py — consultas de leitura para os dropdowns de área

Todas as tabelas aqui são alimentadas por seed (grandes_areas) ou pela
sincronização diária com a API Sucupira (areas_avaliacao / areas_conhecimento),
então este módulo só tem operações de leitura.
"""
from typing import Optional
from sqlalchemy.orm import Session
from models import GrandeAreas, AreaAvaliacao, AreaConhecimento

# ---------------------------------------------------------------------------
# GrandesAreas
# ---------------------------------------------------------------------------
def listar_grandes_areas(db: Session) -> list[GrandeAreas]:
    return db.query(GrandeAreas).order_by(GrandeAreas.nome).all()


def buscar_grande_area(db: Session, grande_area_id: int) -> Optional[GrandeAreas]:
    return db.query(GrandeAreas).filter(GrandeAreas.id == grande_area_id).first()


# ---------------------------------------------------------------------------
# AreasAvaliacao
# ---------------------------------------------------------------------------
def listar_areas_avaliacao(db: Session, grande_area_id: Optional[int] = None):
    query = db.query(AreaAvaliacao)
    if grande_area_id is not None:
        query = query.filter(AreaAvaliacao.grande_area_id == grande_area_id)
    return query.order_by(AreaAvaliacao.nome).all()


def buscar_area_avaliacao(db: Session, area_avaliacao_id: int) -> Optional[AreaAvaliacao]:
    return db.query(AreaAvaliacao).filter(AreaAvaliacao.id == area_avaliacao_id).first()


# ---------------------------------------------------------------------------
# AreasConhecimento
# ---------------------------------------------------------------------------
def listar_areas_conhecimento(
    db: Session,
    area_avaliacao_id: Optional[int] = None,
    grande_area_id: Optional[int] = None,
):
    query = db.query(AreaConhecimento)
    if area_avaliacao_id is not None:
        query = query.filter(AreaConhecimento.area_avaliacao_id == area_avaliacao_id)
    if grande_area_id is not None:
        query = query.join(
            AreaAvaliacao, AreaConhecimento.area_avaliacao_id == AreaAvaliacao.id
        ).filter(AreaAvaliacao.grande_area_id == grande_area_id)
    return query.order_by(AreaConhecimento.nome).all()


def buscar_area_conhecimento(db: Session, area_conhecimento_id: int) -> Optional[AreaConhecimento]:
    return (
        db.query(AreaConhecimento)
        .filter(AreaConhecimento.id == area_conhecimento_id)
        .first()
    )