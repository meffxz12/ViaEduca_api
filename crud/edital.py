"""
crud/edital.py — operações de banco para Edital
"""
from typing import Optional

from sqlalchemy.orm import Session

from models import Edital, ProgramaFavorito, Notificacao, Usuario
from schemas.edital import EditalCreate
from services.firebase_service import enviar_push


def criar_edital(db: Session, programa_id: int, dados: EditalCreate) -> Edital:
    db.query(Edital).filter(
        Edital.programa_id == programa_id,
        Edital.status == "aberto",
    ).update({"status": "encerrado"})

    edital = Edital(
        programa_id=programa_id,
        titulo=dados.titulo,
        descricao=dados.descricao,
        data_inicio_inscricao=dados.data_inicio_inscricao,
        data_fim_inscricao=dados.data_fim_inscricao,
        status="aberto",
    )
    db.add(edital)
    db.flush()  # garante edital.id

    favoritos = (
        db.query(ProgramaFavorito)
        .filter(ProgramaFavorito.programa_id == programa_id)
        .all()
    )

    for fav in favoritos:
        titulo_notif = f"Novo edital: {edital.titulo}"
        db.add(Notificacao(
            estudante_id=fav.estudante_id,
            edital_id=edital.id,
            titulo=titulo_notif,
        ))

        usuario = db.query(Usuario).filter(Usuario.id == fav.estudante_id).first()
        if usuario and usuario.fcm_token:
            enviar_push(usuario.fcm_token, "ViaEduca", titulo_notif)

    db.commit()
    db.refresh(edital)
    return edital


def listar_editais_por_programa(db: Session, programa_id: int) -> list[Edital]:
    return (
        db.query(Edital)
        .filter(Edital.programa_id == programa_id)
        .order_by(Edital.criado_em.desc())
        .all()
    )


def buscar_edital(db: Session, edital_id: int) -> Optional[Edital]:
    return db.query(Edital).filter(Edital.id == edital_id).first()


def buscar_edital_ativo(db: Session, programa_id: int) -> Optional[Edital]:
    return (
        db.query(Edital)
        .filter(Edital.programa_id == programa_id, Edital.status == "aberto")
        .order_by(Edital.criado_em.desc())
        .first()
    )


def atualizar_status(db: Session, edital: Edital, novo_status: str) -> Edital:
    if novo_status == "aberto":
        db.query(Edital).filter(
            Edital.programa_id == edital.programa_id,
            Edital.status == "aberto",
            Edital.id != edital.id,
        ).update({"status": "encerrado"})

    edital.status = novo_status
    db.commit()
    db.refresh(edital)
    return edital