
from sqlalchemy.orm import Session

from models import Notificacao, ProgramaFavorito, Usuario
from services.firebase_service import enviar_push

LIMITE_TITULO = 200

# Usado quando a mensagem não tem como ser dividida em título + corpo.
# (Não pode ser só "ViaEduca": o Android já mostra o nome do app no cabeçalho.)
TITULO_PUSH_PADRAO = "Novidade em um programa favorito"


def cortar(texto: str, limite: int = LIMITE_TITULO) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def formatar_data(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def separar_titulo_corpo(texto: str) -> tuple[str, str]:
    """Divide a mensagem em (título, corpo) pro push.

    'Novo edital: Edital 2026/1'              -> ('Novo edital', 'Edital 2026/1')
    'Prazo alterado: até 05/03 — Edital X'    -> ('Prazo alterado', 'até 05/03 — Edital X')
    'Datas de inscrição removidas — Edital X' -> ('Datas de inscrição removidas', 'Edital X')
    Sem separador: título padrão e a mensagem inteira no corpo.
    """
    for separador in (": ", " — "):
        if separador in texto:
            titulo, corpo = texto.split(separador, 1)
            if titulo.strip() and corpo.strip():
                return titulo.strip(), corpo.strip()
    return TITULO_PUSH_PADRAO, texto


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
        titulo_push, corpo_push = separar_titulo_corpo(titulo)
        dados = {"programa_id": programa_id}
        if edital_id is not None:
            dados["edital_id"] = edital_id
        for token in tokens:
            enviar_push(token, titulo_push, corpo_push, dados)

    return len(ids)