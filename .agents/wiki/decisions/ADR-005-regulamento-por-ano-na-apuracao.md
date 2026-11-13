---
description: Decisão de apurar cada edição pelo regulamento do seu próprio ano, com regras registradas por ano e competição, e interpretações adotadas onde o regulamento de 2025 é omisso.
---

# ADR 005: Regulamento por ano na apuração

> Registrada em 2026-11-11.

## Contexto
- Este repositório complementa o [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao), que guarda um regulamento por ano em `Documentos/<ano>/`. Os regulamentos de 2025 e de 2026 diferem na apuração do CCO: o de 2025 não tem descarte, calcula a média do voluntário sem descarte, exige que o voluntário *compita* em metade das etapas e desempata por mais 1ºs lugares; o de 2026 tem descarte (mais de 3 etapas), média após descarte, exige *participar* e desempata pelo último percurso. Os artigos também mudam de número.
- O motor nasceu para 2026 e trazia essas regras fixas no código e nos textos dos relatórios. Ao entrar os dados de 2025, o cálculo aplicaria descarte e desempate de 2026 a um campeonato que não os prevê.

## Decisão
1. As regras de cada edição ficam em `src/motorCalculo/regulamentos.py`, um `RegrasRegulamento` imutável por par (ano, competição), com o arquivo-fonte e os artigos citados. O motor de cálculo e os relatórios **recebem** esse conjunto e não guardam constante de regulamento.
2. Ano ou competição sem regras registradas **não é apurado**: `obterRegras` levanta `RegulamentoNaoMapeadoError` e o comando recusa. Não há regra padrão nem "ano mais próximo". O `verificar-projeto.py` recusa dados extraídos de ano sem regras.
3. Registrar um ano novo exige ler o regulamento do ano, atualizar a spec do motor e criar testes (passo a passo em [`apurar-etapa.md`](../../workflows/apurar-etapa.md)).
4. O total de etapas realizadas é o das etapas presentes no JSON extraído, e os relatórios mostram uma coluna por etapa presente.

## Interpretações adotadas para 2025
O regulamento de 2025 é omisso ou ambíguo em três pontos. São **escolhas do apurador**, não fatos esportivos; a FECORI pode revê-las e, se mudarem, basta ajustar o campo correspondente em `regulamentos.py`.

| Ponto | Texto de 2025 | Interpretação (revista na [ADR-008](ADR-008-regulamento-prevalece-sobre-o-publicado.md)) |
| :--- | :--- | :--- |
| Mínimo de etapas do voluntário (Art. 36, § 1º) | "competir em, no mínimo, a metade das etapas realizadas" | **A etapa de voluntário/árbitro não conta no mínimo:** o texto exige *competir* (em 2026 é *participar*, e a etapa de apoio conta). A metade é arredondada **para cima** (leitura literal de "no mínimo a metade"). |
| Média do voluntário (Art. 36) | "a média da pontuação conquistada nas outras etapas" | A soma dos pontos das outras etapas é dividida pelo número de **todas as outras etapas realizadas**, inclusive as sem inscrição e a outra etapa de apoio (0 ponto). Em 2026 o divisor é só o das etapas em que o atleta se inscreveu. A média de cada voluntário é arredondada a 2 casas antes de somar, como em 2026. |
| Último confronto direto (Art. 38, Parágrafo Único, "b") | "melhor resultado no último confronto direto" | Vale a etapa mais recente em que **todos** os atletas empatados foram classificados na mesma categoria; vence a melhor colocação nela. Se não houver etapa assim, o empate segue para a idade. |
| Maior idade (Art. 38, Parágrafo Único, "c") | critério final | Não aplicado, como em 2026 ([ADR-003](ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)): o empate é sinalizado (`empateNaoResolvido`) para decisão do apurador. |

## Consequências
- **Positivas:** a apuração de cada ano segue o regulamento daquele ano; ano sem mapeamento falha de forma explícita; os artigos citados nos relatórios são os do ano.
- **Negativas/Atenção:** cada ano novo exige trabalho de leitura e de registro das regras antes da primeira apuração. As interpretações de 2025 acima precisam de confirmação da FECORI se houver contestação. Os anos anteriores a 2025 continuam sem regras registradas e, portanto, não podem ser apurados até serem mapeados.
