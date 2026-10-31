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

    # Pro estudante não existe "arquivo" — é tudo edital. A notificação
    # fala do edital (e do que mudou nele), nunca da palavra "arquivo".
    # Se o título do arquivo for vazio ou igual ao do edital (caso do edital
    # recém-publicado), não repete o nome: "Novo edital: X" em vez de "Edital X: X".
    titulo_arq = (titulo_arquivo or "").strip()
    programa_nome, ies_nome = _programa_e_ies(edital)
    if not titulo_arq or titulo_arq.casefold() == edital.titulo.strip().casefold():
        titulo_notif = f"Novo edital: {edital.titulo}"
        # Push: o Android já mostra "ViaEduca" no cabeçalho, então o título
        # do push não repete o nome do app.
        push_titulo = f"Novo edital · {programa_nome}" if programa_nome else "Novo edital"
        push_corpo = f"{ies_nome} — {edital.titulo}" if ies_nome else edital.titulo
    else:
        titulo_notif = f"Edital {edital.titulo}: {titulo_arq}"
        push_titulo = f"Edital atualizado · {programa_nome}" if programa_nome else "Edital atualizado"
        corpo_base = f"{edital.titulo}: {titulo_arq}"
        push_corpo = f"{ies_nome} — {corpo_base}" if ies_nome else corpo_base
    # Vai junto no push pro app abrir o programa/edital certo ao tocar nele
    push_dados = {
        "tipo": "edital",
        "programa_id": edital.programa_id,
        "edital_id": edital_id,
    }
    tokens_ja_enviados: set[str] = set()   # 1 push por aparelho, mesmo com contas repetidas

    estudantes_ja_notificados: set[int] = set()   # favorito repetido não gera 2 alertas

    for fav in favoritos:
        if fav.estudante_id in estudantes_ja_notificados:
            continue
        estudantes_ja_notificados.add(fav.estudante_id)

        # Se esse mesmo alerta já existe pra esse estudante (ex.: o app mandou
        # o mesmo pedido duas vezes), não cria outro nem manda outro push.
        ja_existe = (
            db.query(Notificacao)
            .filter(
                Notificacao.estudante_id == fav.estudante_id,
                Notificacao.edital_id == edital_id,
                Notificacao.titulo == titulo_notif,
            )
            .first()
        )
        if ja_existe:
            continue

        db.add(Notificacao(
            estudante_id=fav.estudante_id,
            edital_id=edital_id,
            titulo=titulo_notif,
        ))

        if alerta_sonoro:
            usuario = db.query(Usuario).filter(Usuario.id == fav.estudante_id).first()
            token = usuario.fcm_token if usuario else None
            if token and token not in tokens_ja_enviados:
                tokens_ja_enviados.add(token)
                enviar_push(token, push_titulo, push_corpo, push_dados)


def _programa_e_ies(edital):
    """Nome do programa e da IES do edital (None se não achar).
    Usa getattr pra não quebrar o envio caso o nome de algum campo seja outro."""
    programa = getattr(edital, "programa", None)
    programa_nome = getattr(programa, "nome", None)
    # No projeto a IES é a "Instituicao" (nome + sigla); "ies" fica como reserva
    ies = getattr(programa, "instituicao", None) or getattr(programa, "ies", None)
    ies_nome = getattr(ies, "sigla", None) or getattr(ies, "nome", None)
    return programa_nome, ies_nome


def listar_por_edital(db: Session, edital_id: int):
    return (
        db.query(ArquivoEdital)
        .filter(ArquivoEdital.edital_id == edital_id)
        .order_by(ArquivoEdital.publicado_em.desc())
        .all()
    )