"""
crud/coordenador.py — leitura e atualização do perfil do coordenador

O perfil é composto de dois models: Usuario (dados comuns: celular,
foto_url) e Coordenador (dados específicos: email_institucional,
instituicao_id). Esse módulo trata os dois juntos.
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from models import Coordenador, Usuario
from schemas.coordenador import CoordenadorUpdate


def buscar_coordenador(db: Session, usuario_id: uuid.UUID) -> Optional[Coordenador]:
    return db.query(Coordenador).filter(Coordenador.usuario_id == usuario_id).first()


def atualizar_coordenador(
    db: Session,
    usuario: Usuario,
    coordenador: Coordenador,
    dados: CoordenadorUpdate,
) -> Coordenador:
    campos = dados.model_dump(exclude_unset=True)

    # celular e foto_url vivem em Usuario; o resto vive em Coordenador
    if "celular" in campos:
        usuario.celular = campos.pop("celular")
    if "foto_url" in campos:
        usuario.foto_url = campos.pop("foto_url")

    for campo, valor in campos.items():
        setattr(coordenador, campo, valor)

    db.commit()
    db.refresh(usuario)
    db.refresh(coordenador)
    return coordenador