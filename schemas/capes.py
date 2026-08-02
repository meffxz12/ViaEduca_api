from pydantic import BaseModel


# ============================
# Facetas da CAPES
# ============================

class FacetaCAPES(BaseModel):
    tipo: int
    nome: str
    key: str
    value: str


# ============================
# Programa
# ============================

class ProgramaCAPES(BaseModel):
    idPrograma: int

    nome: str
    codigo: str

    grau: str
    modalidade: str

    conceito: str
    situacao: str

    siglaIes: str

    programaEmRede: int

    idAreaAvaliacao: int
    nomeAreaAvaliacao: str

    idAreaConhecimento: int
    nomeAreaConhecimento: str

    idGrandeAreaConhecimento: int
    nomeGrandeAreaConhecimento: str

    idModalidade: int
    idModalidadeEnsino: int

    nomeModalidadeEnsino: str


# ============================
# Resposta paginada
# ============================

class ProgramasCAPESResponse(BaseModel):
    content: list[ProgramaCAPES]
    size: int