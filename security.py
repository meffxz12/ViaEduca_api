from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext


SECRET_KEY = "MEUAMRZNHDXEUTPGTUMNGC1212"
ALGORITHM = "HS256"


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def verificar_senha(
    senha: str,
    senha_hash: str
):
    return pwd_context.verify(
        senha,
        senha_hash
    )


def criar_hash_senha(
    senha: str
):
    return pwd_context.hash(senha)


def criar_token(
    usuario_id: str,
    tipo_usuario: str
):

    expiracao = datetime.now(timezone.utc) + timedelta(hours=24)

    payload = {
        "sub": usuario_id,
        "tipo": tipo_usuario,
        "exp": expiracao
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def decodificar_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        return None