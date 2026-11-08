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
2. **Rastreabilidade Normativa em Docstrings:**
   - Toda função de regra esportiva em `src/motorCalculo/` deve referenciar na docstring o artigo e o parágrafo correspondentes do regulamento vigente (ex.: `Regulamento 2026, Art. 34, § 1º`).
3. **Tipagem Explícita e Imutabilidade:**
   - Uso obrigatório de *type hints* em assinaturas de funções e `dataclasses` (ou modelos tipados) para representar atletas, etapas, resultados e pontuações.
4. **Precisão Numérica:**
   - Médias de voluntários e somatórios que envolvem casas decimais (como observado no histórico de clubes com `,33`, `,50`, `,67`) devem seguir regra de arredondamento explícita e documentada em spec/ADR, evitando imprecisão de ponto flutuante binário (`Decimal` ou arredondamento controlado).
5. **Sanitização de Saídas:**
   - Nomes de atletas, clubes e categorias vindos de banco externo nunca entram em comandos de shell e são sanitizados antes de exportação para planilhas Excel/CSV (prevenindo injeção de fórmulas iniciadas por `=`, `+`, `-`, `@`).

## Testes Automatizados

- Toda regra em `src/motorCalculo/` deve ter teste unitário correspondente em `tests/`, cobrindo casos normais e casos de borda (empates, número ímpar de etapas para voluntários, campeonato com 3 etapas ou menos sem descarte, atleta penalizado pelo Art. 23 sem direito a descarte, troca de categoria).
- O CI e o script [`verificar-projeto.py`](../scripts/verificar-projeto.py) executam a suíte de testes automaticamente.

