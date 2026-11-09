---
description: Decisão de remover o ano de nascimento dos dados versionados (minimização LGPD) e de sinalizar como não resolvido o empate que dependeria do critério de maior idade, até que o regulamento proponha outro critério.
---

# ADR 003: Sem ano de nascimento nos dados versionados e desempate por idade

> Registrada em 2026-11-09.

## Contexto
- O repositório é **público**. O JSON higienizado em `Dados/<ano>/extraidos/` trazia, para cada atleta, nome, sexo, clube, CBO e **ano de nascimento**. A combinação nome + ano de nascimento + clube identifica uma pessoa e vai além do mínimo necessário para apurar o campeonato (princípio da minimização, LGPD Art. 6º, III).
- O ano de nascimento só era usado no 3º critério de desempate individual do Regulamento 2026, Art. 34, § 2º (*maior idade*), depois de *melhor resultado no último percurso* e *percursos anteriores sucessivamente*. Na apuração parcial de 2026, nenhum empate chegou a esse critério (0 de 221 fichas).

## Decisão
1. O ano de nascimento **não é extraído nem versionado**: o campo `anoNascimento` sai do JSON, da leitura do Access (`extrairHelga.py`) e do motor de cálculo. O JSON passa a ser validado e **recusa** esse campo, para que ele não volte por engano.
2. O critério de **maior idade não é aplicado**. Quando dois atletas empatam em todos os critérios anteriores do Art. 34, § 2º, o motor os marca com `empateNaoResolvido`, mantém uma ordem estável (pelo número CBO) apenas para a apresentação, e o relatório avisa que o apurador deve decidir o empate fora do repositório.
3. A substituição desse critério por outro que não dependa de dado pessoal foi proposta na *issue* [Regulamentos-de-Orientacao#42](https://github.com/Jouderian/Regulamentos-de-Orientacao/issues/42), pois a regra é da FECORI (competição estadual) e não deste motor. Até a decisão da FECORI, vale o item 2.

## Consequências
- **Positivas:** o repositório público deixa de expor ano de nascimento; o esquema do JSON fica menor; a regra de dados pessoais mínimos passa a ser verificada por teste e pelo CI.
- **Negativas/Atenção:** a ordem de dois atletas empatados em tudo é provisória e depende de decisão humana; o motor não decide sozinho o que o regulamento ainda não define sem dado pessoal. Os resultados já publicados não mudam, pois não havia empate que dependesse da idade.
