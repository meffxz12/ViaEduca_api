"""
crud/arquivo_edital.py — upload de arquivo por etapa + notificação automática
"""
from sqlalchemy.orm import Session

from models import ArquivoEdital, Edital, ProgramaFavorito, Notificacao, Usuario
from services.firebase_service import enviar_push


def criar_arquivo(
    db: Session,
    edital_id: int,
    etapa_id: int | None,
    titulo: str,
    arquivo_url: str,
    alerta_sonoro: bool,
) -> ArquivoEdital:
    arquivo = ArquivoEdital(
        edital_id=edital_id,
        etapa_id=etapa_id,
        titulo=titulo,
        arquivo_url=arquivo_url,
        alerta_sonoro=alerta_sonoro,
    )
    db.add(arquivo)
    db.flush()

    _notificar_favoritos(db, edital_id, titulo, alerta_sonoro)

    db.commit()
    db.refresh(arquivo)
    return arquivo


def _notificar_favoritos(
    db: Session, edital_id: int, titulo_arquivo: str, alerta_sonoro: bool
):
    """Cria a notificação in-app pra TODOS que favoritaram o programa.
    Só envia push (que já dispara som padrão do celular) se alerta_sonoro=True —
    é isso que o coordenador escolhe por arquivo."""
    edital = db.query(Edital).filter(Edital.id == edital_id).first()
    if edital is None:
        return

    favoritos = (
        db.query(ProgramaFavorito)
        .filter(ProgramaFavorito.programa_id == edital.programa_id)
        .all()
    )

    titulo_notif = f"Novo arquivo: {titulo_arquivo}"

    for fav in favoritos:
        db.add(Notificacao(
            estudante_id=fav.estudante_id,
            edital_id=edital_id,
            titulo=titulo_notif,
        ))

        if alerta_sonoro:
            usuario = db.query(Usuario).filter(Usuario.id == fav.estudante_id).first()
            if usuario and usuario.fcm_token:
                enviar_push(usuario.fcm_token, "ViaEduca", titulo_notif)


def listar_por_edital(db: Session, edital_id: int):
    return (
        db.query(ArquivoEdital)
        .filter(ArquivoEdital.edital_id == edital_id)
        .order_by(ArquivoEdital.publicado_em.desc())
        .all()
    )