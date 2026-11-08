# Dados das Competições por Ano

Cada subpasta `<ano>/` é dividida em três áreas para não misturar fontes humanas/brutas, extrações técnicas e relatórios finais:

- `entradas/`: contém **apenas** o banco bruto do software de apuração (`.mdb`/`.accdb`, ignorado pelo Git por LGPD) e o documento Markdown humano de voluntários e penalidades (`voluntariosCCO.md`).
- `extraidos/`: armazena os arquivos `.json` higienizados extraídos automaticamente do banco Access (`etapasHelga<ano>.json`).
- `resultados/`: armazena os relatórios finais de classificação individual e por clubes gerados pelo motor de cálculo.

Os hashes SHA-256 dos bancos `.mdb`/`.accdb` originais ficam registrados em [`arquivosCongelados.sha256`](arquivosCongelados.sha256).
