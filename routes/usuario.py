from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
from routes.verificacao import disparar_verificacao_email
from crud.verificacao import verificacao_exigida

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
    tasks: BackgroundTasks,
    db: Session = Depends(pegar_sessao),
):
    if crud.email_existe(db, dados.email):
        raise HTTPException(400, "E-mail já cadastrado")
    if crud.cpf_existe(db, dados.cpf):
        raise HTTPException(400, "CPF já cadastrado")
    if dados.celular and crud.celular_existe(db, dados.celular):
        raise HTTPException(400, "Celular já cadastrado")
    usuario = crud.criar_estudante(db, dados)
    disparar_verificacao_email(db, usuario, tasks)   # manda o código por e-mail
    return usuario

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
    tasks: BackgroundTasks,
    db: Session = Depends(pegar_sessao),
):
    if crud.email_existe(db, dados.email):
        raise HTTPException(400, "E-mail já cadastrado")
    if crud.cpf_existe(db, dados.cpf):
        raise HTTPException(400, "CPF já cadastrado")
    if dados.celular and crud.celular_existe(db, dados.celular):
        raise HTTPException(400, "Celular já cadastrado")

    coordenador = crud.criar_coordenador(db, dados)
    db.commit()
    disparar_verificacao_email(db, coordenador, tasks)   # manda o código por e-mail

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
    # Só avisa depois de a senha estar certa (não revela e-mail de terceiros).
    # O app reconhece esse texto e abre a tela de digitar o código.
    if verificacao_exigida() and not usuario.email_verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NAO_VERIFICADO",
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
    # Um aparelho = uma conta. Se o mesmo celular já estava ligado a outra conta
    # (várias contas de teste no mesmo aparelho), solta o token de lá — senão cada
    # conta dispara um push e o aparelho recebe a mesma notificação N vezes.
    db.query(Usuario).filter(
        Usuario.fcm_token == dados.fcm_token,
        Usuario.id != usuario_logado.id,
    ).update({Usuario.fcm_token: None}, synchronize_session=False)

    usuario_logado.fcm_token = dados.fcm_token
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------
# DELETE /auth/me — apagar a própria conta
# ------------------------------------------------------------------
class ExcluirContaRequest(BaseModel):
    senha: str


@auth_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def apagar_minha_conta(
    dados: ExcluirContaRequest,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(get_usuario_atual),
):
    # Pede a senha de novo antes de apagar — protege contra apagar sem
    # querer (ex: celular destravado na mão de outra pessoa) e é o padrão
    # pra qualquer ação irreversível como essa.
    if not verificar_senha(dados.senha, usuario_logado.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha incorreta")

    if usuario_logado.tipo == "coordenador":
        if crud.coordenador_tem_programas(db, usuario_logado.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Você ainda tem programas vinculados à sua conta. "
                "Remova ou transfira esses programas antes de excluir sua conta.",
            )

    crud.apagar_usuario(db, usuario_logado)