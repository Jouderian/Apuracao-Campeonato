---
description: Passo a passo para importar o arquivo .mdb/.accdb de uma etapa, congelar o hash SHA-256, extrair dados higienizados e calcular o campeonato.
---

# Workflow: Apurar Etapa do Campeonato

## 1. Receber o Arquivo do Software de Apuração

1. Salve o arquivo `.mdb` ou `.accdb` da etapa localmente (ex.: `Dados/2026/entradas/etapa1.mdb`). Como `*.mdb` e `*.accdb` estão no `.gitignore`, o arquivo bruto não será enviado ao GitHub.
2. Caso seja o primeiro arquivo do software ou haja mudança de versão, inspecione o esquema:
   ```powershell
   python src/extracaoAccess/inspecionarBanco.py --arquivo "Dados/2026/entradas/etapa1.mdb"
   ```

## 2. Extrair Dados Higienizados e Congelar SHA-256

Execute a extração da etapa para gerar o snapshot higienizado em `Dados/<ano>/entradas/` e registrar o hash SHA-256 do arquivo bruto em [`Dados/arquivosCongelados.sha256`](../../Dados/arquivosCongelados.sha256).

## 3. Registrar Voluntários e Árbitros da Etapa

Atualize o registro de voluntários e árbitro da etapa em `Dados/<ano>/entradas/` conforme o relatório oficial enviado em até 15 dias (CCO) ou ao término da apuração (CCOS), nos termos do Art. 33, § 4º do Regulamento.

## 4. Executar o Motor de Cálculo e Gerar Relatórios

```powershell
python src/apurarCampeonato.py --ano 2026 --competicao CCO
```

Confira os relatórios gerados em `Dados/<ano>/resultados/` e execute `python .agents/scripts/verificar-projeto.py` antes de propor o commit.

