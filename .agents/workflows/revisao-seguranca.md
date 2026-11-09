---
description: Ciclo recorrente de revisão de segurança — medir, corrigir, travar no CI, apertar a régua e repetir.
---

# Workflow: Revisão de Segurança Recorrente

Decisão e motivos em [ADR-004](../wiki/decisions/ADR-004-endurecimento-de-seguranca-e-cadeia-de-suprimentos.md). Faça a revisão ao fechar cada etapa do campeonato e ao menos uma vez por mês.

## Automação semanal

Toda segunda-feira, às 06:23 (Brasília), o GitHub executa sozinho o [CI](../../.github/workflows/ci.yml) (`pip-audit`, `mypy`, `ruff`, `bandit`, validação dos extraídos e testes) e o [CodeQL](../../.github/workflows/codeql.yml). Se algum falhar, o GitHub avisa por e-mail. Esse é o passo 1 do ciclo abaixo; os passos 2 a 6 continuam manuais.

Cuidados:
- O GitHub **desativa** execuções agendadas de repositório público sem nenhuma atividade por 60 dias; um commit ou o botão *Enable workflow* em Actions reativa.
- Para rodar na hora: Actions → *Verificação e Testes* → *Run workflow*.
- Um agente em nuvem que também leia alertas e *pull requests* só pode ser criado depois que o GitHub for conectado à conta Claude (https://claude.ai/connect-github).

## 1. Medir

```powershell
pip install -r requirements-dev.txt
python .agents/scripts/verificar-projeto.py
pip-audit -r requirements-dev.txt
```

O primeiro comando instala as ferramentas; o segundo roda SDD, `mypy`, `ruff`, `bandit` e os testes; o terceiro consulta vulnerabilidades conhecidas (precisa de rede). Veja também os alertas do CodeQL e as propostas do Dependabot no GitHub.

## 2. Corrigir

Cada achado vira correção mínima. Se a correção mudar regra de cálculo, siga o *Spec-Change-First* de [`rules.md`](../rules/rules.md).

## 3. Travar

Todo achado corrigido ganha um teste de regressão em `tests/` (ou uma checagem em `verificar-projeto.py`), para que não volte sem o CI avisar. Exemplos já existentes: [`tests/test_seguranca.py`](../../tests/test_seguranca.py) (injeção no PowerShell, dado pessoal no JSON, hash divergente).

## 4. Apertar a régua

Depois de uma rodada sem achados, endureça uma regra: mais categorias no `ruff` (`pyproject.toml`), menos exceções no `mypy`, novos campos proibidos em `validarEntrada.py`. Registre a mudança de política em um ADR.

## 5. Atualizar dependências

Revise e mescle as propostas do Dependabot. Para atualizar à mão:

```powershell
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements.txt requirements.in
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements-dev.txt requirements-dev.in
```

Confira o que mudou em `requirements*.txt` antes do commit: dependência nova que o projeto não usa é sinal de alerta (foi assim com o PyMuPDF 2.x).

## 6. Configurações do GitHub (administrador)

Confirme que continuam ativas: proteção da `main` com revisão obrigatória do `CODEOWNERS`, *secret scanning* com *push protection* e a configuração padrão do CodeQL desligada (o projeto usa [`codeql.yml`](../../.github/workflows/codeql.yml)).
