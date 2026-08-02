from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
    event,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import text
from database import Base

# ---------------------------------------------------------------------------
# 1. GrandesAreas — lista estática definida pelo professor
# ---------------------------------------------------------------------------
class GrandeAreas(Base):
    __tablename__ = "grandes_areas"

    id   = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)

    # relationships
    estudantes = relationship("Estudante", back_populates="grande_area")

    def __repr__(self):
        return f"<GrandeAreas id={self.id} nome={self.nome!r}>"


# ---------------------------------------------------------------------------
# 2. AreasAvaliacao — sincronizado 1x/dia da API Sucupira
# ---------------------------------------------------------------------------
class AreaAvaliacao(Base):
    __tablename__ = "areas_avaliacao"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    id_capes        = Column(Integer, nullable=False, unique=True)
    nome            = Column(String(150), nullable=False)
    sincronizado_em = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    areas_conhecimento = relationship("AreaConhecimento", back_populates="area_avaliacao")
    programas          = relationship("Programa", back_populates="area_avaliacao",
                                      foreign_keys="Programa.area_avaliacao_id")

    def __repr__(self):
        return f"<AreaAvaliacao id_capes={self.id_capes} nome={self.nome!r}>"


# ---------------------------------------------------------------------------
# 3. AreasConhecimento — sub-áreas, sincronizado 1x/dia da API Sucupira
# ---------------------------------------------------------------------------
class AreaConhecimento(Base):
    __tablename__ = "areas_conhecimento"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    id_capes          = Column(Integer, nullable=False, unique=True)
    area_avaliacao_id = Column(Integer, ForeignKey("areas_avaliacao.id", ondelete="CASCADE"),
                               nullable=False)
    nome              = Column(String(150), nullable=False)
    sincronizado_em   = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    area_avaliacao = relationship("AreaAvaliacao", back_populates="areas_conhecimento")
    programas      = relationship("Programa", back_populates="area_conhecimento",
                                  foreign_keys="Programa.area_conhecimento_id")

    def __repr__(self):
        return f"<AreaConhecimento id_capes={self.id_capes} nome={self.nome!r}>"


# ---------------------------------------------------------------------------
# 4. Instituicoes
# ---------------------------------------------------------------------------
class Instituicao(Base):
    __tablename__ = "instituicoes"
    id = Column(Integer, primary_key=True)
    id_capes = Column(Integer, unique=True)  # <- adicionar
    nome = Column(String)
    sigla = Column(String(100))
    # relationships
    coordenadores = relationship("Coordenador", back_populates="instituicao")
    programas     = relationship("Programa", back_populates="instituicao")

    def __repr__(self):
        return f"<Instituicao id={self.id} sigla={self.sigla!r}>"


# ---------------------------------------------------------------------------
# 5. Usuarios — base compartilhada (estudante e coordenador)
# ---------------------------------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    server_default=text("gen_random_uuid()"))
    tipo          = Column(Enum("estudante", "coordenador", name="tipo_usuario"), nullable=False)
    nome_completo = Column(String(150), nullable=False)
    cpf           = Column(String(11), nullable=False, unique=True)
    email         = Column(String(150), nullable=False, unique=True)
    senha_hash    = Column(String(255), nullable=False)
    celular       = Column(String(20))
    foto_url      = Column(String(255))
    criado_em     = Column(DateTime, nullable=False, default=datetime.now)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # relationships (1-pra-1, dependendo do tipo)
    estudante    = relationship("Estudante", back_populates="usuario", uselist=False)
    coordenador  = relationship("Coordenador", back_populates="usuario", uselist=False)

    fcm_token = Column(String(255), nullable=True)
    def __repr__(self):
        return f"<Usuario id={self.id} tipo={self.tipo} email={self.email!r}>"


# ---------------------------------------------------------------------------
# 6. Estudantes — perfil específico do estudante
# ---------------------------------------------------------------------------
class Estudante(Base):
    __tablename__ = "estudantes"

    usuario_id      = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"),
                             primary_key=True)
    titulacao_atual = Column(
        Enum("Graduação", "Especialização", "Mestrado", "Doutorado", name="titulacao")
    )
    area_titulacao_id  = Column(Integer, ForeignKey("grandes_areas.id"))

    # relationships
    usuario       = relationship("Usuario", back_populates="estudante")
    grande_area   = relationship("GrandeAreas", back_populates="estudantes")
    favoritos     = relationship("ProgramaFavorito", back_populates="estudante")
    notificacoes  = relationship("Notificacao", back_populates="estudante")

    def __repr__(self):
        return f"<Estudante usuario_id={self.usuario_id}>"


# ---------------------------------------------------------------------------
# 7. Coordenadores — perfil específico do coordenador
# ---------------------------------------------------------------------------
class Coordenador(Base):
    __tablename__ = "coordenadores"

    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )

    email_institucional = Column(String(150), nullable=False)

    instituicao_id = Column(
        Integer,
        ForeignKey("instituicoes.id"),
        nullable=False,
    )

    area_avaliacao_id = Column(
        Integer,
        ForeignKey("areas_avaliacao.id"),
        nullable=False,
    )

    area_conhecimento_id = Column(
        Integer,
        ForeignKey("areas_conhecimento.id"),
        nullable=False,
    )

    usuario = relationship("Usuario", back_populates="coordenador")
    instituicao = relationship("Instituicao", back_populates="coordenadores")
    area_avaliacao = relationship("AreaAvaliacao")
    area_conhecimento = relationship("AreaConhecimento")

    programas = relationship("Programa", back_populates="coordenador")

# ---------------------------------------------------------------------------
# 8. Programas
# ---------------------------------------------------------------------------
class Programa(Base):
    __tablename__ = "programas"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "nome", "nivel", name="uq_programa_inst_nome_nivel"),
        CheckConstraint("nota_capes BETWEEN 1 AND 7", name="ck_nota_capes"),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    coordenador_id = Column(
    UUID(as_uuid=True),
    ForeignKey("coordenadores.usuario_id"),
    nullable=True
)
    instituicao_id       = Column(Integer, ForeignKey("instituicoes.id"), nullable=False)
    nome                 = Column(String(150), nullable=False)
    id_capes             = Column(String(20), unique=True, nullable=False)
    nivel                = Column(
        Enum("MP", "MA", "D", name="nivel_programa"), nullable=False
    )
    area_avaliacao_id    = Column(Integer, ForeignKey("areas_avaliacao.id"))
    area_conhecimento_id = Column(Integer, ForeignKey("areas_conhecimento.id"))
    nota_capes           = Column(SmallInteger)
    criado_em            = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    coordenador      = relationship("Coordenador", back_populates="programas")
    instituicao      = relationship("Instituicao", back_populates="programas")
    area_avaliacao   = relationship("AreaAvaliacao", back_populates="programas",
                                    foreign_keys=[area_avaliacao_id])
    area_conhecimento = relationship("AreaConhecimento", back_populates="programas",
                                     foreign_keys=[area_conhecimento_id])
    linhas_pesquisa  = relationship("LinhaPesquisa", back_populates="programa",
                                    cascade="all, delete-orphan")
    etapas_processo           = relationship("EtapaProcesso", back_populates="programa",
                                    cascade="all, delete-orphan",
                                    order_by="EtapaProcesso.ordem")
    editais          = relationship("Edital", back_populates="programa",
                                    cascade="all, delete-orphan")
    favoritos        = relationship("ProgramaFavorito", back_populates="programa")

    programa_aberto = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Programa id={self.id} nome={self.nome!r} nivel={self.nivel}>"


# ---------------------------------------------------------------------------
# 9. LinhasPesquisa — lista dinâmica no cadastro do programa
# ---------------------------------------------------------------------------
class LinhaPesquisa(Base):
    __tablename__ = "linhas_pesquisa"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    descricao   = Column(String(200), nullable=False)

    # relationships
    programa = relationship("Programa", back_populates="linhas_pesquisa")

    def __repr__(self):
        return f"<LinhaPesquisa id={self.id} descricao={self.descricao!r}>"


# ---------------------------------------------------------------------------
# 10. EtapasProcesso — lista dinâmica com ordem no cadastro do programa
# Ex: 1ª Análise curricular, 2ª Prova discursiva, 3ª Entrevista
# ---------------------------------------------------------------------------
class EtapaProcesso(Base):
    __tablename__ = "etapas_processo"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    ordem       = Column(SmallInteger, nullable=False)
    descricao   = Column(String(200), nullable=False)

    # relationships
    programa         = relationship("Programa", back_populates="etapas_processo")
    arquivos_edital  = relationship("ArquivoEdital", back_populates="etapa")

    def __repr__(self):
        return f"<EtapaProcesso ordem={self.ordem} descricao={self.descricao!r}>"


# ---------------------------------------------------------------------------
# 11. Editais — ativado pelo toggle do coordenador
# ---------------------------------------------------------------------------
class Edital(Base):
    __tablename__ = "editais"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    programa_id           = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"),
                                   nullable=False)
    titulo                = Column(String(200), nullable=False)
    data_inicio_inscricao = Column(Date)
    data_fim_inscricao    = Column(Date)
    status                = Column(
        Enum("rascunho", "aberto", "encerrado", name="status_edital"),
        nullable=False,
        default="aberto",
    )
    criado_em    = Column(DateTime, nullable=False, default=datetime.now)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # relationships
    programa = relationship("Programa", back_populates="editais")
    arquivos = relationship("ArquivoEdital", back_populates="edital",
                            cascade="all, delete-orphan",
                            order_by="ArquivoEdital.publicado_em.desc()")
    descricao = Column(Text)
    def __repr__(self):
        return f"<Edital id={self.id} titulo={self.titulo!r} status={self.status}>"


# ---------------------------------------------------------------------------
# 12. ArquivosEdital — cada arquivo postado gera 1 notificação
# ---------------------------------------------------------------------------
class ArquivoEdital(Base):
    __tablename__ = "arquivos_edital"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    edital_id    = Column(Integer, ForeignKey("editais.id", ondelete="CASCADE"), nullable=False)
    etapa_id     = Column(Integer, ForeignKey("etapas_processo.id"))  # opcional
    titulo       = Column(String(200), nullable=False)
    arquivo_url  = Column(String(255), nullable=False)
    publicado_em = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    edital        = relationship("Edital", back_populates="arquivos")
    etapa         = relationship("EtapaProcesso", back_populates="arquivos_edital")
   

    def __repr__(self):
        return f"<ArquivoEdital id={self.id} titulo={self.titulo!r}>"


# ---------------------------------------------------------------------------
# 13. ProgramasFavoritos — "Meus Alertas" do estudante
# ---------------------------------------------------------------------------
class ProgramaFavorito(Base):
    __tablename__ = "programas_favoritos"

    estudante_id  = Column(UUID(as_uuid=True),
                           ForeignKey("estudantes.usuario_id", ondelete="CASCADE"),
                           primary_key=True)
    programa_id   = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"),
                           primary_key=True)
    favoritado_em = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    estudante = relationship("Estudante", back_populates="favoritos")
    programa  = relationship("Programa", back_populates="favoritos")

    def __repr__(self):
        return f"<ProgramaFavorito estudante={self.estudante_id} programa={self.programa_id}>"


# ---------------------------------------------------------------------------
# 14. Notificacoes — gerada pelo trigger quando arquivo novo é postado
# ---------------------------------------------------------------------------
class Notificacao(Base):
    __tablename__ = "notificacoes"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    estudante_id = Column(UUID(as_uuid=True), ForeignKey("estudantes.usuario_id", ondelete="CASCADE"), nullable=False)
    edital_id    = Column(Integer, ForeignKey("editais.id", ondelete="CASCADE"), nullable=False)
    titulo       = Column(String(200), nullable=False)
    lida         = Column(Boolean, nullable=False, default=False)
    criado_em    = Column(DateTime, nullable=False, default=datetime.now)

    estudante = relationship("Estudante", back_populates="notificacoes")
    edital    = relationship("Edital")

    def __repr__(self):
        return f"<Notificacao id={self.id} lida={self.lida} titulo={self.titulo!r}>"


# ---------------------------------------------------------------------------
# 15. SyncLog — histórico da sincronização diária com a Sucupira
# ---------------------------------------------------------------------------
class SyncLog(Base):
    __tablename__ = "sync_log"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    fonte                 = Column(String(50), nullable=False, default="sucupira_capes")
    recurso               = Column(String(50), nullable=False)
    status                = Column(
        Enum("sucesso", "falha", "parcial", name="status_sync"), nullable=False
    )
    registros_novos       = Column(Integer, default=0)
    registros_atualizados = Column(Integer, default=0)
    mensagem_erro         = Column(Text)
    executado_em          = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"<SyncLog recurso={self.recurso!r} status={self.status} em={self.executado_em}>"
    
# Catalogo de programas vindos da CAPES/Sucupira — populado pelo sync diário.
class ProgramaCapes(Base):
    """
    Catálogo de programas vindos da CAPES/Sucupira — populado pelo sync diário.
    Usado só como referência pro dropdown de cadastro (Tela 2), nunca é
    ligado direto a um coordenador.
    """
    __tablename__ = "programas_capes"

    id = Column(Integer, primary_key=True)
    id_programa_capes = Column(Integer, unique=True, nullable=False)  # idPrograma da API
    nome = Column(String, nullable=False)
    codigo = Column(String)
    grau = Column(String)               # ex: "MESTRADO", "DOUTORADO"
    conceito = Column(String)  # em vez de SmallInteger        # nota CAPES sugerida
    situacao = Column(String)
    sigla_ies = Column(String)           # sigla da instituição, ex: "USP"

    instituicao_id = Column(Integer, ForeignKey("instituicoes.id"))
    area_avaliacao_id = Column(Integer, ForeignKey("areas_avaliacao.id"))
    area_conhecimento_id = Column(Integer, ForeignKey("areas_conhecimento.id"))

    sincronizado_em = Column(DateTime)