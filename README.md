# Apuração do Campeonato Cearense de Orientação

Sistema para cálculo, auditoria e publicação dos resultados individuais e por clubes do **Campeonato Cearense de Orientação (CCO)** e do **Campeonato Cearense de Orientação Sprint (CCOS)**, da [FECORI](https://www.fecori.org.br/), a partir dos arquivos gerados pelo software de apuração em Microsoft Access (`.mdb` / `.accdb`).

As regras esportivas aplicadas por este motor seguem os regulamentos oficiais mantidos no repositório [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao).

## Estrutura do Repositório

| Caminho | Finalidade |
| :--- | :--- |
| [`src/extracaoAccess/`](src/extracaoAccess/) | Leitura dos arquivos `.mdb`/`.accdb` do software de apuração e higienização dos dados |
| [`src/motorCalculo/`](src/motorCalculo/) | Regras de pontuação, descarte, média de voluntários/árbitros, classificação de clubes e desempates |
| [`src/relatorios/`](src/relatorios/) | Geração de relatórios finais em Markdown, PDF e Excel |
| [`Dados/`](Dados/) | Entradas higienizadas, manifesto de integridade SHA-256 e resultados gerados por ano |
| [`tests/`](tests/) | Testes automatizados do motor de cálculo e da extração |
| [`.agents/`](.agents/) | Especificações (SDD), decisões arquiteturais (ADRs), regras de agentes e scripts de verificação |

## Privacidade e Auditabilidade (LGPD)

Os arquivos brutos do Microsoft Access (`.mdb` / `.accdb`) não são versionados diretamente no Git para proteger dados pessoais sensíveis de atletas. Em vez disso:

1. O hash **SHA-256** do arquivo original de cada etapa é registrado em [`Dados/arquivosCongelados.sha256`](Dados/arquivosCongelados.sha256) para garantir rastreabilidade e imutabilidade.
2. Apenas os dados estritamente necessários para a classificação esportiva (número CBO, nome do atleta, categoria, clube, tempo/colocação e situação na etapa) são extraídos e versionados em `Dados/<ano>/entradas/`.

## Verificação e Testes

Antes de qualquer commit ou pull request, execute:

```bash
python .agents/scripts/verificar-projeto.py
```

## Licença

O **código-fonte** é distribuído sob a licença [PolyForm Noncommercial 1.0.0](LICENSE). Você pode usar, estudar, modificar e redistribuir para qualquer finalidade não comercial, o que inclui clubes, federações sem fins lucrativos, ensino e pesquisa. O uso comercial, como vender o motor ou oferecê-lo como serviço pago, exige autorização do autor.

As **regras esportivas** vêm do repositório [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao), cuja organização e formatação estão sob a [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR). O conteúdo das regras pertence à FECORI e à CBO, e as citações dele neste repositório continuam atribuídas a elas. As duas licenças são independentes, e a [ADR-002](.agents/wiki/decisions/ADR-002-licenciamento-polyform-noncommercial-e-relacao-com-o-regulamento.md) registra o motivo.

