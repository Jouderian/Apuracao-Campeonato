---
description: Procedimento para levar uma mudança à main por PR — branch, verificação do projeto, apresentação ao usuário, PR e mesclagem autorizada.
---

# Workflow: Atualizar Repositório Remoto

Este workflow detalha o fluxo de Git definido em [`rules.md`](../rules/rules.md).

## 1. Criar o Branch

Parta da `main` atualizada. O nome do branch segue `<escopo>/<N>-<resumo>` (ou `<escopo>/<resumo>` quando autorizado):

```powershell
git switch main
git pull
git switch -c calculo/1-motor-pontuacao-etapa
```

### Trabalho em paralelo: um *worktree* por agente

Se outro agente já atua neste diretório, não troque o branch dele: crie um *worktree* próprio ([`rules.md`](../rules/rules.md)) e copie os arquivos ignorados pelo Git de que a tarefa precisa:

```powershell
git worktree add ..\Apuracao-2025 -b dados/2025-ajuste main
Copy-Item Dados\2025\entradas\* ..\Apuracao-2025\Dados\2025\entradas\ -Recurse -Force   # .mdb e .xlsx ignorados
# ao terminar, com o PR mesclado:
git worktree remove ..\Apuracao-2025
```

## 2. Verificar o Projeto e Executar Testes

Antes de propor o commit, execute o verificador do projeto (que valida links, frontmatter, índice de specs e roda a suíte de testes):

```powershell
python .agents/scripts/verificar-projeto.py
```

## 3. Apresentar Alterações ao Usuário

Antes de pedir autorização, apresente claramente ao usuário:
1. A **lista exata** dos arquivos modificados que serão incluídos no commit (`git status --short`).
2. A **mensagem de commit** proposta (em Conventional Commits com escopo obrigatório e sem coautoria de IA).

## 4. Commitar, Enviar e Abrir PR

Após aprovação explícita do usuário, adicione somente os arquivos listados (nunca `git add -A` às cegas):

```powershell
git add <arquivos aprovados>
git commit -m "<mensagem aprovada>"
git push -u origin <branch>
```

## 5. Depois do Merge: Apagar o Branch

Com o PR mesclado, apague o branch local e o remoto e atualize a `main`. Essa limpeza vale por regra ([`rules.md`](../rules/rules.md)) e não precisa de nova autorização:

```powershell
gh pr view <N> --json state          # deve ser MERGED
git switch main
git pull --ff-only
git diff main <branch>               # vazio: o conteúdo já está na main
git branch -D <branch>               # -D porque o merge por rebase muda os hashes
git push origin --delete <branch>
git fetch --prune origin
```

Nunca apague branches de terceiros (Dependabot) nem branches com PR aberto.

