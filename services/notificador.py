"""
services/notificador.py — cria notificações para quem favoritou um programa.

Usado por: criar/editar/encerrar edital, anexar arquivo e os lembretes de prazo.
Regras:
  - a notificação do app (tabela notificacoes) é criada pra TODOS que favoritaram
  - push só se push=True, e no máximo 1 por aparelho (várias contas no mesmo celular)
  - o título é cortado em 200 caracteres (limite da coluna; antes um edital com
    título longo estourava erro 500 ao notificar)
  - evitar_duplicada=True: não repete a mesma notificação (usado pelos lembretes,
    que rodam todo dia)
"""
from sqlalchemy.orm import Session

from models import Notificacao, ProgramaFavorito, Usuario
from services.firebase_service import enviar_push

LIMITE_TITULO = 200


def cortar(texto: str, limite: int = LIMITE_TITULO) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def formatar_data(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def notificar_favoritos(
    db: Session,
    programa_id: int,
    edital_id: int | None,
    titulo: str,
    push: bool = True,
    evitar_duplicada: bool = False,
) -> int:
    """Adiciona as notificações na sessão (quem chama faz o commit). Devolve quantos estudantes foram avisados.

    edital_id=None: avisa só por push, sem criar notificação no app (a tabela
    notificacoes exige um edital — usado quando o programa ainda não tem nenhum)."""
    titulo = cortar(titulo)

    ids = [
        r[0]
        for r in db.query(ProgramaFavorito.estudante_id)
        .filter(ProgramaFavorito.programa_id == programa_id)
        .all()
    ]
    if not ids:
        return 0

    if evitar_duplicada and edital_id is not None:
        ja_avisados = {
            r[0]
            for r in db.query(Notificacao.estudante_id)
            .filter(
                Notificacao.edital_id == edital_id,
                Notificacao.titulo == titulo,
                Notificacao.estudante_id.in_(ids),
            )
            .all()
        }
        ids = [i for i in ids if i not in ja_avisados]
        if not ids:
            return 0

    if edital_id is not None:
        for estudante_id in ids:
            db.add(Notificacao(estudante_id=estudante_id, edital_id=edital_id, titulo=titulo))

    if push:
        tokens = {
            r[0]
            for r in db.query(Usuario.fcm_token)
            .filter(Usuario.id.in_(ids), Usuario.fcm_token.isnot(None))
            .all()
            if r[0]
        }
        for token in tokens:
            enviar_push(token, "ViaEduca", titulo)

    return len(ids)