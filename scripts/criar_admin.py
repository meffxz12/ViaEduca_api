# scripts/criar_admin.py
from database import SessionLocal
from models import Usuario
from security import criar_hash_senha

def criar_admin():
    db = SessionLocal()
    try:
        email = input("Email do admin: ").strip()

        ja_existe = db.query(Usuario).filter(Usuario.email == email).first()
        if ja_existe:
            print("Já existe um usuário com esse email.")
            return

        senha = input("Senha: ").strip()
        nome = input("Nome completo: ").strip()
        cpf = input("CPF (11 dígitos, só números): ").strip()

        admin = Usuario(
            tipo="admin",
            nome_completo=nome,
            cpf=cpf,
            email=email,
            senha_hash=criar_hash_senha(senha),
        )
        db.add(admin)
        db.commit()
        print(f"Admin criado com sucesso! id={admin.id}")
    finally:
        db.close()

if __name__ == "__main__":
    criar_admin()