---
description: Decisão de licenciar o código de apuração em PolyForm Noncommercial 1.0.0 e de mantê-la independente da CC BY 4.0 do repositório de regulamentos.
---

# ADR 002: Licenciamento PolyForm Noncommercial e Relação com o Regulamento

> Registrada em 2026-11-08. Corresponde à [ADR 007](https://github.com/Jouderian/Regulamentos-de-Orientacao/blob/main/.agents/wiki/decisions/ADR-007-licenciamento-cc-by-e-relacao-com-o-codigo.md) do repositório Regulamentos-de-Orientacao.

## Contexto
O projeto tem dois repositórios públicos que se complementam: [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao), com o texto organizado das regras, e este, com o código que as aplica na apuração. Cada um tem uma necessidade distinta:

- **O código** é uma ferramenta que o autor quer manter aberta para auditoria, estudo e uso por clubes e federações, mas sem que terceiros a revendam ou a ofereçam como serviço pago.
- **O texto** precisa circular sem barreiras, com crédito ao autor da organização (CC BY 4.0). O conteúdo das regras pertence à FECORI e à CBO.

A CC BY 4.0 não se destina a software e não restringe o uso comercial. Licenças de software de código aberto convencionais (MIT, Apache) também não restringem.

## Decisão
1. O **código-fonte** é licenciado sob a [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0), com o texto oficial em inglês e uma tradução não oficial para conveniência no `LICENSE`.
2. As **regras esportivas** não são relicenciadas aqui. Citações do regulamento em specs, comentários e relatórios indicam a entidade e o artigo de origem (FECORI ou CBO) e não recebem a licença do código.
3. A licença do código é **independente** da CC BY 4.0 do repositório de regulamentos: usar um repositório não sujeita o outro às condições do primeiro.

## Consequências
- **Positivas:**
  * O código permanece público e auditável, em linha com a rastreabilidade do projeto (hash SHA-256, specs, ADRs).
  * Clubes, federações sem fins lucrativos, escolas e pesquisadores usam livremente.
  * O autor, como titular, mantém o direito de usar o código comercialmente e de licenciá-lo a terceiros sob outros termos.
- **Negativas/Atenção:**
  * A PolyForm Noncommercial não é licença de código aberto pela definição da OSI, e isso pode afastar contribuidores e empresas.
  * A licença vale para o código. Os arquivos de `Dados/` não têm licença declarada, e os dados pessoais seguem a LGPD ([ADR-001](ADR-001-arquitetura-python-e-extracao-access.md)).
  * O logotipo da edição não é licenciado para reuso.
  * Contribuições de terceiros entram sob a mesma licença. Para o autor continuar podendo relicenciar, é preciso que cada contribuidor ceda ou licencie seus direitos a ele.
  * Trocar de licença no futuro exige nova ADR e não alcança as cópias já distribuídas.
