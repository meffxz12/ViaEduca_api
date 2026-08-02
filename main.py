from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes import usuario, areas, programas, edital, estudante, coordenador, instituicao, capes
app = FastAPI()
from routes.edital import edital_router


app.include_router(usuario.auth_router)
app.include_router(areas.areas_router)
app.include_router(programas.programas_router)
app.include_router(edital.edital_router)
app.include_router(instituicao.instituicao_router)
app.include_router(estudante.estudante_router)
app.include_router(coordenador.coordenador_router)
app.include_router(capes.capes_router)
# serve os arquivos de edital salvos localmente (uploads/editais/...)
#app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def home():
    return {"mensagem": "API ViaEduca funcionando!"}