# Base de análise de desempenho

Esta pasta recebe a base SQLite `analiseCCO.sqlite`, derivada dos JSON higienizados de `Dados/<ano>/extraidos/`. Ela **não é versionada** (fica no `.gitignore`) e se recria quando precisar. A análise é informativa e não faz parte da apuração do campeonato.

## Gerar a base

```powershell
python src/analises/gerarBase.py
```

Lê os JSON de todos os anos, confere o hash de cada um no manifesto e grava `Dados/analise/analiseCCO.sqlite`. Rode de novo depois de qualquer nova extração.

## Consultar

```powershell
python src/analises/consultar.py "SELECT nome, ritmoTexto FROM vwRitmo WHERE ano = 2026 AND numeroEtapa = 4 AND categoria = 'H Adulto E' ORDER BY ritmoSegundosPorKm"
```

A consulta é somente leitura (só `SELECT`), limitada a 200 linhas por padrão (`--limite`) e pode sair em JSON (`--json`).

## Mais informações

- Tabelas, colunas, unidades e regras de leitura: [dicionário de dados](../../.agents/wiki/dicionario-dados-analise.md).
- Decisão e motivos: [ADR-009](../../.agents/wiki/decisions/ADR-009-base-sqlite-gerada-para-analise-de-desempenho.md) e [spec da análise de desempenho](../../.agents/specs/analise-desempenho/spec.md).
