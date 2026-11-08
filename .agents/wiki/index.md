---
description: Índice da base de conhecimento do projeto — decisões arquiteturais (ADRs) e páginas técnicas.
---

# Base de Conhecimento

Última atualização: 2026-11-08

Índice das páginas da wiki. As decisões formais ficam em `decisions/` como ADRs; specs, planos e workflows continuam sendo a fonte de verdade de cada iniciativa.

## Decisões Arquiteturais (ADRs)

| ADR | Assunto | Resumo |
| :--- | :--- | :--- |
| [ADR-001](decisions/ADR-001-arquitetura-python-e-extracao-access.md) | Arquitetura Python e Extração Higienizada do Access | Uso de Python 3.12+, separação entre leitura ODBC do Access (`.mdb`/`.accdb`) e motor de cálculo puro, com proteção LGPD e hash SHA-256 |
| [ADR-002](decisions/ADR-002-licenciamento-polyform-noncommercial-e-relacao-com-o-regulamento.md) | Licenciamento PolyForm Noncommercial | Código sob PolyForm Noncommercial 1.0.0; regras esportivas permanecem das entidades e da CC BY 4.0 do repositório de regulamentos; licenças independentes |

## Páginas Técnicas

| Página | Resumo |
| :--- | :--- |
| [Esquema do Banco Access](schema-access.md) | Mapeamento das tabelas, colunas e códigos de status do arquivo `.mdb`/`.accdb` do software de apuração |

## Onde mais procurar

| Assunto | Local |
| :--- | :--- |
| Visão, atores e restrições do projeto | [`specs/project-vision/spec.md`](../specs/project-vision/spec.md) |
| Specs e a situação de cada uma | [`specs/index.md`](../specs/index.md) |
| Regras gerais e convenções de Git | [`rules/rules.md`](../rules/rules.md) |
| Padrões de código e arquitetura limpa | [`rules/code-standards.md`](../rules/code-standards.md) |
| Como atualizar o repositório remoto | [`workflows/atualizar-repositorio.md`](../workflows/atualizar-repositorio.md) |
| Como importar uma etapa e calcular resultados | [`workflows/apurar-etapa.md`](../workflows/apurar-etapa.md) |
| Como gerir *issues* | [`workflows/gestao-issues.md`](../workflows/gestao-issues.md) |

