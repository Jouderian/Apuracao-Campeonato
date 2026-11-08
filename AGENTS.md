# Apuração do Campeonato — Instruções para Agentes

Este repositório é mantido com apoio de agentes de IA de mais de uma ferramenta. Para que a regra valha igual em todas, ela vive em **um único arquivo canônico**:

> **[`.agents/rules/rules.md`](.agents/rules/rules.md) — leia por inteiro antes de qualquer tarefa.**

Não duplique regra aqui nem em arquivo de ferramenta específica. Toda alteração de regra permanente vai no arquivo canônico; os arquivos de entrada (este e os equivalentes de cada ferramenta) apenas apontam para ele.

## Contexto mínimo

| Para saber | Leia |
| :--- | :--- |
| O que é o projeto e como executar | [`README.md`](README.md) |
| Visão, atores e restrições inegociáveis | [`.agents/specs/project-vision/spec.md`](.agents/specs/project-vision/spec.md) |
| Specs e a situação de cada uma | [`.agents/specs/index.md`](.agents/specs/index.md) |
| Decisões arquiteturais e esquema do banco | [`.agents/wiki/index.md`](.agents/wiki/index.md) |
| Padrões de código e arquitetura limpa | [`.agents/rules/code-standards.md`](.agents/rules/code-standards.md) |
| O que está pendente | [*Issues* abertas](https://github.com/Jouderian/Apuracao-Campeonato/issues); passo a passo em [`.agents/workflows/gestao-issues.md`](.agents/workflows/gestao-issues.md) |

## Antes de qualquer commit

```bash
python .agents/scripts/verificar-projeto.py
```

O commit só pode ser proposto se a verificação passar. É a mesma checagem que o CI executa.

