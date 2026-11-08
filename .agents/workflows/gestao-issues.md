---
description: Passo a passo para abrir, conduzir e fechar issues no repositório Apuracao-Campeonato.
---

# Workflow: Gestão de *Issues*

As regras gerais estão em [`rules.md`](../rules/rules.md).

## Rótulos Principais

| Rótulo | Quando usar |
| :--- | :--- |
| `tarefa` | Implementação de módulo, extração de dados, ajuste de relatório ou manutenção do repositório |
| `bug` | Divergência entre o cálculo gerado e a regra do Regulamento / ROP |
| `auditoria` | Conferência ou contestação de resultado de etapa/campeonato (Art. 26 do Regulamento) |

## Fluxo de Fechamento

Toda *issue* é fechada com comentário de resumo contendo:
- **Resumo:** o que foi feito (em até 3 linhas).
- **Mudanças:** arquivos alterados.
- **Referência:** hash do commit ou número do PR.
- **Fica de fora:** o que não foi feito e em qual *issue* ficou registrado (ou "nada").

