"""Script para carregar o seed nos bancos madeinlace e madeinlace_test."""
from __future__ import annotations

import sys
from pathlib import Path
import pymysql
from pymysql.constants import CLIENT


def carregar_banco(nome_db: str, sql_conteudo: str) -> bool:
    print(f"\n==========================================")
    print(f"Executando carga no banco: {nome_db}")
    print(f"==========================================")
    
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="AntiGravity",
        password="1234",
        charset="utf8mb4",
        client_flag=CLIENT.MULTI_STATEMENTS,
        autocommit=False,
    )
    
    try:
        with conn.cursor() as cur:
            # 1. Garante que as descrições com acentos nas tabelas de domínio estejam corretas (UTF-8)
            cur.execute(f"USE {nome_db};")
            cur.execute("UPDATE METODO_PAGAMENTO SET METODO = 'Cartão de crédito' WHERE ID = 2 OR METODO LIKE '%cr%dito%';")
            cur.execute("UPDATE METODO_PAGAMENTO SET METODO = 'Cartão de débito' WHERE ID = 3 OR METODO LIKE '%d%bito%';")
            cur.execute("UPDATE STATUS_VENDA SET DESCRICAO = 'Pedido entregue à transportadora' WHERE ESTADO_ANDAMENTO = 'NA_TRANSPORTADORA';")
            cur.execute("UPDATE STATUS_VENDA SET DESCRICAO = 'Pedido em trânsito' WHERE ESTADO_ANDAMENTO = 'EM_TRANSITO';")
            cur.execute("UPDATE STATUS_TROCA SET DESCRICAO = 'Novo produto entregue à transportadora' WHERE ESTADO_ANDAMENTO = 'NA_TRANSPORTADORA';")
            cur.execute("UPDATE STATUS_TROCA SET DESCRICAO = 'Troca concluída: novo produto entregue' WHERE ESTADO_ANDAMENTO = 'ENTREGUE';")
            conn.commit()

            # 2. Prepara o script substituindo o USE pelo banco de destino
            # Substitui USE MADEINLACE; por USE <nome_db>;
            script_alvo = sql_conteudo
            if f"USE {nome_db};".lower() not in script_alvo.lower():
                import re
                script_alvo = re.sub(r"(?i)USE\s+MADEINLACE\s*;", f"USE {nome_db};", script_alvo)

            # 3. Executa o script do seed
            cur.execute(script_alvo)
            while conn.next_result():
                pass
            conn.commit()
            print(f"-> Seed executado com SUCESSO em {nome_db}!")

            # 4. Valida as contagens pós-inserção
            tabelas = [
                "LINHA", "FORNECEDORES", "PRODUTOS", "IMGS_PRODUTOS", "VARIACAO",
                "USUARIOS", "ENDERECO_USUARIO", "CARRINHO", "VENDA",
                "HISTORICO_STATUS_VENDA", "ITEM_VENDA", "AVALIACAO", "IMGS_AVALIACAO"
            ]
            print("\nContagens de registros inseridos:")
            for t in tabelas:
                cur.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = cur.fetchone()[0]
                print(f"  - {t}: {cnt}")

            # 5. Validação das constraints das 10 vendas
            cur.execute("""
                SELECT ID, SUBTOTAL, FRETE, DESCONTO, TOTAL,
                       ROUND(SUBTOTAL * IF(DESCONTO = 1, 0.90, 1.00), 2) + FRETE AS TOTAL_ESPERADO,
                       IF(TOTAL = ROUND(SUBTOTAL * IF(DESCONTO = 1, 0.90, 1.00), 2) + FRETE, 'OK', 'FALHA') AS STATUS_FORMULA
                FROM VENDA;
            """)
            vendas = cur.fetchall()
            print(f"\nValidação das {len(vendas)} vendas contra constraint CK_VENDA_TOTAL:")
            todas_ok = True
            for v in vendas:
                if v[6] != 'OK':
                    todas_ok = False
                    print(f"  [FALHA] Venda {v[0]}: Inserido {v[4]} != Esperado {v[5]}")
            if todas_ok:
                print(f"  -> Todas as {len(vendas)} vendas conferem exatamente com a fórmula financeira!")

        return True

    except Exception as e:
        conn.rollback()
        print(f"-> ERRO ao carregar {nome_db}: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def main() -> int:
    sql_path = Path("docs/seed_madeinlace.sql")
    if not sql_path.exists():
        print(f"Arquivo não encontrado: {sql_path}", file=sys.stderr)
        return 1

    sql_conteudo = sql_path.read_text(encoding="utf-8")

    sucesso_dev = carregar_banco("madeinlace", sql_conteudo)
    sucesso_test = carregar_banco("madeinlace_test", sql_conteudo)

    if sucesso_dev and sucesso_test:
        print("\n==========================================")
        print("CARGA FINALIZADA COM SUCESSO EM AMBOS BANCOS!")
        print("==========================================")
        return 0
    else:
        print("\nFalha na carga em um ou mais bancos.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
