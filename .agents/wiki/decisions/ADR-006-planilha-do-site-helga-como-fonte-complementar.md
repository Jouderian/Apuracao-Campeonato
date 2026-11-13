---
description: Decisão de aceitar a planilha exportada do site de resultados do Helga como fonte complementar de etapas cujo banco se perdeu ou veio sem resultados, congelada por SHA-256.
---

# ADR 006: Planilha do site do Helga como fonte complementar

> Registrada em 2026-11-11.

## Contexto
- Na apuração de 2025, o `HelgaDat.mdb` não tinha a 2ª etapa (o arquivo do evento se perdeu) e trazia a 3ª só com inscrições, todas `NP`. As duas etapas tinham resultado publicado no site de resultados do Helga, que não aceita acesso automatizado (HTTP 403).
- A transcrição por OCR dos PDFs do site foi tentada e descartada: perdia tempos e linhas, o que muda colocação e pontos.
- Uma planilha exportada à mão do site, com lista de partida e resultado, mostrou-se consistente: tempos conferem com min/km e com a diferença para o líder, e a lista de partida da 3ª etapa bate exatamente com as inscrições do banco.

## Decisão
1. A planilha `Dados/<ano>/entradas/exportadoSiteHelga.xlsx` é fonte oficial **complementar**: gera `etapasHelgaWeb<ano>.json`, e as etapas dele substituem as de mesmo número do banco ([spec](../../specs/web-results-ingestion/spec.md)).
2. A planilha é **congelada** por SHA-256 no `arquivosCongelados.sha256` e **é versionada** no Git (pois não contém dados sensíveis e serve como memória de cálculo); o JSON complementar também é versionado e traz o hash.
3. A extração recusa qualquer inconsistência (lista de problemas) em vez de corrigir por estimativa.
4. Categorias com prefixo `Militar` não valem para o CCO e ficam fora.

## Consequências
- **Positivas:** etapas sem banco utilizável podem ser apuradas com rastreabilidade; todo inscrito tem situação definida, inclusive quem não largou.
- **Negativas/Atenção:** a planilha é produzida à mão, então a conferência automática é a garantia; a extração só roda onde a planilha existe (como o `.mdb`). Etapa sem lista de partida não pode usar este caminho.
