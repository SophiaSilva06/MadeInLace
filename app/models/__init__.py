from app.core.database import Base
from app.models.avaliacao import Avaliacao, ImgsAvaliacao
from app.models.carrinho import Carrinho, ItemCarrinho
from app.models.dominio import Linha, MetodoPagamento, StatusTroca, StatusVenda
from app.models.fornecedor import (
    EmailsFornecedor,
    EnderecoFornecedor,
    Fornecedor,
    Fornecedores,
    TelefoneFornecedor,
)
from app.models.pos_venda import HistoricoStatusTroca, Reembolso, Troca
from app.models.produto import ImgsProduto, ImgsProdutos, Produto, Produtos, Variacao
from app.models.usuario import EnderecoUsuario, Recuperacao, Usuario, Usuarios, VerificacaoEmail
from app.models.venda import HistoricoStatusVenda, ItemVenda, Venda

__all__ = [
    "Base",
    # Tabelas de Domínio
    "Linha",
    "MetodoPagamento",
    "StatusVenda",
    "StatusTroca",
    # Fornecedores
    "Fornecedor",
    "Fornecedores",
    "EmailsFornecedor",
    "TelefoneFornecedor",
    "EnderecoFornecedor",
    # Produtos
    "Produto",
    "Produtos",
    "ImgsProduto",
    "ImgsProdutos",
    "Variacao",
    # Usuários
    "Usuario",
    "Usuarios",
    "EnderecoUsuario",
    "Recuperacao",
    "VerificacaoEmail",
    # Carrinho
    "Carrinho",
    "ItemCarrinho",
    # Vendas
    "Venda",
    "HistoricoStatusVenda",
    "ItemVenda",
    # Trocas e Reembolsos
    "Troca",
    "HistoricoStatusTroca",
    "Reembolso",
    # Avaliações
    "Avaliacao",
    "ImgsAvaliacao",
]
