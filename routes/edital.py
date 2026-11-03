import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from crud import edital as crud
from crud import arquivo_edital as crud_arquivo
from crud import programas as crud_programas
from dependencies import pegar_sessao, exigir_coordenador, get_usuario_opcional
from models import EtapaProcesso, Usuario
from schemas.edital import EditalCreate, EditalUpdateStatus, EditalResponse, EditalUpdate
from schemas.arquivo_edital import ArquivoEditalResponse
from services import storage

edital_router = APIRouter(tags=["Editais"])

def _exigir_dono_programa(db: Session, programa_id: int, usuario_logado: Usuario):
    programa = crud_programas.buscar_programa(db, programa_id)
    if programa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programa não encontrado")
    if programa.coordenador_id != usuario_logado.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não é o coordenador deste programa")
    return programa


def _e_dono(programa, usuario: Usuario | None) -> bool:
    """True se quem está chamando é o coordenador dono do programa."""
    return (
        usuario is not None
        and usuario.tipo == "coordenador"
        and programa is not None
        and programa.coordenador_id == usuario.id
    )


# ------------------------------------------------------------------
# POST /programas/{programa_id}/editais
# ------------------------------------------------------------------
@edital_router.post(
    "/programas/{programa_id}/editais",
    response_model=EditalResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_edital(
    programa_id: int,
    dados: EditalCreate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    _exigir_dono_programa(db, programa_id, usuario_logado)
    return crud.criar_edital(db, programa_id, dados)


# ------------------------------------------------------------------
# GET /programas/{programa_id}/editais
# ------------------------------------------------------------------
@edital_router.get(
    "/programas/{programa_id}/editais",
    response_model=list[EditalResponse],
)
def listar_editais(
    programa_id: int,
    db: Session = Depends(pegar_sessao),
    usuario: Usuario | None = Depends(get_usuario_opcional),
):
    editais = crud.listar_editais_por_programa(db, programa_id)

    # Rascunho é só do coordenador dono do programa. Pra qualquer outra
    # pessoa (estudante, visitante sem login) o rascunho nem existe.
    programa = crud_programas.buscar_programa(db, programa_id)
    if not _e_dono(programa, usuario):
        editais = [e for e in editais if e.status != "rascunho"]
    return editais


# ------------------------------------------------------------------
# PATCH /editais/{edital_id}/status
# ------------------------------------------------------------------
@edital_router.patch(
    "/editais/{edital_id}/status",
    response_model=EditalResponse,
)
def atualizar_status_edital(
    edital_id: int,
    dados: EditalUpdateStatus,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    if dados.status not in ("rascunho", "aberto", "encerrado"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Status inválido")

    return crud.atualizar_status(db, edital, dados.status)


# ------------------------------------------------------------------
# POST /editais/{edital_id}/arquivos — anexa arquivo (opcionalmente por etapa)
# ------------------------------------------------------------------
@edital_router.post(
    "/editais/{edital_id}/arquivos",
    response_model=ArquivoEditalResponse,
    status_code=status.HTTP_201_CREATED,
)
def anexar_arquivo(
    edital_id: int,
    titulo: str = Form(...),
    etapa_id: int | None = Form(None),
    alerta_sonoro: bool = Form(False),
    arquivo: UploadFile = File(...),
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")
    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    # A etapa escolhida tem que ser deste mesmo programa (antes dava pra ligar
    # o arquivo a uma etapa de outro programa, ou estourar 500 com id inexistente)
    if etapa_id is not None:
        etapa_ok = (
            db.query(EtapaProcesso.id)
            .filter(
                EtapaProcesso.id == etapa_id,
                EtapaProcesso.programa_id == edital.programa_id,
            )
            .first()
        )
        if etapa_ok is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Etapa inválida para este programa.",
            )

    # ── Proteções no upload: tamanho e tipo do arquivo ──────────────────
    # Sem isso, qualquer coordenador logado podia mandar um arquivo de
    # qualquer tamanho/tipo (ex: um executável, ou um PDF de 2GB) e lotar
    # o disco do servidor ou tentar algo malicioso.
    EXTENSOES_PERMITIDAS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
    TAMANHO_MAXIMO_MB = 20

    extensao = os.path.splitext(arquivo.filename or "")[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tipo de arquivo não permitido. Use: {', '.join(sorted(EXTENSOES_PERMITIDAS))}",
        )

    # Lê o arquivo na memória (no máximo 20MB) pra validar o tamanho antes de
    # guardar — guarda no Supabase Storage (produção) ou na pasta local (dev).
    tamanho_maximo_bytes = TAMANHO_MAXIMO_MB * 1024 * 1024
    conteudo = arquivo.file.read(tamanho_maximo_bytes + 1)
    if len(conteudo) > tamanho_maximo_bytes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Arquivo muito grande. Máximo permitido: {TAMANHO_MAXIMO_MB}MB",
        )
    if not conteudo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo vazio.")

    nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
    storage.salvar_arquivo(nome_arquivo, conteudo)

    # o caminho salvo continua o mesmo de sempre — o app não muda
    arquivo_url = f"/arquivos/editais/{nome_arquivo}"

    return crud_arquivo.criar_arquivo(
        db,
        edital_id=edital_id,
        etapa_id=etapa_id,
        titulo=titulo,
        arquivo_url=arquivo_url,
        alerta_sonoro=alerta_sonoro,
    )


# ------------------------------------------------------------------
# GET /editais/{edital_id}/arquivos — lista arquivos do edital
# ------------------------------------------------------------------
@edital_router.get(
    "/editais/{edital_id}/arquivos",
    response_model=list[ArquivoEditalResponse],
)
def listar_arquivos(
    edital_id: int,
    db: Session = Depends(pegar_sessao),
    usuario: Usuario | None = Depends(get_usuario_opcional),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    # Arquivos de rascunho só aparecem pro dono do programa
    if edital.status == "rascunho":
        programa = crud_programas.buscar_programa(db, edital.programa_id)
        if not _e_dono(programa, usuario):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    return crud_arquivo.listar_por_edital(db, edital_id)

@edital_router.patch(
    "/editais/{edital_id}",
    response_model=EditalResponse,
)
def atualizar_edital(
    edital_id: int,
    dados: EditalUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    return crud.atualizar_edital(db, edital, dados)


# ------------------------------------------------------------------
# DELETE /editais/{edital_id}
# ------------------------------------------------------------------
@edital_router.delete(
    "/editais/{edital_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def apagar_edital(
    edital_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    edital = crud.buscar_edital(db, edital_id)
    if edital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edital não encontrado")

    # Só o coordenador dono do programa pode apagar — mesma checagem
    # usada em todas as outras rotas de edital.
    _exigir_dono_programa(db, edital.programa_id, usuario_logado)

    crud.apagar_edital(db, edital)