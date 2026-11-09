---
description: Decisão de adotar análise estática (mypy, ruff, bandit), validação das entradas, dependências com hash, GitHub Actions fixadas por SHA e revisão de segurança recorrente.
---

# ADR 004: Endurecimento de segurança e cadeia de suprimentos

> Registrada em 2026-11-09.

## Contexto
Uma análise do projeto (tipos, bandit, ruff, `pip-audit` e leitura do código) encontrou:
- **Injeção de comando no PowerShell:** o caminho do `.mdb` era interpolado em uma string entre aspas duplas; um nome de arquivo com `$(...)` executava comando (reproduzido).
- **Entradas sem validação:** o motor aceitava qualquer JSON, não conferia o `sha256Fonte` contra o manifesto e convertia números de tamanho arbitrário.
- **Verificação estática ausente:** sem `mypy`, `ruff` ou `bandit` no CI, e com 2 erros de tipo e 2 variáveis de laço sem uso no motor.
- **Cadeia de suprimentos frouxa:** dependências sem versão fixa nem hash, Actions por tag móvel, `GITHUB_TOKEN` sem permissão mínima declarada. Além disso, `pymupdf>=1.24.3` já resolvia para a série 2.x, que passou a exigir cerca de dez pacotes que o projeto não usa (`onnxruntime`, `numpy`, `networkx`, `pymupdf-layout` e outros).

## Decisão
1. **Extração segura:** o caminho do banco vai para o PowerShell por variável de ambiente (`CCO_MDB_CAMINHO`), em chaves de escape ODBC, nunca interpolado no script; o executável é o `powershell.exe` do sistema, por caminho absoluto, sem `shell`.
2. **Validação das entradas** em `src/extracaoAccess/validarEntrada.py`, só com a biblioteca padrão: estrutura e tipos do JSON, campos de dados pessoais proibidos ([ADR-003](ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)), textos sem caractere de controle, e `sha256Fonte` igual ao de `Dados/arquivosCongelados.sha256`. A apuração recusa entrada inválida; o `verificar-projeto.py` aplica a mesma validação aos JSON versionados.
3. **Análise estática obrigatória** (`pyproject.toml`): `mypy --strict` em `src/`, `ruff` (E, F, B, S, UP) e `bandit`. Rodam no `verificar-projeto.py` e, portanto, no CI.
4. **Dependências com hash:** `requirements.in` e `requirements-dev.in` guardam as faixas de versão; `requirements.txt` e `requirements-dev.txt` são gerados por `pip-compile --generate-hashes` e instalados com `--require-hashes`. O PyMuPDF fica na série 1.x (`<2`) enquanto a série 2.x exigir pacotes que o projeto não usa.
5. **CI e repositório:** `permissions: contents: read`, Actions fixadas por SHA de commit, `persist-credentials: false`, `pip-audit`, CodeQL semanal e Dependabot (semanal, agrupado) para propor atualizações revisáveis. O `verificar-projeto.py` recusa workflow com Action sem SHA ou sem bloco `permissions`, e dependência sem hash.
6. **Revisão recorrente:** o ciclo medir → corrigir → travar no CI → apertar a régua está descrito em [`revisao-seguranca.md`](../../workflows/revisao-seguranca.md).

## Consequências
- **Positivas:** a vulnerabilidade encontrada deixa de existir e tem teste de regressão; entrada adulterada ou com dado pessoal é recusada antes do cálculo; a cadeia de suprimentos fica fixada, auditável e com atualização revisada.
- **Negativas/Atenção:** quem contribui com código instala também `requirements-dev.txt`; atualizar uma dependência passa a exigir recompilar os arquivos `.txt` (o Dependabot faz isso nas propostas dele); o CodeQL avançado conflita com a "configuração padrão" do CodeQL nas configurações do GitHub, que deve ficar desligada.
- **Fora do código (configurações do GitHub):** proteção da `main` com revisão obrigatória do `CODEOWNERS`, *secret scanning* com *push protection* e commits assinados dependem das configurações do repositório e são aplicados por quem administra o repositório.
