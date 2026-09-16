"""
routes/auth.py — cadastro e login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import usuario as crud
from dependencies import pegar_sessao, get_usuario_atual
from models import Usuario
from schemas.usuario import (
    EstudanteCreate,
    CoordenadorCreate,
    LoginRequest,
    TokenResponse,
    UsuarioResponse,
)
from security import verificar_senha, criar_token
from crud import programas as crud_programas
from pydantic import BaseModel

auth_router = APIRouter(prefix="/auth", tags=["Autenticação"])

# ------------------------------------------------------------------
# POST /auth/cadastro/estudante
# ------------------------------------------------------------------
@auth_router.post(
    "/cadastro/estudante",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_estudante(
    dados: EstudanteCreate,
    db: Session = Depends(pegar_sessao),
):
    if crud.email_existe(db, dados.email):
        raise HTTPException(400, "E-mail já cadastrado")
    return crud.criar_estudante(db, dados)

# ------------------------------------------------------------------
# POST /auth/cadastro/coordenador
# ------------------------------------------------------------------
@auth_router.post(
    "/cadastro/coordenador",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_coordenador(
    dados: CoordenadorCreate,
    db: Session = Depends(pegar_sessao),
):
    if crud.email_existe(db, dados.email):
        raise HTTPException(400, "E-mail já cadastrado")
    if crud.cpf_existe(db, dados.cpf):
        raise HTTPException(400, "CPF já cadastrado")
    if crud.celular_existe(db, dados.celular):
        raise HTTPException(400, "Celular já cadastrado")

    coordenador = crud.criar_coordenador(db, dados)
    db.commit()

    token = criar_token(str(coordenador.id), "coordenador")
    return TokenResponse(access_token=token, tipo_usuario="coordenador")
# ------------------------------------------------------------------
# POST /auth/login
# ------------------------------------------------------------------
@auth_router.post("/login", response_model=TokenResponse)
def login(
    dados: LoginRequest,
    db: Session = Depends(pegar_sessao),
):
    usuario = crud.buscar_por_email(db, dados.email)
    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )
    token = criar_token(str(usuario.id), usuario.tipo)
    return TokenResponse(access_token=token, tipo_usuario=usuario.tipo)


# ------------------------------------------------------------------
# GET /auth/me — perfil do usuário logado (token -> dados)
# ------------------------------------------------------------------
@auth_router.get("/me", response_model=UsuarioResponse)
def meu_perfil(usuario_logado: Usuario = Depends(get_usuario_atual)):
    return usuario_logado

class FcmTokenUpdate(BaseModel):
    fcm_token: str

@auth_router.post("/me/fcm-token")
def salvar_fcm_token(
    dados: FcmTokenUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(get_usuario_atual),
):
    usuario_logado.fcm_token = dados.fcm_token
    db.commit()
    return {"ok": True}