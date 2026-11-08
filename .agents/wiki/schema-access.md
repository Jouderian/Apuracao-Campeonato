---
description: Mapeamento das tabelas, colunas e códigos de status do banco de dados Microsoft Access (.mdb/.accdb) do software de apuração.
---

# Esquema do Banco de Dados Microsoft Access

Última atualização: 2026-11-08

Esta página documenta a estrutura das tabelas do arquivo `.mdb` / `.accdb` utilizado na apuração das etapas.

## Como inspecionar um novo arquivo Access

Coloque o arquivo `.mdb` ou `.accdb` localmente (ele está protegido pelo `.gitignore`) e execute o inspetor de esquema:

```powershell
python src/extracaoAccess/inspecionarBanco.py --arquivo "caminho/para/arquivo.mdb"
```

O script listará todas as tabelas, colunas e tipos de dados sem expor dados pessoais, permitindo atualizar o mapeamento abaixo.

## Tabelas Mapeadas

> *Pendente da primeira execução de `inspecionarBanco.py` sobre um arquivo real de etapa.*

| Tabela no Access | Papel na Apuração | Campos Relevantes (Higienizados) | Campos Ignorados (LGPD) |
| :--- | :--- | :--- | :--- |
| *A mapear* | Cadastro de atletas / inscrições | Número CBO, Nome, Sexo, Ano de Nascimento, Clube, Filiação | CPF, RG, Endereço, Telefone, E-mail |
| *A mapear* | Categorias e percursos | Nome da Categoria, Status do Percurso (válido / anulado) | — |
| *A mapear* | Resultados / Tempos da etapa | Atleta, Categoria, Tempo, Colocação, Status (OK, NC, DNF, DSQ, MP), Penalidade Art. 23 | — |

