# Dados das Competições por Ano

Cada subpasta `<ano>/` é dividida em três áreas para não misturar fontes humanas/brutas, extrações técnicas e relatórios finais:

- `entradas/`: contém **apenas** o banco bruto do software de apuração (`.mdb`/`.accdb`, ignorado pelo Git por LGPD), a planilha exportada do site de resultados do Helga quando uma etapa não tem banco utilizável (`exportadoSiteHelga.xlsx`, também ignorada pelo Git e congelada por SHA-256) e o documento Markdown humano de voluntários e penalidades (`voluntariosCCO.md`).
- `extraidos/`: armazena os arquivos `.json` higienizados extraídos automaticamente do banco Access (`etapasHelga<ano>.json`, mais `etapasHelgaWeb<ano>.json` quando há planilha do site).
- `resultados/`: armazena os relatórios finais de classificação individual e por clubes gerados pelo motor de cálculo.

Na raiz de `Dados/` ficam também `logoFECORI.png` e a pasta `brasoes/` (um arquivo por clube, nomeado pela sigla em camelCase), usados nos PDFs finais.

Os hashes SHA-256 dos bancos `.mdb`/`.accdb` originais ficam registrados em [`arquivosCongelados.sha256`](arquivosCongelados.sha256).
