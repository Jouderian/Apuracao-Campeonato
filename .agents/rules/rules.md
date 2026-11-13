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

- **Proibido versionar banco bruto com dados pessoais:** arquivos `.mdb` e `.accdb` ficam no `.gitignore` para evitar exposição de CPF, RG, endereço, telefone, e-mail ou data de nascimento completa em repositório público.
- **Dados pessoais mínimos:** os `.json` de `Dados/<ano>/extraidos/` não levam data nem ano de nascimento, documento, endereço ou contato; o campo `anoNascimento` é recusado pela validação das entradas ([ADR-003](../wiki/decisions/ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)).
- **Congelamento por SHA-256:** todo arquivo `.mdb`/`.accdb` oficial utilizado na apuração de uma etapa, e a planilha `exportadoSiteHelga.xlsx` quando usada, tem seu hash SHA-256 registrado em [`Dados/arquivosCongelados.sha256`](../../Dados/arquivosCongelados.sha256). Arquivo congelado não pode mudar: hash diferente do registrado recusa a extração.
- **Separação de pastas em `Dados/<ano>/`:**
  - `Dados/<ano>/entradas/`: contém exclusivamente o banco bruto `.mdb`/`.accdb` (local, ignorado pelo Git), a planilha de resultados exportada do site do Helga (`exportadoSiteHelga.xlsx`, versionada; usada só quando o banco de uma etapa se perdeu ou veio sem resultados, conforme [ADR-006](../wiki/decisions/ADR-006-planilha-do-site-helga-como-fonte-complementar.md)) e o arquivo Markdown de voluntários/convocados (`voluntariosCCO.md`), facilitando a auditoria humana.
  - `Dados/<ano>/extraidos/`: armazena os arquivos `.json` higienizados extraídos do banco Access.
  - `Dados/logoFECORI.png` e `Dados/brasoes/<sigla>.png`: logos usadas nos PDFs finais (a da FECORI e o brasão de cada clube, com o nome da sigla em camelCase, ex.: `trilhaNorte.png`), extraídas do resultado de clubes oficial de 2025. A logo da edição fica em `Dados/<ano>/logoCCO.*`.
  - `Dados/<ano>/resultados/`: armazena os relatórios finais calculados (`.md`, `.pdf`, `.xlsx`).

## O Regulamento Prevalece

- **Estritamente o regulamento:** a apuração segue o texto do regulamento do ano da edição, a pedido da FECORI ([ADR-008](../wiki/decisions/ADR-008-regulamento-prevalece-sobre-o-publicado.md)). Um resultado já publicado não vincula o repositório: onde difere do que o regulamento e os dados produzem, vale o cálculo do regulamento, que substitui o publicado.
- **Interpretação onde o regulamento é omisso ou ambíguo:** é escolha do apurador, registrada em ADR ou na spec, e a FECORI pode revê-la. Nenhuma interpretação se apoia em "foi assim que se publicou".
- **O agente não decide empate por critério fora do regulamento nem corrige resultado por conta própria:** ao achar ambiguidade ou divergência, lista-a ao usuário. Ajuste por decisão formal da FECORI (seções de ajustes do `voluntariosCCO.md`) só se registra com autorização expressa e referência à decisão.

## Controle de Pendências

- O que está pendente vive exclusivamente como *issue* do GitHub ([`gestao-issues.md`](../workflows/gestao-issues.md)).
- O agente só abre, altera rótulo ou fecha *issue* com autorização expressa do usuário, apresentando o texto antes.

## Trabalho Simultâneo de Agentes

- **Um agente por diretório de trabalho:** dois agentes (ou um agente e o usuário) nunca operam ao mesmo tempo no mesmo diretório. Para trabalho paralelo, cada um usa seu próprio *worktree* (`git worktree add ..\Apuracao-<assunto> -b <branch> main`), com o `.mdb` e o `.xlsx` ignorados pelo Git copiados para ele ([`atualizar-repositorio.md`](../workflows/atualizar-repositorio.md)).
- **Comandos que descartam trabalho:** `git clean`, `git restore .`, `git checkout -- .`, `git reset --hard` e `git stash drop` só atuam sobre arquivos da própria tarefa, e nunca sobre saídas geradas por outro agente. Antes de trocar de branch, o `git status` deve estar limpo ou o que sobra deve ir para um stash nomeado.
- **Commit logo após gerar e conferir:** resultado gerado e verificado vai para commit local no branch de trabalho antes de qualquer outra tarefa, porque o que não está em commit se perde num descarte. O `push` continua dependendo de autorização.

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
- **Depois do merge, apague o branch:** com o PR mesclado (confira `gh pr view <N> --json state`), o agente apaga o branch local e o remoto do PR e atualiza a `main` local, sem precisar de nova autorização. Antes de apagar, confirme que o conteúdo já está na `main` (`git diff main <branch>` vazio); como o merge por *rebase* muda os hashes, o `git branch -d` recusa o branch e se usa `-D` depois dessa conferência. Branches de terceiros (como os do Dependabot) e branches com PR aberto nunca são apagados ([`atualizar-repositorio.md`](../workflows/atualizar-repositorio.md)).
