import os

from dotenv import load_dotenv

load_dotenv()  # antes de importar o resto (security.py e storage.py leem o .env)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import SessionLocal
from routes import (
    areas,
    capes,
    coordenador,
    edital,
    estudante,
    instituicao,
    programas,
    usuario,
)
from routes.admin import admin_router
from routes.arquivos import arquivos_router
from routes.perfil import perfil_router
from routes.verificacao import verificacao_router
from services.lembrete import iniciar_agendador

app = FastAPI(title="API ViaEduca")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads/editais", exist_ok=True)

# arquivos dos editais (disco local ou redirecionamento pro Supabase Storage)
app.include_router(arquivos_router)

app.include_router(usuario.auth_router)
app.include_router(verificacao_router)      # /auth/config, verificar-email, esqueci-senha...
app.include_router(areas.areas_router)
app.include_router(programas.programas_router)
app.include_router(edital.edital_router)
app.include_router(instituicao.instituicao_router)
app.include_router(estudante.estudante_router)
app.include_router(coordenador.coordenador_router)
app.include_router(capes.capes_router)
app.include_router(perfil_router)
app.include_router(admin_router)

# rota opcional pra disparar os lembretes na mão (teste do roteiro de QA)
try:
    from routes.lembretes import lembretes_router
    app.include_router(lembretes_router)
except ImportError:
    pass


@app.on_event("startup")
def _iniciar_lembretes():
    iniciar_agendador()


@app.get("/")
def home():
    return {"mensagem": "API ViaEduca funcionando!"}


@app.get("/health")
def health():
    """Usado pelo monitor (UptimeRobot) e pelo Render.
    O SELECT 1 também mantém o banco do Supabase 'acordado'."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True}
    finally:
        db.close()
