---
description: Visão fundacional, atores, arquitetura e restrições inegociáveis do sistema de apuração do campeonato.
status: ativa
---

# Visão do Projeto: Apuração do Campeonato

## Objetivo Principal
Automatizar, auditar e publicar o cálculo dos resultados individuais e por clubes do **Campeonato Cearense de Orientação (CCO)** e do **Campeonato Cearense de Orientação Sprint (CCOS)** a partir dos bancos de dados gerados pelo software de apuração em Microsoft Access (`.mdb` / `.accdb`), garantindo total conformidade com os regulamentos oficiais vigentes no repositório [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao).

## Atores
- **Diretoria Técnica e Apuradores (FECORI):** Importam os bancos de cada etapa, informam a lista oficial de voluntários/árbitros e geram a classificação parcial e final.
- **Árbitros dos Eventos:** Validam os resultados das etapas e os relatórios de apuração.
- **Clubes e Atletas:** Consultam os resultados publicados com transparência sobre a pontuação obtida em cada etapa, descartes aplicados, médias de voluntários e soma dos clubes.
- **Agentes de IA:** Mantêm o código e auditam os resultados seguindo o protocolo SDD.

## Restrições e Premissas Inegociáveis
1. **Fidelidade Estrita ao Regulamento:** Toda regra de cálculo deve refletir exatamente o Regulamento das Competições Cearenses de Orientação e a ROP da CBO vigentes naquele ano. Nenhuma regra esportiva é presumida sem amparo documental.
2. **Privacidade e Proteção de Dados (LGPD):** Como este repositório é público, arquivos brutos `.mdb`/`.accdb` contendo dados pessoais sensíveis (CPF, RG, endereço, contato, data de nascimento completa) nunca são comitados.
3. **Auditabilidade Criptográfica (SHA-256):** A integridade de cada arquivo `.mdb`/`.accdb` usado na apuração é garantida pelo registro de seu hash SHA-256 em [`Dados/arquivosCongelados.sha256`](../../../Dados/arquivosCongelados.sha256), acompanhado de extração higienizada versionada em `Dados/<ano>/entradas/`.
4. **Reprodutibilidade:** Dado o mesmo conjunto de entradas higienizadas e parâmetros da edição, o motor de cálculo produz resultado idêntico em qualquer sistema operacional.

