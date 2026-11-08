---
description: Passo a passo para importar o arquivo .mdb/.accdb de uma etapa, congelar o hash SHA-256, extrair dados higienizados e calcular o campeonato.
---

# Workflow: Apurar Etapa do Campeonato

## 1. Receber o Arquivo do Software de Apuração

Salve o arquivo `.mdb` ou `.accdb` da etapa localmente em `Dados/<ano>/entradas/` (ex.: `Dados/2026/entradas/HelgaDat.mdb`). Na pasta `entradas/` ficam apenas o arquivo `.mdb` e o arquivo Markdown de voluntários (`voluntariosCCO.md`).

## 2. Registrar Voluntários e Árbitros em Markdown

Atualize a tabela em `Dados/<ano>/entradas/voluntariosCCO.md` conforme a relação oficial enviada em até 15 dias (CCO) ou ao término da apuração (CCOS), nos termos do Art. 33, § 4º do Regulamento.

## 3. Extrair Dados Higienizados e Congelar SHA-256

Execute a extração da etapa para gerar o snapshot JSON higienizado em `Dados/<ano>/extraidos/` e mantenha o hash SHA-256 do arquivo bruto em [`Dados/arquivosCongelados.sha256`](../../Dados/arquivosCongelados.sha256):

```powershell
python src/extracaoAccess/extrairHelga.py --mdb "Dados/2026/entradas/HelgaDat.mdb" --saida "Dados/2026/extraidos/etapasHelga2026.json"
```

## 4. Executar o Motor de Cálculo e Gerar Relatórios

```powershell
python src/apurarCampeonato.py --ano 2026 --competicao CCO
```

Confira os relatórios gerados em `Dados/<ano>/resultados/` e execute `python .agents/scripts/verificar-projeto.py` antes de propor o commit.
