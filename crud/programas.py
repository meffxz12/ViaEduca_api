"""
crud/programas.py — operações de banco para o programa (cadastro do coordenador)
"""
import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from models import Programa, LinhaPesquisa, EtapaProcesso, AreaAvaliacao, Edital
from schemas.programas import ProgramaCreate, ProgramaUpdate


def _ids_programas_com_edital_aberto(db: Session, programa_ids: list[int]) -> set[int]:
    """Descobre, numa única query, quais desses programas têm pelo menos
    um edital com status 'aberto' e prazo ainda não vencido."""
    if not programa_ids:
        return set()

    hoje = date.today()  # objeto date puro, já que a coluna é Date de verdade

    linhas = (
        db.query(Edital.programa_id)
        .filter(
            Edital.programa_id.in_(programa_ids),
            Edital.status == "aberto",
            (Edital.data_fim_inscricao.is_(None)) | (Edital.data_fim_inscricao >= hoje),
        )
        .distinct()
        .all()
    )
    return {linha[0] for linha in linhas}


def _sincronizar_programa_aberto(db: Session, programas: list[Programa]) -> list[Programa]:
    """Sobrescreve programa_aberto em memória com o valor real (calculado),
    em vez do valor estático salvo no banco. Não faz commit — é só pra
    essa resposta específica da API refletir a verdade atual."""
    ids_abertos = _ids_programas_com_edital_aberto(db, [p.id for p in programas])
    for p in programas:
        p.programa_aberto = p.id in ids_abertos
    return programas


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
    programa = _com_relacionamentos(
        db.query(Programa).filter(Programa.id == programa_id)
    ).first()

    if programa is not None:
        _sincronizar_programa_aberto(db, [programa])

    return programa


def programas_do_coordenador(db: Session, coordenador_id: uuid.UUID) -> list[Programa]:
    """Retorna 1 (só mestrado OU doutorado) ou 2 (mestrado E doutorado do mesmo PPG)."""
    programas = _com_relacionamentos(
        db.query(Programa).filter(Programa.coordenador_id == coordenador_id)
    ).all()
    return _sincronizar_programa_aberto(db, programas)


def _aplicar_filtros(
    query,
    nivel=None,
    instituicao_id=None,
    area_avaliacao_id=None,
    area_conhecimento_id=None,
    nota_capes_min=None,
    nome=None,
    grande_area_id=None,
):
    if grande_area_id is not None:
        query = query.join(AreaAvaliacao, Programa.area_avaliacao_id == AreaAvaliacao.id)
        query = query.filter(AreaAvaliacao.grande_area_id == grande_area_id)
    if nivel is not None:
        query = query.filter(Programa.nivel == nivel)
    if instituicao_id is not None:
        query = query.filter(Programa.instituicao_id == instituicao_id)
    if area_avaliacao_id is not None:
        query = query.filter(Programa.area_avaliacao_id == area_avaliacao_id)
    if area_conhecimento_id is not None:
        query = query.filter(Programa.area_conhecimento_id == area_conhecimento_id)
    if nota_capes_min is not None:
        query = query.filter(Programa.nota_capes >= nota_capes_min)
    if nome:
        query = query.filter(Programa.nome.ilike(f"%{nome}%"))
    return query


def listar_programas(
    db: Session,
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
    nota_capes_min: Optional[int] = None,
    nome: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    grande_area_id: Optional[int] = None,
) -> list[Programa]:
    query = db.query(Programa).options(
        joinedload(Programa.linhas_pesquisa),
        joinedload(Programa.etapas_processo),
    )
    query = _aplicar_filtros(
        query, nivel, instituicao_id, area_avaliacao_id,
        area_conhecimento_id, nota_capes_min, nome,
        grande_area_id=grande_area_id,
    )
    query = query.order_by(Programa.nome)
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    programas = query.all()
    return _sincronizar_programa_aberto(db, programas)


def contar_programas(
    db: Session,
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
    nota_capes_min: Optional[int] = None,
    nome: Optional[str] = None,
    grande_area_id: Optional[int] = None,
) -> int:
    query = db.query(Programa)
    query = _aplicar_filtros(
        query, nivel, instituicao_id, area_avaliacao_id,
        area_conhecimento_id, nota_capes_min, nome,
        grande_area_id=grande_area_id,
    )
    return query.count()


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