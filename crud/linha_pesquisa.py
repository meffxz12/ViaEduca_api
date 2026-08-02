"""
crud/linha_pesquisa.py — gerenciar linhas de pesquisa de um programa
depois do cadastro inicial (que é feito em lote via ProgramaCreate)
"""
from typing import Optional

from sqlalchemy.orm import Session

from models import LinhaPesquisa
from schemas.programas import LinhaPesquisaCreate, LinhaPesquisaUpdate


def adicionar(db: Session, programa_id: int, dados: LinhaPesquisaCreate) -> LinhaPesquisa:
    linha = LinhaPesquisa(programa_id=programa_id, descricao=dados.descricao)
    db.add(linha)
    db.commit()
    db.refresh(linha)
    return linha


def buscar(db: Session, linha_id: int) -> Optional[LinhaPesquisa]:
    return db.query(LinhaPesquisa).filter(LinhaPesquisa.id == linha_id).first()


def atualizar(db: Session, linha: LinhaPesquisa, dados: LinhaPesquisaUpdate) -> LinhaPesquisa:
    linha.descricao = dados.descricao
    db.commit()
    db.refresh(linha)
    return linha


def remover(db: Session, linha: LinhaPesquisa) -> None:
    db.delete(linha)
    db.commit()