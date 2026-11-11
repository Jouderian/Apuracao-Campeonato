---
description: Regras gerais de idioma, nomenclatura, SDD, formato de documentos, privacidade (LGPD) e convenções de Git do projeto.
trigger: always_on
---

# Regras Gerais

> Regras de todos os agentes do projeto. Toda regra permanente vive aqui. Os padrões de arquitetura e código ficam em [`code-standards.md`](code-standards.md) e o passo a passo operacional fica em `.agents/workflows/`, lido quando a tarefa o exige.

## Idioma e Nomenclatura

- Documentação, código-fonte (módulos, funções, variáveis, classes), comentários e mensagens de commit em **pt-BR**.
- **Duas zonas de nomenclatura:**
  - **Código e dados do projeto** (`src/`, `Dados/`): **camelCase** em pt-BR (`apurarCampeonato.py`, `motorCalculo/`, `voluntariosCCO.md`).
  - **Configuração e SDD** (`.agents/`): **kebab-case** (`project-vision/spec.md`, `verificar-projeto.py`).
- Exceções canônicas: `AGENTS.md`, `CLAUDE.md`, `README.md`, `LICENSE` e arquivos de teste do `pytest` (`tests/test_*.py`).

## Formato de Documentos e SDD

- Todo `.md` em `.agents/` começa com frontmatter YAML com `description` (resumo de uma linha).
- **Protocolo Spec-Change-First:** nunca implemente ou altere comportamento de cálculo sem que a respectiva `spec.md` exista ou esteja atualizada em `.agents/specs/`.
- **Índice de Specs:** todo `spec.md` tem `status` (`ativa` ou `concluída`) e aparece em [`specs/index.md`](../specs/index.md) com a mesma situação no mesmo commit.
- **ADRs:** decisões de arquitetura, stack ou interpretação de regra esportiva vão para [`.agents/wiki/decisions/`](../wiki/decisions/) (`ADR-<NNN>-<assunto>.md`) e são listadas em [`wiki/index.md`](../wiki/index.md).

## Arquivos de Entrada dos Agentes

- [`AGENTS.md`](../../AGENTS.md) e [`CLAUDE.md`](../../CLAUDE.md), na raiz, são **ponteiros finos** para este arquivo e nunca contêm regra própria.

## Estilo de Resposta ao Usuário

**Escopo:** somente a resposta do agente no chat (não vale para documentos, specs, ADRs ou relatórios gerados).

1. Comece pela resposta ou pela próxima ação: comando, caminho do arquivo ou trecho. Sem preâmbulo.
2. Numere trabalhos com várias etapas, uma ação bem delimitada por etapa.
3. Termine com uma próxima ação que caiba em menos de dois minutos, quando houver.
4. Conclua o problema atual antes de levantar outro.
5. Reafirme o progresso em **uma linha** por turno quando houver plano ativo.
6. Estime **esforço** em unidades concretas. **Fato esportivo ou normativo** (pontuação, colocação, artigo do regulamento, número CBO) nunca se estima: vem dos dados ou do regulamento.
7. Após uma alteração, mostre o que passou a funcionar.
8. Erros: local (`caminho:linha`), causa e correção, em até 3 linhas, sem drama.
9. No máximo 5 itens por lista de julgamento; listas de fatos são completas.
10. Sem recapitulação ou despedida.

## Privacidade (LGPD), Organização de Dados e Auditabilidade

- **Proibido versionar banco bruto com dados pessoais:** arquivos `.mdb` e `.accdb` (e a planilha `exportadoSiteHelga.xlsx`, que recebe o mesmo tratamento) ficam no `.gitignore` para evitar exposição de CPF, RG, endereço, telefone, e-mail ou data de nascimento completa em repositório público.
- **Dados pessoais mínimos:** os `.json` de `Dados/<ano>/extraidos/` não levam data nem ano de nascimento, documento, endereço ou contato; o campo `anoNascimento` é recusado pela validação das entradas ([ADR-003](../wiki/decisions/ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)).
- **Congelamento por SHA-256:** todo arquivo `.mdb`/`.accdb` oficial utilizado na apuração de uma etapa, e a planilha `exportadoSiteHelga.xlsx` quando usada, tem seu hash SHA-256 registrado em [`Dados/arquivosCongelados.sha256`](../../Dados/arquivosCongelados.sha256). Arquivo congelado não pode mudar: hash diferente do registrado recusa a extração.
- **Separação de pastas em `Dados/<ano>/`:**
  - `Dados/<ano>/entradas/`: contém exclusivamente o banco bruto `.mdb`/`.accdb` (local), a planilha de resultados exportada do site do Helga (`exportadoSiteHelga.xlsx`, local; usada só quando o banco de uma etapa se perdeu ou veio sem resultados, conforme [ADR-006](../wiki/decisions/ADR-006-planilha-do-site-helga-como-fonte-complementar.md)) e o arquivo Markdown de voluntários/convocados (`voluntariosCCO.md`), facilitando a auditoria humana.
  - `Dados/<ano>/extraidos/`: armazena os arquivos `.json` higienizados extraídos do banco Access.
  - `Dados/logoFECORI.png` e `Dados/brasoes/<sigla>.png`: logos usadas nos PDFs finais (a da FECORI e o brasão de cada clube, com o nome da sigla em camelCase, ex.: `trilhaNorte.png`), extraídas do resultado de clubes oficial de 2025. A logo da edição fica em `Dados/<ano>/logoCCO.*`.
  - `Dados/<ano>/resultados/`: armazena os relatórios finais calculados (`.md`, `.pdf`, `.xlsx`).

## Resultados Oficiais Publicados

- **O publicado prevalece:** o resultado de uma edição já publicado oficialmente pela FECORI vale mesmo que contenha erro de cálculo; o repositório o reproduz e não o recalcula ([ADR-007](../wiki/decisions/ADR-007-resultado-oficial-publicado-prevalece.md)).
- **Divergências registradas, nunca embutidas:** cada ponto em que o publicado difere do que o regulamento e os dados produziriam fica na seção `Ajustes do Resultado Oficial Publicado` do `voluntariosCCO.md`, uma linha por atleta e etapa, com o valor publicado e o motivo. O motor recusa ajuste que não encontra o atleta, e o relatório sinaliza as células ajustadas.
- **O agente não corrige resultado publicado:** ao achar divergência, lista-a ao usuário; só registra o ajuste com autorização expressa.

## Controle de Pendências

- O que está pendente vive exclusivamente como *issue* do GitHub ([`gestao-issues.md`](../workflows/gestao-issues.md)).
- O agente só abre, altera rótulo ou fecha *issue* com autorização expressa do usuário, apresentando o texto antes.

## Convenções de Git

- [Conventional Commits](https://www.conventionalcommits.org/): `tipo(escopo): descrição`, **escopo obrigatório**. Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `spec`.
- Commit que trata de *issue* leva no rodapé `Refs #N` ou `Closes #N`.
- **Escopos válidos:**

  | Escopo | Quando usar |
  | :--- | :--- |
  | `access` | Extração, conectores e leitura de arquivos `.mdb`/`.accdb` e Markdown de entrada (`src/extracaoAccess/`) |
  | `calculo` | Motor de pontuação, descarte, voluntários, clubes e desempates (`src/motorCalculo/`) |
  | `relatorios` | Geração de saídas Markdown, PDF e Excel (`src/relatorios/`) |
  | `dados` | Entradas em Markdown, extraídos higienizados, resultados por ano e manifesto `arquivosCongelados.sha256` (`Dados/`) |
  | `tests` | Testes automatizados (`tests/`) |
  | `agents` | Artefatos de `.agents/` (regras, specs, workflows, wiki, scripts) |
  | `ci` | Automação e templates em `.github/` |
  | `docs` | `README.md`, `LICENSE` e documentação geral |
  | `root` | Configuração na raiz (`.gitignore`, `.gitattributes`, `pyproject.toml`, `requirements.txt`) |

- **Autoria humana exclusiva:** nenhum rodapé de coautoria ou geração por IA (`Co-Authored-By:`, `Generated with` ou equivalente).
- **Antes do commit:** `python .agents/scripts/verificar-projeto.py` deve passar sem erros.
- **Antes de pedir autorização:** apresente a lista exata de arquivos e a mensagem exata do commit. `git push`, abertura e mesclagem de PR só ocorrem com autorização expressa do usuário ([`atualizar-repositorio.md`](../workflows/atualizar-repositorio.md)).
