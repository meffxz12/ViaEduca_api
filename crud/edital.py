import os
from typing import Optional

from sqlalchemy.orm import Session

from models import Edital
from schemas.edital import EditalCreate
from services.notificador import formatar_data, notificar_favoritos


def criar_edital(db: Session, programa_id: int, dados: EditalCreate) -> Edital:
   
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

    notificar_favoritos(db, programa_id, edital.id, f"Novo edital: {edital.titulo}")

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
    # Sem efeito colateral nos outros editais do programa — cada edital
    # muda só o próprio status. Quem abre/encerra inscrições é o PROGRAMA
    # (Programa.programa_aberto), então mudar o status do edital não notifica ninguém.
    edital.status = novo_status
    db.commit()
    db.refresh(edital)
    return edital


def atualizar_edital(db: Session, edital: Edital, dados) -> Edital:
    campos = dados.model_dump(exclude_unset=True)
    antes = {c: getattr(edital, c, None) for c in campos}

    for campo, valor in campos.items():
        setattr(edital, campo, valor)

    # ── avisa quem favoritou, mas SÓ se algo mudou de verdade
    # (o app costuma reenviar todos os campos; sem essa comparação todo "Salvar" notificaria)
    mudou = lambda c: c in campos and antes[c] != getattr(edital, c, None)

    if edital.status != "rascunho":
        ini, fim = edital.data_inicio_inscricao, edital.data_fim_inscricao
        aviso = None

        if mudou("data_inicio_inscricao") or mudou("data_fim_inscricao"):
            if ini and fim:
                aviso = f"Datas de inscrição alteradas: {formatar_data(ini)} a {formatar_data(fim)} — {edital.titulo}"
            elif fim:
                aviso = f"Prazo alterado: inscrições até {formatar_data(fim)} — {edital.titulo}"
            elif ini:
                aviso = f"Início das inscrições alterado para {formatar_data(ini)} — {edital.titulo}"
            else:
                aviso = f"Datas de inscrição removidas — {edital.titulo}"
        elif mudou("titulo") or mudou("descricao") or mudou("url"):
            aviso = f"Edital atualizado: {edital.titulo}"

        if aviso:
            notificar_favoritos(db, edital.programa_id, edital.id, aviso)

    db.commit()
    db.refresh(edital)
    return edital


# ------------------------------------------------------------------
# APAGAR EDITAL
# ------------------------------------------------------------------
def apagar_edital(db: Session, edital: Edital) -> None:
    """Apaga o edital e os arquivos físicos anexados (o banco apaga as linhas
    de arquivos e notificações ligadas a ele via CASCADE)."""
    for arquivo in edital.arquivos:
        nome_arquivo = arquivo.arquivo_url.rsplit("/", 1)[-1]
        caminho = os.path.join("uploads", "editais", nome_arquivo)
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except OSError:
            pass  # não trava a exclusão se o arquivo já não existe / está em uso

    db.delete(edital)
    db.commit()