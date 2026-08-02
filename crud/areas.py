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
def listar_areas_avaliacao(db: Session) -> list[AreaAvaliacao]:
    return db.query(AreaAvaliacao).order_by(AreaAvaliacao.nome).all()


def buscar_area_avaliacao(db: Session, area_avaliacao_id: int) -> Optional[AreaAvaliacao]:
    return db.query(AreaAvaliacao).filter(AreaAvaliacao.id == area_avaliacao_id).first()


# ---------------------------------------------------------------------------
# AreasConhecimento
# ---------------------------------------------------------------------------
def listar_areas_conhecimento(
    db: Session,
    area_avaliacao_id: Optional[int] = None,
) -> list[AreaConhecimento]:
    """
    Lista as áreas de conhecimento. Se `area_avaliacao_id` for informado,
    filtra só as sub-áreas daquela área de avaliação — é o caso de uso
    principal no Flutter: coordenador escolhe a área de avaliação e o
    segundo dropdown (conhecimento) é recarregado filtrado por ela.
    """
    query = db.query(AreaConhecimento)
    if area_avaliacao_id is not None:
        query = query.filter(AreaConhecimento.area_avaliacao_id == area_avaliacao_id)
    return query.order_by(AreaConhecimento.nome).all()


def buscar_area_conhecimento(db: Session, area_conhecimento_id: int) -> Optional[AreaConhecimento]:
    return (
        db.query(AreaConhecimento)
        .filter(AreaConhecimento.id == area_conhecimento_id)
        .first()
    )