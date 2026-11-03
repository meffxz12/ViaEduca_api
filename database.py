import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL não encontrada no .env")

# Supabase/Heroku entregam "postgres://..." ou "postgresql://...";
# o SQLAlchemy 2 só aceita "postgresql://" (ou "postgresql+psycopg2://").
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # testa a conexão antes de usar (o banco na nuvem derruba ociosas)
    pool_recycle=300,     # renova conexões a cada 5 min
    pool_size=5,
    max_overflow=2,       # o plano grátis tem poucas conexões simultâneas
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
