---
description: Especificação da leitura de bancos Microsoft Access (.mdb/.accdb), registro de hash SHA-256 e extração higienizada.
status: concluída
---

# Especificação: Ingestão de Dados do Microsoft Access

## O Quê
Módulo responsável por ler o arquivo de banco de dados (`HelgaDat.mdb`) produzido pelo software de apuração Helga em cada etapa/percurso, registrar o hash SHA-256 do arquivo bruto e exportar um arquivo estruturado e higienizado em `Dados/<ano>/entradas/`.

## Por Quê
1. Desacoplar o motor de cálculo da dependência de drivers ODBC exclusivos do Windows, permitindo que os testes e o CI rodem em Linux (`ubuntu-latest`).
2. Cumprir a restrição de LGPD em repositório público, extraindo apenas dados esportivos públicos da etapa.
3. Preservar a cadeia de custódia do arquivo original por meio do hash SHA-256.

## Critérios de Aceitação
- [x] Utilitário de inspeção e extração ([`extrairHelga.py`](../../../src/extracaoAccess/extrairHelga.py)) capaz de mapear e extrair as tabelas do `HelgaDat.mdb` com esquema documentado em [`.agents/wiki/schema-access.md`](../../wiki/schema-access.md).
- [x] Registro do hash SHA-256 do arquivo `.mdb` em [`Dados/arquivosCongelados.sha256`](../../../Dados/arquivosCongelados.sha256).
- [x] Extração higienizada ([`Dados/2026/entradas/etapasHelga2026.json`](../../../Dados/2026/entradas/etapasHelga2026.json)) contendo apenas campos necessários à apuração (identificador CBO, nome do atleta, sexo, ano de nascimento para desempate de idade, clube, filiação, categoria, tempo e `Status_FK`).
