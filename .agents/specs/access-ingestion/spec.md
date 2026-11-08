---
description: Especificação da leitura de bancos Microsoft Access (.mdb/.accdb), registro de hash SHA-256 e extração higienizada.
status: ativa
---

# Especificação: Ingestão de Dados do Microsoft Access

## O Quê
Módulo responsável por ler o arquivo de banco de dados (`.mdb` ou `.accdb`) produzido pelo software de apuração de cada etapa/percurso, registrar o hash SHA-256 do arquivo bruto e exportar um arquivo estruturado e higienizado em `Dados/<ano>/entradas/`.

## Por Quê
1. Desacoplar o motor de cálculo da dependência de drivers ODBC exclusivos do Windows, permitindo que os testes e o CI rodem em Linux (`ubuntu-latest`).
2. Cumprir a restrição de LGPD em repositório público, extraindo apenas dados esportivos públicos da etapa.
3. Preservar a cadeia de custódia do arquivo original por meio do hash SHA-256.

## Critérios de Aceitação
- [ ] Utilitário de inspeção capaz de listar todas as tabelas e colunas de um arquivo `.mdb`/`.accdb` fornecido localmente para documentar o esquema em [`.agents/wiki/schema-access.md`](../../wiki/schema-access.md).
- [ ] Registro automático do hash SHA-256 do arquivo `.mdb`/`.accdb` em [`Dados/arquivosCongelados.sha256`](../../../Dados/arquivosCongelados.sha256).
- [ ] Extração higienizada contendo apenas campos necessários à apuração (identificador CBO, nome do atleta, sexo, faixa/ano para desempate de idade quando aplicável, clube, filiação, categoria, tempo, colocação e situação na etapa).

