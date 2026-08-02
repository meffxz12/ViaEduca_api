"""
crud/programas.py — operações de banco para o programa (cadastro do coordenador)
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from models import Programa, LinhaPesquisa, EtapaProcesso
from schemas.programas import ProgramaCreate, ProgramaUpdate


def _com_relacionamentos(query):
    """Evita N+1: carrega linhas_pesquisa e etapas junto com o programa."""
    return query.options(
        joinedload(Programa.linhas_pesquisa),
        joinedload(Programa.etapas_processo),
    )


def coordenador_ja_tem_programa(db: Session, coordenador_id: uuid.UUID) -> bool:
    return (
        db.query(Programa)
        .filter(Programa.coordenador_id == coordenador_id)
        .first()
        is not None
    )


def validar_novo_programa(
    db: Session,
    coordenador_id: uuid.UUID,
    dados: ProgramaCreate,
) -> Optional[str]:
    """
    Um coordenador pode acumular mestrado (MP/MA) e doutorado (D) do MESMO
    PPG (mesmo nome + mesma instituição, nível diferente). Não pode
    cadastrar um segundo programa de nome/instituição diferentes.
    Retorna uma mensagem de erro se a regra for violada, ou None se ok.
    (O nível duplicado — dois programas com o mesmo nível — já é barrado
    pelo unique(instituicao_id, nome, nivel) lá no banco.)
    """
    existentes = (
        db.query(Programa).filter(Programa.coordenador_id == coordenador_id).all()
    )
    if not existentes:
        return None

    primeiro = existentes[0]
    if primeiro.nome != dados.nome or primeiro.instituicao_id != dados.instituicao_id:
        return (
            "Este coordenador já coordena um programa diferente. Só é permitido "
            "acumular mestrado e doutorado do MESMO programa (mesmo nome e instituição)."
        )
    return None


def criar_programa(
    db: Session,
    coordenador_id: uuid.UUID,
    dados: ProgramaCreate,
) -> Programa:
    programa = Programa(
        coordenador_id=coordenador_id,
        instituicao_id=dados.instituicao_id,
        nome=dados.nome,
        id_capes=(dados.id_programa_capes),
        nivel=dados.nivel,
        area_avaliacao_id=dados.area_avaliacao_id,
        area_conhecimento_id=dados.area_conhecimento_id,
        nota_capes=dados.nota_capes,
    )
    db.add(programa)
    db.flush()  # garante programa.id pras linhas/etapas abaixo

    for linha in dados.linhas_pesquisa:
        db.add(LinhaPesquisa(programa_id=programa.id, descricao=linha.descricao))

    for etapa in dados.etapas_processo:
        db.add(
            EtapaProcesso(
                programa_id=programa.id,
                ordem=etapa.ordem,
                descricao=etapa.descricao,
            )
        )

    db.commit()
    db.refresh(programa)
    return programa


def buscar_programa(db: Session, programa_id: int) -> Optional[Programa]:
    return _com_relacionamentos(
        db.query(Programa).filter(Programa.id == programa_id)
    ).first()


def programas_do_coordenador(db: Session, coordenador_id: uuid.UUID) -> list[Programa]:
    """Retorna 1 (só mestrado OU doutorado) ou 2 (mestrado E doutorado do mesmo PPG)."""
    return _com_relacionamentos(
        db.query(Programa).filter(Programa.coordenador_id == coordenador_id)
    ).all()


def listar_programas(
    db: Session,
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    grande_area_id: Optional[int] = None,
) -> list[Programa]:
    query = db.query(Programa).options(
        joinedload(Programa.linhas_pesquisa),
        joinedload(Programa.etapas_processo),
    )
    if nivel is not None:
        query = query.filter(Programa.nivel == nivel)
    if instituicao_id is not None:
        query = query.filter(Programa.instituicao_id == instituicao_id)
    return query.order_by(Programa.nome).all()

def atualizar_programa(
    db: Session,
    programa: Programa,
    dados: ProgramaUpdate,
) -> Programa:
    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(programa, campo, valor)
    db.commit()
    db.refresh(programa)
    return programa