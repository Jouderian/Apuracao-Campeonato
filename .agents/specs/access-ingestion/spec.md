---
description: Especificação da leitura de bancos Microsoft Access (.mdb/.accdb), registro de hash SHA-256 e extração higienizada.
status: concluída
---

# Especificação: Ingestão de Dados do Microsoft Access

## O Quê
Módulo responsável por ler o arquivo de banco de dados (`HelgaDat.mdb`) produzido pelo software de apuração Helga em cada etapa/percurso, registrar o hash SHA-256 do arquivo bruto e exportar um arquivo estruturado e higienizado em `Dados/<ano>/extraidos/`, mantendo em `Dados/<ano>/entradas/` apenas o `.mdb` e o arquivo Markdown de voluntários (`voluntariosCCO.md`).

## Por Quê
1. Desacoplar o motor de cálculo da dependência de drivers ODBC exclusivos do Windows, permitindo que os testes e o CI rodem em Linux (`ubuntu-latest`).
2. Cumprir a restrição de LGPD em repositório público, extraindo apenas dados esportivos públicos da etapa.
3. Preservar a cadeia de custódia do arquivo original por meio do hash SHA-256 e manter o controle de voluntários em Markdown legível para auditoria humana.

## Critérios de Aceitação
- [x] Utilitário de inspeção e extração ([`extrairHelga.py`](../../../src/extracaoAccess/extrairHelga.py)) capaz de mapear e extrair as tabelas do `HelgaDat.mdb` com esquema documentado em [`.agents/wiki/schema-access.md`](../../wiki/schema-access.md).
- [x] Registro do hash SHA-256 do arquivo `.mdb` em [`Dados/arquivosCongelados.sha256`](../../../Dados/arquivosCongelados.sha256).
- [x] Extração higienizada ([`Dados/2026/extraidos/etapasHelga2026.json`](../../../Dados/2026/extraidos/etapasHelga2026.json)) separada da pasta `entradas/`, onde ficam apenas o `.mdb` e [`Dados/2026/entradas/voluntariosCCO.md`](../../../Dados/2026/entradas/voluntariosCCO.md).
