---
description: Passo a passo para importar o arquivo .mdb/.accdb de uma etapa, congelar o hash SHA-256, extrair dados higienizados e calcular o campeonato.
---

# Workflow: Apurar Etapa ou Ajustar Resultado do Campeonato

Este procedimento deve ser executado:
- **A cada nova etapa apurada** no banco do Helga (`HelgaDat.mdb`);
- **Sempre que novos voluntários ou árbitros forem informados** pelas equipes organizadoras ou pela FECORI;
- **Quando a FECORI demandar ajustes** cadastrais ou de apuração;
- **Todos os anos**, ao iniciar uma nova edição do campeonato.

## 0. Conferir o Regulamento do Ano (antes de tudo)

Este repositório complementa o [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao). **Cada edição é apurada pelo regulamento do seu próprio ano** (`Documentos/<ano>/regulamento*.md` daquele repositório); nunca assuma que o regulamento mais recente vale para anos anteriores nem que o anterior vale para os seguintes.

1. Confirme que o ano tem regras registradas em [`src/motorCalculo/regulamentos.py`](../../src/motorCalculo/regulamentos.py) (hoje: 2025 e 2026). O comando recusa ano sem regras e o `verificar-projeto.py` recusa dados extraídos de ano sem regras.
2. **Ano novo ou ano ainda não mapeado:** leia o regulamento do ano e compare, ponto a ponto, com a tabela de diferenças da [spec do motor](../specs/scoring-engine/spec.md): tabela de pontos, descarte, média e mínimo de etapas do voluntário, desempate individual, clubes, premiação e numeração dos artigos.
3. Registre o conjunto de regras em `regulamentos.py`, atualize a spec (tabela de diferenças) no mesmo commit, crie testes em `tests/` e, se houver interpretação ambígua, registre-a em ADR (modelo: [ADR-005](../wiki/decisions/ADR-005-regulamento-por-ano-na-apuracao.md)).
4. Só então siga para os passos abaixo.

## 1. Preparar Entradas e Logo da Edição

1. Salve o arquivo `.mdb` ou `.accdb` atualizado localmente em `Dados/<ano>/entradas/` (ex.: `Dados/2026/entradas/HelgaDat.mdb`). Na pasta `entradas/` ficam apenas o arquivo `.mdb` (ignorado pelo Git por LGPD) e o arquivo Markdown de voluntários (`voluntariosCCO.md`).
2. Certifique-se de que a logo oficial da edição esteja em `Dados/<ano>/logoCCO.jpeg` (copiada do repositório `Regulamentos-de-Orientacao/Documentos/<ano>/logoCCO.jpeg`). Os PDFs finais também usam `Dados/logoFECORI.png` e os brasões em `Dados/brasoes/<sigla>.png`; clube sem arquivo de brasão sai sem imagem.

## 2. Registrar ou Atualizar Voluntários e Árbitros em Markdown

Atualize a tabela em `Dados/<ano>/entradas/voluntariosCCO.md` conforme a relação oficial enviada em até 15 dias (CCO) ou ao término da apuração (CCOS), nos termos do Art. 33, § 4º do Regulamento. Caso alguma etapa ainda não tenha enviado a lista de voluntários, o relatório parcial indicará automaticamente as etapas pendentes no bloco de `OBSERVAÇÃO`.

## 3. Extrair Dados Higienizados e Congelar SHA-256 (Quando o `.mdb` mudar)

Se o arquivo `.mdb` tiver sido atualizado, execute a extração para gerar o snapshot JSON higienizado em `Dados/<ano>/extraidos/` e atualize o hash SHA-256 em [`Dados/arquivosCongelados.sha256`](../../Dados/arquivosCongelados.sha256):

```powershell
python src/extracaoAccess/extrairHelga.py --mdb "Dados/2026/entradas/HelgaDat.mdb" --saida "Dados/2026/extraidos/etapasHelga2026.json"
```

## 3b. Etapa sem banco utilizável: planilha do site do Helga (quando for o caso)

Se o banco de uma etapa se perdeu ou veio sem resultados, use a planilha exportada do site de resultados do Helga ([spec](../specs/web-results-ingestion/spec.md), [ADR-006](../wiki/decisions/ADR-006-planilha-do-site-helga-como-fonte-complementar.md)). Ela deve ter, por etapa, uma aba `listaPartidaEtapa<N>` e uma `resultadoEtapa<N>`, e ficar em `Dados/<ano>/entradas/exportadoSiteHelga.xlsx`:

```powershell
python src/extracaoAccess/leitorHelgaWeb.py --ano 2025 --etapa-nova "2|2025-06-29|COFORT|Sabiaguaba - Fortaleza/CE|6071" --alias-clube "Nome do clube no site=SIGLA"
```

- `--etapa-nova` só é necessário para etapa que não existe no banco (`NUM|DATA|SIGLA_CLUBE|LOCAL|COMPETITION_ID`); `--alias-clube` só quando o site grafa o clube de outro modo que o banco (confirme pelo cadastro dos atletas).
- O comando gera `Dados/<ano>/extraidos/etapasHelgaWeb<ano>.json`, congela o SHA-256 da planilha no manifesto e **recusa** qualquer inconsistência, listando os problemas. Categorias `Militar` ficam fora do CCO.
- A apuração (passo 4) mescla sozinha o JSON do banco com o complemento: as etapas do complemento substituem as de mesmo número.

## 4. Executar o Motor de Cálculo e Gerar Relatórios (MD, XLSX e PDF)

```powershell
python src/apurarCampeonato.py --ano 2026 --competicao CCO
```

O `--ano` é obrigatório e define o regulamento aplicado; o comando informa o regulamento e as etapas apuradas (só as presentes no banco). Se alguma etapa do calendário não estiver no JSON extraído, ela **não entra** na apuração: confira com o apurador se a etapa foi cancelada ou se falta o banco dela, pois isso muda o total de etapas realizadas.

O comando gera e atualiza em `Dados/<ano>/resultados/`:
- `resultadoParcialCCO.pdf` (seguindo o layout da FECORI, sem a logo (por ser não oficial) e com "NÃO OFICIAL" à direita do título, destaque em rosa para trocas de categoria e observação de pendências);
- `apuracaoCampeonato<ano>.xlsx` (planilha auditável com abas `resultadoParcial`, `resultadoClubes`, `resultadoIndividual` e `memoriaClubesTop3`);
- `resultadoIndividualCCO.md`.

> **Atenção:** Os relatórios finais `resultadoIndividualCCO.pdf`, `resultadoClubesCCO.pdf` e `resultadoClubesCCO.md` **não podem ser gerados** enquanto a revisão do `resultadoParcialCCO.pdf` pela FECORI não estiver concluída. Somente após a autorização final da FECORI, execute com a flag `--oficial`.

Confira os arquivos gerados em `Dados/<ano>/resultados/` e execute `python .agents/scripts/verificar-projeto.py` antes de propor o commit.

