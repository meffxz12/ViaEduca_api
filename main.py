from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes import usuario, areas, programas, edital, estudante, coordenador, instituicao, capes
app = FastAPI()
from routes.edital import edital_router
from routes.admin import admin_router
from routes.perfil import perfil_router
app.include_router(admin_router)
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.staticfiles import StaticFiles
from services.lembrete import iniciar_agendador
from dotenv import load_dotenv
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



os.makedirs("uploads/editais", exist_ok=True)
app.mount("/arquivos", StaticFiles(directory="uploads"), name="arquivos")
app.include_router(usuario.auth_router)
app.include_router(areas.areas_router)
app.include_router(programas.programas_router)
app.include_router(edital.edital_router)
app.include_router(instituicao.instituicao_router)
app.include_router(estudante.estudante_router)
app.include_router(coordenador.coordenador_router)
app.include_router(capes.capes_router)
app.include_router(perfil_router)

@app.on_event("startup")
def _iniciar_lembretes():
        iniciar_agendador()

@app.get("/")
def home():
    return {"mensagem": "API ViaEduca funcionando!"}