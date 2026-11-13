---
description: Decisão de apurar estritamente pelo regulamento do ano, sem se vincular a resultados já publicados, que substitui a ADR-007 e revê as interpretações de 2025 e o ícone do campeão.
---

# ADR 008: O regulamento prevalece sobre o publicado

> Registrada em 2026-11-13. Substitui a [ADR-007](ADR-007-resultado-oficial-publicado-prevalece.md).

## Contexto
- A ADR-007 fez o resultado de 2025 já publicado pela FECORI prevalecer, mesmo com erros de cálculo manual, e adotou para 2025 o método do publicado na soma de clubes, na coluna "Atletas" e no ícone do campeão.
- A FECORI pediu que o repositório **siga sempre, estritamente, o regulamento**, e que os arquivos de resultado representem o que o regulamento determina, sem a amarra do publicado.

## Decisão
1. **O regulamento do ano vale.** Resultado já publicado não vincula a apuração; onde difere, vale o cálculo pelo regulamento e pelos dados.
2. **Regras de 2025 revistas** (`regulamentos.py`):
   - **Clubes (Arts. 37 e 39):** os 3 melhores atletas filiados de cada categoria, **por etapa** (antes: os 3 maiores totais finais).
   - **Coluna "Atletas":** atletas distintos que participaram (antes: linhas do resultado individual).
   - **Voluntário (Art. 36, § 1º):** precisa **competir** em metade das etapas (arredondada para cima); a etapa de apoio **não conta** (antes: contava). A média é dividida por todas as outras etapas realizadas e arredondada a 2 casas, como em 2026 (o regulamento não define o arredondamento).
   - **Mantido:** só clubes filiados à FECORI são classificados (Art. 40, com o Art. 2º).
3. **Seções do `voluntariosCCO.md` de 2025** `Ajustes` e `Atletas Fora do Resultado Oficial Publicado` foram removidas; aparecem agora os atletas que o publicado omitia. **Exceção, por pedido da FECORI:** nos empates que o regulamento deixa para a maior idade (Art. 38, Parágrafo Único, "c"; ADR-003), vale a ordem que a FECORI decidiu em 2025. Ela fica na seção `Desempates Decididos pela FECORI` (17 posições em 6 categorias) e só vale para atletas ainda empatados no cálculo do regulamento; o H Master A (CBO 21843) segue sinalizado, pois a FECORI não decidiu sua posição.
4. **Ícone do campeão nos PDFs:** os regulamentos de 2025 (Art. 42) e de 2026 (Art. 38) premiam atletas só com medalhas; o troféu é dos clubes (Arts. 41 e 39). Todo campeão de categoria tem **medalha de ouro**, e o quadro de premiação tem 3 linhas.
5. **Interpretações** onde o regulamento é omisso ou ambíguo seguem como escolha do apurador, em ADR ou na spec (ADR-005), nunca como "o publicado fez assim".
6. Os mecanismos de ajuste de nota, posição e omissão continuam no motor para uma **decisão formal futura da FECORI**; hoje nenhum dado os usa. A regra está em [`rules.md`](../../rules/rules.md).
7. O item 8 da ADR-007 (layout dos PDFs, logos e brasões) continua valendo.

## Consequências
- **Positivas:** os resultados refletem o regulamento; nenhuma regra depende de erro de cálculo manual.
- **Negativas/Atenção:** o resultado de 2025 **muda em relação ao publicado**, inclusive a classificação de clubes (COCAP passa a 3º, e a TRILHA NORTE a 4º) e pontos individuais. O H Master A tem um empate sem decisão da FECORI (CBO 21843). Quem já recebeu o resultado antigo precisa ser avisado.
