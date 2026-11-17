import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from models import ProgramaFavorito, Notificacao, Edital, Estudante

# ---------------------------------------------------------------------------
# Favoritos
# ---------------------------------------------------------------------------
def ja_favoritou(db: Session, estudante_id: uuid.UUID, programa_id: int) -> bool:
    return (
        db.query(ProgramaFavorito)
        .filter(
            ProgramaFavorito.estudante_id == estudante_id,
            ProgramaFavorito.programa_id == programa_id,
        )
        .first()
        is not None
    )


def favoritar_programa(
    db: Session, estudante_id: uuid.UUID, programa_id: int
) -> ProgramaFavorito:
    existente = (
        db.query(ProgramaFavorito)
        .filter(
            ProgramaFavorito.estudante_id == estudante_id,
            ProgramaFavorito.programa_id == programa_id,
        )
        .first()
    )
    if existente is not None:
        return existente

    # Favoritar NÃO gera notificação: quem favorita já está vendo o programa
    # e os editais na tela. O aviso só chega pro que acontecer DEPOIS
    # (novo edital, prazo alterado, programa abriu/fechou, lembretes).
    favorito = ProgramaFavorito(estudante_id=estudante_id, programa_id=programa_id)
    db.add(favorito)
    db.commit()
    db.refresh(favorito)
    return favorito


def desfavoritar_programa(db: Session, estudante_id: uuid.UUID, programa_id: int) -> bool:
    favorito = (
        db.query(ProgramaFavorito)
        .filter(
            ProgramaFavorito.estudante_id == estudante_id,
            ProgramaFavorito.programa_id == programa_id,
        )
        .first()
    )
    if favorito is None:
        return False
    db.delete(favorito)
    db.commit()
    return True


def listar_favoritos(db: Session, estudante_id: uuid.UUID) -> list[ProgramaFavorito]:
    return (
        db.query(ProgramaFavorito)
        .options(joinedload(ProgramaFavorito.programa))
        .filter(ProgramaFavorito.estudante_id == estudante_id)
        .order_by(ProgramaFavorito.favoritado_em.desc())
        .all()
    )


def ids_programas_favoritados(db: Session, estudante_id: uuid.UUID) -> set[int]:
    """Usado na busca, pra marcar `favoritado=True` em cada item retornado."""
    linhas = (
        db.query(ProgramaFavorito.programa_id)
        .filter(ProgramaFavorito.estudante_id == estudante_id)
        .all()
    )
    return {programa_id for (programa_id,) in linhas}


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------
def _com_relacionamentos(query):
    return query.options(
        joinedload(Notificacao.edital).joinedload(Edital.programa)
    )


def listar_notificacoes(
    db: Session,
    estudante_id: uuid.UUID,
    apenas_nao_lidas: bool = False,
) -> list[Notificacao]:
    query = _com_relacionamentos(
        db.query(Notificacao).filter(Notificacao.estudante_id == estudante_id)
    )
    if apenas_nao_lidas:
        query = query.filter(Notificacao.lida.is_(False))
    return query.order_by(Notificacao.criado_em.desc()).all()


def buscar_notificacao(db: Session, notificacao_id: int) -> Optional[Notificacao]:
    return _com_relacionamentos(
        db.query(Notificacao).filter(Notificacao.id == notificacao_id)
    ).first()


def contar_nao_lidas(db: Session, estudante_id: uuid.UUID) -> int:
    return (
        db.query(Notificacao)
        .filter(Notificacao.estudante_id == estudante_id, Notificacao.lida.is_(False))
        .count()
    )


def marcar_notificacao_lida(db: Session, notificacao: Notificacao) -> Notificacao:
    notificacao.lida = True
    db.commit()
    db.refresh(notificacao)
    return notificacao


def marcar_todas_lidas(db: Session, estudante_id: uuid.UUID) -> int:
    atualizadas = (
        db.query(Notificacao)
        .filter(Notificacao.estudante_id == estudante_id, Notificacao.lida.is_(False))
        .update({"lida": True})
    )
    db.commit()
    return atualizadas

# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------
def buscar_estudante(db: Session, usuario_id: uuid.UUID) -> Optional[Estudante]:
    return db.query(Estudante).filter(Estudante.usuario_id == usuario_id).first()