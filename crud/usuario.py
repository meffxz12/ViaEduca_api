import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Usuario, Estudante, Coordenador
from schemas.usuario import EstudanteCreate, CoordenadorCreate
from security import criar_hash_senha


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def email_existe(db: Session, email: str) -> bool:
    # sem diferenciar maiúscula/minúscula: "Maria@x.com" e "maria@x.com" são a mesma conta
    return (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == _normalizar_email(email))
        .first()
        is not None
    )

def cpf_existe(db: Session, cpf: str) -> bool:
    return db.query(Usuario).filter(Usuario.cpf == cpf).first() is not None

def celular_existe(db: Session, celular: str) -> bool:
    return db.query(Usuario).filter(Usuario.celular == celular).first() is not None

def criar_estudante(db: Session, dados: EstudanteCreate) -> Usuario:

    usuario = Usuario(
        id=uuid.uuid4(),
        tipo="estudante",
        nome_completo=dados.nome_completo,
        cpf=dados.cpf,
        email=_normalizar_email(dados.email),
        senha_hash=criar_hash_senha(dados.senha),
        celular=dados.celular,
    )
    db.add(usuario)
    db.flush()

    estudante = Estudante(
        usuario_id=usuario.id,
        titulacao_atual=dados.titulacao_atual,
        area_titulacao_id=dados.area_titulacao_id,
    )
    db.add(estudante)
    db.commit()
    db.refresh(usuario)
    return usuario


def criar_coordenador(db: Session, dados: CoordenadorCreate) -> Usuario:

    usuario = Usuario(
        id=uuid.uuid4(),
        tipo="coordenador",
        nome_completo=dados.nome_completo,
        cpf=dados.cpf,
        email=_normalizar_email(dados.email),
        senha_hash=criar_hash_senha(dados.senha),
        celular=dados.celular,
    )
    db.add(usuario)
    db.flush()

    coordenador = Coordenador(
        usuario_id=usuario.id,
        email_institucional=dados.email_institucional,
        instituicao_id=dados.instituicao_id,
        area_avaliacao_id=dados.area_avaliacao_id,        # <-- adiciona
        area_conhecimento_id=dados.area_conhecimento_id,  # <-- adiciona
    )
    db.add(coordenador)
    db.commit()
    db.refresh(usuario)
    return usuario


def buscar_por_email(db: Session, email: str) -> Usuario | None:
    return (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == _normalizar_email(email))
        .first()
    )


def listar_usuarios(db: Session) -> list[Usuario]:
    return db.query(Usuario).all()


# ------------------------------------------------------------------
# APAGAR CONTA
# ------------------------------------------------------------------
def coordenador_tem_programas(db: Session, usuario_id) -> bool:
    """
    Checa se o coordenador ainda tem algum programa vinculado antes de
    deixar apagar a conta. A FK 'Programa.coordenador_id' não tem
    ondelete=CASCADE de propósito (apagar um coordenador não devia apagar
    os programas — eles continuam existindo pra outro coordenador assumir),
    então sem essa checagem o banco simplesmente recusaria o DELETE com um
    erro feio de integridade. Melhor avisar o usuário de forma clara antes.
    """
    from models import Programa
    return (
        db.query(Programa)
        .filter(Programa.coordenador_id == usuario_id)
        .first()
        is not None
    )


def apagar_usuario(db: Session, usuario: Usuario) -> None:
    """
    Apaga a conta. No banco, 'estudantes.usuario_id' e
    'coordenadores.usuario_id' têm ondelete=CASCADE pra 'usuarios.id', e as
    tabelas que dependem do estudante (favoritos, notificações) também têm
    CASCADE — então apagar o Usuario já apaga tudo isso junto
    automaticamente no Postgres.
    """
    db.delete(usuario)
    db.commit()