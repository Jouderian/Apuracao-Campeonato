# Apuração do Campeonato Cearense de Orientação

Sistema para cálculo, auditoria e publicação dos resultados individuais e por clubes do **Campeonato Cearense de Orientação (CCO)** e do **Campeonato Cearense de Orientação Sprint (CCOS)**, da [FECORI](https://www.fecori.org.br/), a partir dos arquivos gerados pelo software de apuração em Microsoft Access (`.mdb` / `.accdb`).

As regras esportivas aplicadas por este motor seguem os regulamentos oficiais mantidos no repositório [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao).

**Cada edição é apurada pelo regulamento do seu próprio ano** (`Documentos/<ano>/` do repositório de regulamentos): o 2025 não tem descarte e desempata de outra forma que o 2026, por exemplo. As regras de cada ano ficam em [`src/motorCalculo/regulamentos.py`](src/motorCalculo/regulamentos.py) (hoje 2025 e 2026), e um ano sem regras registradas não é apurado. Para apurar: `python src/apurarCampeonato.py --ano <ano> --competicao CCO` (o `--ano` é obrigatório). Detalhes em [`apurar-etapa.md`](.agents/workflows/apurar-etapa.md) e na [ADR-005](.agents/wiki/decisions/ADR-005-regulamento-por-ano-na-apuracao.md).

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

Instale as dependências uma vez. Os arquivos `requirements*.txt` trazem versões fixas e hashes, por isso a instalação exige `--require-hashes`:

```bash
pip install --require-hashes -r requirements.txt        # só para apurar (Excel e PDF)
pip install --require-hashes -r requirements-dev.txt    # para contribuir (inclui mypy, ruff, bandit e testes de propriedade)
```

Antes de qualquer commit ou pull request, execute:

```bash
python .agents/scripts/verificar-projeto.py
```

A verificação confere links e frontmatter dos `.md`, o índice de specs, o manifesto SHA-256 (inclusive o `sha256Fonte` de cada JSON extraído), a validação dos JSON extraídos (sem dados pessoais proibidos), Actions fixadas por SHA, dependências com hash, a análise estática (`mypy`, `ruff` e `bandit`) e roda os testes unitários e de integração. A rotina de revisão está em [`revisao-seguranca.md`](.agents/workflows/revisao-seguranca.md).

## Licença

O **código-fonte** é distribuído sob a licença [PolyForm Noncommercial 1.0.0](LICENSE). Você pode usar, estudar, modificar e redistribuir para qualquer finalidade não comercial, o que inclui clubes, federações sem fins lucrativos, ensino e pesquisa. O uso comercial, como vender o motor ou oferecê-lo como serviço pago, exige autorização do autor.

As **regras esportivas** vêm do repositório [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao), cuja organização e formatação estão sob a [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR). O conteúdo das regras pertence à [FECORI](https://www.fecori.org.br/) (regulamentos das competições cearense) e a [CBO](https://www.cbo.esp.br/) (Regras de Orientação Pedestre), e as citações dele neste repositório continuam atribuídas a elas. As duas licenças são independentes, e a [ADR-002](.agents/wiki/decisions/ADR-002-licenciamento-polyform-noncommercial-e-relacao-com-o-regulamento.md) registra o motivo.