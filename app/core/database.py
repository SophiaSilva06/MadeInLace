from collections.abc import Generator

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Integer,
    MetaData,
    SmallInteger,
    create_engine,
)
from sqlalchemy.dialects.mysql import (
    INTEGER as MYSQL_INTEGER,
)
from sqlalchemy.dialects.mysql import (
    SMALLINT as MYSQL_SMALLINT,
)
from sqlalchemy.dialects.mysql import (
    TINYINT as MYSQL_TINYINT,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Convenção de nomes: padroniza os nomes de constraints geradas pelo SQLAlchemy
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM SQLAlchemy 2.0."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Tipos de dados auxiliares com variantes MySQL nativas e compatibilidade cross-dialect
int_unsigned = Integer().with_variant(MYSQL_INTEGER(unsigned=True), "mysql")
smallint_unsigned = (
    SmallInteger()
    .with_variant(MYSQL_SMALLINT(unsigned=True), "mysql")
    .with_variant(Integer, "sqlite")
)
tinyint_unsigned = (
    SmallInteger()
    .with_variant(MYSQL_TINYINT(unsigned=True), "mysql")
    .with_variant(Integer, "sqlite")
)
bool_tinyint = Boolean().with_variant(MYSQL_TINYINT(1), "mysql")
money_decimal: DECIMAL = DECIMAL(10, 2)
percent_decimal: DECIMAL = DECIMAL(5, 2)

# Criação lazy/pool do engine de banco de dados
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI para obter sessão transacional do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
