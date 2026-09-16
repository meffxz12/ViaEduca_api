from datetime import datetime
from sqlalchemy.orm import Session

from models import SolicitacaoVinculo, Programa, LinhaPesquisa, EtapaProcesso


def criar(db: Session, programa_id: int, coordenador_id, linhas_pesquisa=None, etapas_processo=None):
    solicitacao = SolicitacaoVinculo(
        programa_id=programa_id,
        coordenador_id=coordenador_id,
        status="pendente",
        linhas_pesquisa_rascunho=[l.model_dump() for l in (linhas_pesquisa or [])],
        etapas_processo_rascunho=[e.model_dump() for e in (etapas_processo or [])],
    )
    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)
    return solicitacao


def ja_tem_pendente(db: Session, coordenador_id) -> bool:
    return db.query(SolicitacaoVinculo).filter(
        SolicitacaoVinculo.coordenador_id == coordenador_id,
        SolicitacaoVinculo.status == "pendente",
    ).first() is not None


def listar_pendentes(db: Session):
    return db.query(SolicitacaoVinculo).filter(
        SolicitacaoVinculo.status == "pendente"
    ).order_by(SolicitacaoVinculo.criado_em).all()


def buscar(db: Session, solicitacao_id: int):
    return db.query(SolicitacaoVinculo).filter(
        SolicitacaoVinculo.id == solicitacao_id
    ).first()


def aprovar(db: Session, solicitacao: SolicitacaoVinculo, admin_id):
    programa = db.query(Programa).filter(Programa.id == solicitacao.programa_id).first()
    programa.coordenador_id = solicitacao.coordenador_id

    # transforma os rascunhos em dados reais do programa
    for item in (solicitacao.linhas_pesquisa_rascunho or []):
        db.add(LinhaPesquisa(programa_id=programa.id, descricao=item["descricao"]))

    for item in (solicitacao.etapas_processo_rascunho or []):
        db.add(EtapaProcesso(
            programa_id=programa.id,
            ordem=item["ordem"],
            descricao=item["descricao"],
        ))

    solicitacao.status = "aprovado"
    solicitacao.decidido_em = datetime.now()
    solicitacao.decidido_por = admin_id

    db.commit()
    db.refresh(solicitacao)
    return solicitacao


def rejeitar(db: Session, solicitacao: SolicitacaoVinculo, admin_id, motivo: str | None):
    solicitacao.status = "rejeitado"
    solicitacao.decidido_em = datetime.now()
    solicitacao.decidido_por = admin_id
    solicitacao.motivo_rejeicao = motivo

    db.commit()
    db.refresh(solicitacao)
    return solicitacao