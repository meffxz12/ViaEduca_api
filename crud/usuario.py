import uuid

from sqlalchemy.orm import Session

from models import Usuario, Estudante, Coordenador
from schemas.usuario import EstudanteCreate, CoordenadorCreate
from security import criar_hash_senha


def email_existe(db: Session, email: str) -> bool:
    return db.query(Usuario).filter(Usuario.email == email).first() is not None

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
        email=dados.email,
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
        email=dados.email,
        senha_hash=criar_hash_senha(dados.senha),
        celular=dados.celular,
    )
    db.add(usuario)
    db.flush()

    coordenador = Coordenador(
        usuario_id=usuario.id,
        email_institucional=dados.email_institucional,
        instituicao_id=dados.instituicao_id,
    )
    db.add(coordenador)
    db.commit()
    db.refresh(usuario)
    return usuario


def buscar_por_email(db: Session, email: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.email == email).first()


def listar_usuarios(db: Session) -> list[Usuario]:
    return db.query(Usuario).all()