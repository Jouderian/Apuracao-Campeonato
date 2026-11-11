---
description: Decisão de que o resultado oficial já publicado prevalece sobre o recálculo, com as divergências registradas como ajustes auditáveis e as regras de clubes de 2025 (soma, federação e contagem de atletas) iguais às do publicado.
---

# ADR 007: O resultado oficial publicado prevalece

> Registrada em 2026-11-11.

## Contexto
- O resultado de 2025 foi calculado à mão e publicado pela FECORI. Ao reapurar 2025 com o motor, a comparação com o publicado (atleta por atleta e por clube) mostrou duas famílias de diferenças:
  1. **Método:** o publicado soma, para cada clube e categoria, os 3 melhores **totais finais** de atletas, e não os 3 melhores por etapa que o Art. 37 descreve.
  2. **Erros pontuais do cálculo manual:** pontos lançados que os dados e o regulamento não sustentam (um 21 no lugar de 31; dois atletas com 32 pontos na mesma categoria e etapa, embora os tempos sejam diferentes; um 1º lugar sem pontos; uma média lançada na etapa errada; uma média para quem não consta da lista de voluntários; um desclassificado com 0 ponto).
- A FECORI não pode recalcular o resultado já publicado.

## Decisão
1. O resultado oficial publicado **vale**, mesmo com erros. O repositório o reproduz.
2. A soma de clubes de 2025 segue o método do publicado (`clubeSomaTop3Por = "totalDoCampeonato"` em `regulamentos.py`). Em 2026 continua por etapa.
3. Cada erro pontual é um **ajuste** na seção `Ajustes do Resultado Oficial Publicado` do `voluntariosCCO.md`: etapa, CBO, categoria, pontos publicados e motivo. O motor aplica o ajuste depois de calcular a nota da etapa (inclusive a média de voluntário) e antes do total, do descarte e da classificação. Ajuste sem ficha correspondente recusa a apuração.
4. O relatório sinaliza as células ajustadas, para que ninguém confunda o publicado com o calculado.
5. O agente nunca corrige resultado publicado por conta própria.
6. A seção `Posições do Resultado Oficial Publicado` fixa a posição de quem o publicado desempatou por critério que o repositório não aplica (idade, ADR-003), e a seção `Atletas Fora do Resultado Oficial Publicado` omite as linhas que o publicado não tinha (atletas sem pontos que só constam da lista de partida da 2ª etapa, cujo banco se perdeu, ou voluntários sem inscrição). O motor recusa omissão de atleta com pontos ou sem ficha.
7. Também em 2025, o resultado de clubes só classifica clubes filiados à FECORI (`federacaoExigidaDoClube`; o CODAC, da FOMS, fica de fora, Art. 40) e a coluna "Atletas" conta as linhas do clube no resultado individual (`clubeContaAtletasPor`). Em 2026 vale a filiação à CBO e a contagem de atletas distintos.
8. Os PDFs finais (individual e de clubes) seguem o layout publicado pela FECORI, com a logo da edição, a logo da FECORI (`Dados/logoFECORI.png`) e os brasões dos clubes (`Dados/brasoes/<sigla>.png`), extraídos do resultado de clubes oficial de 2025.

## Consequências
- **Positivas:** o resultado reproduzido coincide com o publicado, e cada divergência fica visível, justificada e reversível.
- **Negativas/Atenção:** os ajustes carregam erros conhecidos do publicado; eles não são o que o regulamento produziria. Uma correção oficial futura se faz removendo ou alterando a linha do ajuste, com autorização.
