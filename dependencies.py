from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import SessionLocal
from security import decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# igual ao de cima, mas NÃO dá erro se não vier token (rotas públicas que
# mostram mais coisas pra quem está logado)
oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


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
    from models import Usuario 

    credencial_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decodificar_token(token)
    if not payload or not payload.get("sub"):
        raise credencial_exception
    usuario_id: str = payload["sub"]

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise credencial_exception
    return usuario


def get_usuario_opcional(
    token: str | None = Depends(oauth2_scheme_opcional),
    db: Session = Depends(pegar_sessao),
):
    """Usuario logado, ou None se não mandou token / token inválido (nunca dá erro)."""
    from models import Usuario

    if not token:
        return None
    payload = decodificar_token(token)
    if not payload or not payload.get("sub"):
        return None
    return db.query(Usuario).filter(Usuario.id == payload["sub"]).first()


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