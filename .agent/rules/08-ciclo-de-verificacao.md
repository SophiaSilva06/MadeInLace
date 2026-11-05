---
trigger: always_on
description: "Ciclo obrigatório para toda alteração de código: patch em sandbox, oráculo estático (ruff, mypy), oráculo dinâmico (pytest), erros sanitizados com arquivo:linha:código e critério de homologação."
---

# Ciclo de verificação

Vale para toda alteração de código (Python, JS, templates), inclusive correções pequenas. Mudança só em documentação está isenta.

```text
[Agente emite patch] -> [Aplicação em sandbox]
        -> [Oráculo estático: ruff, mypy] --falha de sintaxe/tipos--+
        -> [Oráculo dinâmico: pytest]     --falha de asserção-------+
        -> exit code 0 -> [TAREFA HOMOLOGADA]                       v
                                         [Parser sanitizador de erros]
                                                      |
                              [Injeção de coordenadas: arquivo, linha, código]
                                                      |
                                       volta ao patch (próximo ciclo)
```

## Executor oficial
Rode sempre `tools/verify.py`, não os comandos soltos. Ele aplica a ordem, para no primeiro estágio que falha e imprime só o erro já sanitizado:

```bash
python tools/verify.py                                              # homologação: tudo, suíte completa
python tools/verify.py --alvo app/x.py --testes tests/test_x.py::test_a   # iteração
```

Saída: uma linha `ESTAGIO arquivo:linha:coluna CODIGO mensagem` por erro (máx. 10, ordenadas por arquivo e linha) e, sempre, a última linha `EXIT n`: 0 verde (`EXIT 0 PARCIAL` se usou `--alvo`/`--testes`), 1 falha de código, 2 não verificável (`FERRAMENTA_AUSENTE`, `BANCO_NAO_TESTE`, `TIMEOUT`). Não repita nem resuma a saída bruta das ferramentas; trabalhe só com essas linhas. Se o script não existir ou quebrar, rode à mão `ruff check --output-format=concise .`, `mypy`, `pytest -q --tb=short` e reduza ao mesmo formato.

## Passos
1. **Patch e sandbox:** aplique o patch só no workspace de desenvolvimento, com o banco `MADEINLACE_TEST` (regra 07). Rode `git status` antes e não sobrescreva alterações do usuário. O patch precisa ser pequeno e reversível. Nada de rodar testes em `MADEINLACE`.
2. **Oráculo estático, sempre antes dos testes:** ruff (sintaxe, lint) e depois mypy (tipos; o Ruff não verifica tipos). `ruff format` pode ser aplicado direto nos arquivos alterados. Falhou: não rode o pytest. Em JS, use Biome só se o projeto o configurar.
3. **Oráculo dinâmico:** na iteração, só os testes afetados; na homologação, a suíte completa. O critério é código de saída 0. Vitest só se o projeto o configurar.
4. **Sanitize o erro antes de corrigir.** Trabalhe só com as linhas do `tools/verify.py`: no máximo 10 itens por rodada, na ordem sintaxe, tipos, testes. Para teste: id, linha e esperado × obtido. Descarte cores ANSI, frames de bibliotecas, traceback repetido e avisos antigos. Corrija primeiro o item 1 (um erro de sintaxe costuma gerar os demais).
5. **Corrija pela coordenada:** abra só o trecho ao redor (±20 linhas) de `arquivo:linha` e corrija a causa, não o sintoma. Silenciar o oráculo é proibido (`# noqa`, `# type: ignore`, `per-file-ignores`, afrouxar regra do Ruff ou do mypy), salvo caso justificado e aprovado pelo usuário. As proibições sobre teste estão na regra 00. A cada novo patch, volte ao passo 1.
6. **Limite:** no máximo 5 ciclos por tarefa, ou o mesmo erro 2 vezes seguidas sem progresso. Então pare, volte ao último estado bom (`git restore`/`git stash` do que você mudou) e relate coordenadas, hipótese e o que já tentou.
7. **Homologação:** só diga "tarefa homologada" com ruff, mypy (se configurado) e pytest em `EXIT 0` (sem PARCIAL) na versão final, pelo comando completo. Antes de fechar, rode também `python .agent/skills/qa-adversarial-tester/scripts/check_integrity.py` (regra 00). Informe o comando e o `EXIT`. Etapa pulada, ferramenta ausente ou `EXIT 0 PARCIAL`: "não homologada", com o motivo.
