import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from services.notificador import notificar_favoritos
from models import Programa, LinhaPesquisa, EtapaProcesso, AreaAvaliacao, Edital 
from schemas.programas import ProgramaCreate, ProgramaUpdate

def _com_relacionamentos(query):
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
    # Evita o erro 500 do banco (id_capes e (instituição, nome, nível) são
    # únicos) trocando por uma mensagem que o app consegue mostrar.
    ja_existe = (
        db.query(Programa)
        .filter(
            (Programa.id_capes == str(dados.id_programa_capes))
            | (
                (Programa.instituicao_id == dados.instituicao_id)
                & (Programa.nome == dados.nome)
                & (Programa.nivel == dados.nivel)
            )
        )
        .first()
    )
    if ja_existe is not None:
        return (
            "Este programa já está cadastrado. Se ele ainda não tem coordenador, "
            "solicite o vínculo pelo catálogo."
        )

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


def _aplicar_filtros(
    query,
    nivel=None,
    instituicao_id=None,
    area_avaliacao_id=None,
    area_conhecimento_id=None,
    nota_capes_min=None,
    nome=None,
    grande_area_id=None,
    nota_capes=None,
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
        from sqlalchemy import cast, Integer
        query = query.filter(
            Programa.nota_capes.op('~')(r'^[0-9]+$'),
            cast(Programa.nota_capes, Integer) >= nota_capes_min,
        )
    if nota_capes is not None:
        # nota exata (1 a 7 ou A) — é o que o filtro do app usa
        query = query.filter(Programa.nota_capes == nota_capes.upper())
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
    nota_capes: Optional[str] = None,
) -> list[Programa]:
    query = db.query(Programa).options(
        joinedload(Programa.linhas_pesquisa),
        joinedload(Programa.etapas_processo),
    )
    query = _aplicar_filtros(
        query, nivel, instituicao_id, area_avaliacao_id,
        area_conhecimento_id, nota_capes_min, nome,
        grande_area_id=grande_area_id,
        nota_capes=nota_capes,
    )
    query = query.order_by(Programa.nome)
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def contar_programas(
    db: Session,
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
    nota_capes_min: Optional[int] = None,
    nome: Optional[str] = None,
    grande_area_id: Optional[int] = None,
    nota_capes: Optional[str] = None,
) -> int:
    query = db.query(Programa)
    query = _aplicar_filtros(
        query, nivel, instituicao_id, area_avaliacao_id,
        area_conhecimento_id, nota_capes_min, nome,
        grande_area_id=grande_area_id,
        nota_capes=nota_capes,
    )
    return query.count()

def atualizar_programa(
    db: Session,
    programa: Programa,
    dados: ProgramaUpdate,
) -> Programa:
    campos = dados.model_dump(exclude_unset=True)
    estava_aberto = programa.programa_aberto
 
    for campo, valor in campos.items():
        setattr(programa, campo, valor)
 
   
    if "programa_aberto" in campos and programa.programa_aberto != estava_aberto:
        ultimo_edital = (
            db.query(Edital)
            .filter(Edital.programa_id == programa.id)
            .order_by(Edital.criado_em.desc())
            .first()
        )
        texto = (
            f"Programa aberto: {programa.nome}"
            if programa.programa_aberto
            else f"Programa encerrado: {programa.nome}"
        )
        notificar_favoritos(
            db, programa.id, ultimo_edital.id if ultimo_edital else None, texto
        )
 
    db.commit()
    db.refresh(programa)
    return programa