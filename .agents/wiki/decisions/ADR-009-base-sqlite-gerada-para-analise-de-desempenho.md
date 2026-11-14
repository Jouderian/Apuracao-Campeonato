---
description: Decisão de manter os JSON como fonte oficial e gerar, para a análise de desempenho, uma base SQLite derivada, consultada só para leitura por script, com dicionário de dados em Markdown.
---

# ADR 009: Base SQLite gerada para a análise de desempenho

> Registrada em 2026-11-13. Spec: [analise-desempenho](../../specs/analise-desempenho/spec.md).

## Contexto
- A análise de desempenho (ritmo médio, evolução, parciais) vai cruzar vários anos e será feita, a princípio, com apoio de uma IA.
- O `etapasHelga2026.json` tem cerca de 350 KB. Entregá-lo inteiro a uma IA é caro e impreciso, e o Markdown perde o tipo dos campos e gasta mais espaço que dado estruturado.
- O projeto exige auditabilidade e reprodutibilidade, e limita dependências novas ([ADR-004](ADR-004-endurecimento-de-seguranca-e-cadeia-de-suprimentos.md)).

## Decisão
1. **Fonte oficial inalterada:** os JSON versionados em `Dados/<ano>/extraidos/` (os existentes e os das Camadas A e B da spec) continuam sendo a única fonte. Nada da base é editado à mão.
2. **Base derivada:** um arquivo SQLite, `Dados/analise/analiseCCO.sqlite`, gerado dos JSON por `src/analises/gerarBase.py`, **ignorado pelo Git** (reconstruível) e sem data de geração, para sair idêntico a cada geração. A geração recusa JSON inválido ou sem hash conferido.
3. **Acesso por script, só leitura:** `src/analises/consultar.py` abre a base com `mode=ro`, aceita apenas `SELECT` e limita as linhas devolvidas. A IA escreve o SQL e roda o script; a conta (média, mediana, ritmo) é feita pelo SQL, nunca estimada pela IA.
4. **Dicionário de dados em Markdown:** [`dicionario-dados-analise.md`](../dicionario-dados-analise.md), em `.agents/wiki/`, descreve tabelas, colunas, unidades e regras (por exemplo, "ritmo em min/km, só para quem concluiu"), e é o que a IA lê antes de consultar.
5. **Sem dependência nova:** usa apenas o módulo `sqlite3` do Python. Ficam fora, por ora, servidor MCP de SQLite, DuckDB, pandas e site de página única; cada um pede ADR ou spec própria.
6. **LGPD:** a base herda só os campos dos JSON higienizados, sem ano de nascimento ([ADR-003](ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)).

## Consequências
- **Positivas:** consulta livre entre anos sem instalar nada; resultado reproduzível a partir dos JSON; a IA responde com a consulta usada, que o apurador pode conferir.
- **Negativas/Atenção:** a base precisa ser regerada a cada nova extração; o `.gitignore` e a seção de pastas de `Dados/` em `rules.md` precisam de ajuste na implementação (local da base e do dicionário), que só se altera com autorização expressa. Um site ou um servidor MCP no futuro reaproveitam a mesma base, mas pedem decisão nova.
