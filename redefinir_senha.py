import secrets
import string
import sys

from database import SessionLocal
from models import Usuario
from security import criar_hash_senha


def gerar_senha(tamanho: int = 10) -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        senha = "".join(secrets.choice(alfabeto) for _ in range(tamanho))
        # garante letra e número
        if any(c.isalpha() for c in senha) and any(c.isdigit() for c in senha):
            return senha


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python resetar_senha.py email@da.pessoa [nova_senha]")

    email = sys.argv[1].strip().lower()
    nova = sys.argv[2] if len(sys.argv) > 2 else gerar_senha()

    if len(nova) < 8:
        sys.exit("A senha precisa ter pelo menos 8 caracteres.")

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email.ilike(email)).first()
        if usuario is None:
            sys.exit(f"Nenhum usuário com o e-mail {email}.")

        usuario.senha_hash = criar_hash_senha(nova)
        db.commit()

        print(f"Senha de {usuario.nome_completo} ({usuario.email}) redefinida.")
        print(f"Senha provisória: {nova}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
