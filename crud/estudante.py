import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from models import ProgramaFavorito, Notificacao, Edital, Usuario, Estudante, Programa
from services.notificador import cortar
from services.firebase_service import enviar_push

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

    favorito = ProgramaFavorito(estudante_id=estudante_id, programa_id=programa_id)
    db.add(favorito)

    programa = db.query(Programa).filter(Programa.id == programa_id).first()

    # Só avisa "inscrições abertas" se o PROGRAMA está aberto; usa o edital mais recente.
    # (edital não abre nem fecha: quem abre é o programa)
    edital_recente = None
    if programa is not None and programa.programa_aberto:
        edital_recente = (
            db.query(Edital)
            .filter(Edital.programa_id == programa_id, Edital.status != "rascunho")
            .order_by(Edital.criado_em.desc())
            .first()
        )

    if edital_recente is not None:
        titulo_notif = cortar(f"Inscrições abertas: {edital_recente.titulo}")
        db.add(Notificacao(
            estudante_id=estudante_id,
            edital_id=edital_recente.id,
            titulo=titulo_notif,
        ))

        usuario = db.query(Usuario).filter(Usuario.id == estudante_id).first()
        if usuario and usuario.fcm_token:
            enviar_push(usuario.fcm_token, "ViaEduca", titulo_notif)

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