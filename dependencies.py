"""
dependencies.py — injeções de dependência reutilizáveis
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from database import SessionLocal
from security import decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def pegar_sessao():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(pegar_sessao),
):
    """Retorna o Usuario logado ou levanta 401."""
    from models import Usuario  # import local evita circular

    credencial_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decodificar_token(token)
        usuario_id: str = payload.get("sub")
        if not usuario_id:
            raise credencial_exception
    except JWTError:
        raise credencial_exception

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise credencial_exception
    return usuario


def exigir_coordenador(usuario=Depends(get_usuario_atual)):
    if usuario.tipo != "coordenador":
        raise HTTPException(status_code=403, detail="Apenas coordenadores podem fazer isso")
    return usuario


def exigir_estudante(usuario=Depends(get_usuario_atual)):
    if usuario.tipo != "estudante":
        raise HTTPException(status_code=403, detail="Apenas estudantes podem fazer isso")
    return usuario

def exigir_admin(usuario=Depends(get_usuario_atual)):
    if usuario.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem fazer isso")
    return usuario