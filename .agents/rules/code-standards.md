---
description: Padrões de código Python — Arquitetura Limpa, funções puras no motor de cálculo, sanitização e testes automatizados.
trigger: always_on
---

# Padrões de Código

> Diretrizes técnicas aplicáveis a todo o código em [`src/`](../../src/) e [`tests/`](../../tests/).

## Princípios de Design e Arquitetura

1. **Separação de Responsabilidades (Clean Architecture):**
   - `src/extracaoAccess/`: leitura de arquivos `.mdb`/`.accdb`, validação de esquema e higienização (LGPD). Não calcula pontuação do campeonato.
   - `src/motorCalculo/`: funções puras e determinísticas que implementam os artigos do Regulamento (pontuação de etapa, descarte, média de voluntários, clubes e desempates). Não acessa banco de dados nem sistema de arquivos.
   - `src/relatorios/`: formatação dos resultados calculados em Markdown, PDF ou Excel.
   - `src/analises/`: análises informativas de desempenho (ritmo, evolução, parciais), em funções puras sobre os JSON higienizados. Nunca abre `.mdb`/`.accdb`, nunca altera nem alimenta pontuação, descarte, desempate ou clubes; o resultado é rotulado como informativo ([spec](../specs/analise-desempenho/spec.md), [ADR-009](../wiki/decisions/ADR-009-base-sqlite-gerada-para-analise-de-desempenho.md)).
2. **Rastreabilidade Normativa em Docstrings:**
   - Toda função de regra esportiva em `src/motorCalculo/` deve referenciar na docstring o artigo e o parágrafo correspondentes do regulamento vigente (ex.: `Regulamento 2026, Art. 34, § 1º`).
3. **Tipagem Explícita e Imutabilidade:**
   - Uso obrigatório de *type hints* em assinaturas de funções e `dataclasses` (ou modelos tipados) para representar atletas, etapas, resultados e pontuações.
4. **Precisão Numérica:**
   - Médias de voluntários e somatórios que envolvem casas decimais (como observado no histórico de clubes com `,33`, `,50`, `,67`) devem seguir regra de arredondamento explícita e documentada em spec/ADR, evitando imprecisão de ponto flutuante binário (`Decimal` ou arredondamento controlado).
5. **Sanitização de Saídas:**
   - Nomes de atletas, clubes e categorias vindos de banco externo nunca entram em comandos de shell e são sanitizados antes de exportação para planilhas Excel/CSV (prevenindo injeção de fórmulas iniciadas por `=`, `+`, `-`, `@`).

6. **Entradas Externas Validadas e Sem Interpolação:**
   - JSON extraído e Markdown de entrada passam por `src/extracaoAccess/validarEntrada.py` (estrutura, dados pessoais proibidos, hash no manifesto) antes de chegar ao motor.
   - Valor externo (caminho de arquivo, nome, texto do banco) nunca é interpolado em script, SQL ou comando; vai por parâmetro ou variável de ambiente ([ADR-004](../wiki/decisions/ADR-004-endurecimento-de-seguranca-e-cadeia-de-suprimentos.md)).
7. **Análise Estática Obrigatória:**
   - `mypy --strict` em `src/`, `ruff` (E, F, B, S, UP) e `bandit` passam sem achados (`pyproject.toml`). Exceção só com justificativa no próprio código (`# noqa` ou `# nosec` com o motivo na linha anterior).

## Testes Automatizados

- Toda regra em `src/motorCalculo/` deve ter teste unitário correspondente em `tests/`, cobrindo casos normais e casos de borda (empates, número ímpar de etapas para voluntários, campeonato com 3 etapas ou menos sem descarte, atleta penalizado pelo Art. 23 sem direito a descarte, troca de categoria).
- Toda função de `src/analises/` tem teste unitário em `tests/`, incluindo o arredondamento e as recusas de entrada.
- O CI e o script [`verificar-projeto.py`](../scripts/verificar-projeto.py) executam a suíte de testes automaticamente.
- Todo achado de segurança corrigido ganha teste de regressão ([`revisao-seguranca.md`](../workflows/revisao-seguranca.md)); entradas de texto externas têm teste de propriedade (`hypothesis`).

