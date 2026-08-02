"""
crud/etapa_processo.py — gerenciar etapas do processo seletivo de um
programa depois do cadastro inicial (que é feito em lote via ProgramaCreate)
"""
from typing import Optional

from sqlalchemy.orm import Session

from models import EtapaProcesso
from schemas.programas import EtapaProcessoCreate, EtapaProcessoUpdate


def ordem_em_uso(
    db: Session,
    programa_id: int,
    ordem: int,
    ignorar_etapa_id: Optional[int] = None,
) -> bool:
    query = db.query(EtapaProcesso).filter(
        EtapaProcesso.programa_id == programa_id,
        EtapaProcesso.ordem == ordem,
    )
    if ignorar_etapa_id is not None:
        query = query.filter(EtapaProcesso.id != ignorar_etapa_id)
    return query.first() is not None


def adicionar(db: Session, programa_id: int, dados: EtapaProcessoCreate) -> EtapaProcesso:
    etapa = EtapaProcesso(
        programa_id=programa_id,
        ordem=dados.ordem,
        descricao=dados.descricao,
    )
    db.add(etapa)
    db.commit()
    db.refresh(etapa)
    return etapa


def buscar(db: Session, etapa_id: int) -> Optional[EtapaProcesso]:
    return db.query(EtapaProcesso).filter(EtapaProcesso.id == etapa_id).first()


def atualizar(db: Session, etapa: EtapaProcesso, dados: EtapaProcessoUpdate) -> EtapaProcesso:
    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(etapa, campo, valor)
    db.commit()
    db.refresh(etapa)
    return etapa


def remover(db: Session, etapa: EtapaProcesso) -> None:
    db.delete(etapa)
    db.commit()


def listar_do_programa(db: Session, programa_id: int) -> list[EtapaProcesso]:
    return (
        db.query(EtapaProcesso)
        .filter(EtapaProcesso.programa_id == programa_id)
        .order_by(EtapaProcesso.ordem)
        .all()
    )