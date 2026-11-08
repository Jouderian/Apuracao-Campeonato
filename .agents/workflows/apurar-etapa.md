---
description: Passo a passo para importar o arquivo .mdb/.accdb de uma etapa, congelar o hash SHA-256, extrair dados higienizados e calcular o campeonato.
---

# Workflow: Apurar Etapa ou Ajustar Resultado do Campeonato

Este procedimento deve ser executado:
- **A cada nova etapa apurada** no banco do Helga (`HelgaDat.mdb`);
- **Sempre que novos voluntários ou árbitros forem informados** pelas equipes organizadoras ou pela FECORI;
- **Quando a FECORI demandar ajustes** cadastrais ou de apuração;
- **Todos os anos**, ao iniciar uma nova edição do campeonato.

## 1. Preparar Entradas e Logo da Edição

1. Salve o arquivo `.mdb` ou `.accdb` atualizado localmente em `Dados/<ano>/entradas/` (ex.: `Dados/2026/entradas/HelgaDat.mdb`). Na pasta `entradas/` ficam apenas o arquivo `.mdb` (ignorado pelo Git por LGPD) e o arquivo Markdown de voluntários (`voluntariosCCO.md`).
2. Certifique-se de que a logo oficial da edição esteja em `Dados/<ano>/logoCCO.jpeg` (copiada do repositório `Regulamentos-de-Orientacao/Documentos/<ano>/logoCCO.jpeg`).

## 2. Registrar ou Atualizar Voluntários e Árbitros em Markdown

Atualize a tabela em `Dados/<ano>/entradas/voluntariosCCO.md` conforme a relação oficial enviada em até 15 dias (CCO) ou ao término da apuração (CCOS), nos termos do Art. 33, § 4º do Regulamento. Caso alguma etapa ainda não tenha enviado a lista de voluntários, o relatório parcial indicará automaticamente as etapas pendentes no bloco de `OBSERVAÇÃO`.

## 3. Extrair Dados Higienizados e Congelar SHA-256 (Quando o `.mdb` mudar)

Se o arquivo `.mdb` tiver sido atualizado, execute a extração para gerar o snapshot JSON higienizado em `Dados/<ano>/extraidos/` e atualize o hash SHA-256 em [`Dados/arquivosCongelados.sha256`](../../Dados/arquivosCongelados.sha256):

```powershell
python src/extracaoAccess/extrairHelga.py --mdb "Dados/2026/entradas/HelgaDat.mdb" --saida "Dados/2026/extraidos/etapasHelga2026.json"
```

## 4. Executar o Motor de Cálculo e Gerar Relatórios (MD, XLSX e PDF)

```powershell
python src/apurarCampeonato.py --ano 2026 --competicao CCO
```

O comando gera e atualiza em `Dados/<ano>/resultados/`:
- `resultadoParcialCCO.pdf` (seguindo o layout da FECORI, sem a logo (por ser não oficial) e com "NÃO OFICIAL" à direita do título, destaque em rosa para trocas de categoria e observação de pendências);
- `apuracaoCampeonato<ano>.xlsx` (planilha auditável com abas `resultadoParcial`, `resultadoClubes`, `resultadoIndividual` e `memoriaClubesTop3`);
- `resultadoIndividualCCO.md`.

> **Atenção:** Os relatórios finais `resultadoIndividualCCO.pdf`, `resultadoClubesCCO.pdf` e `resultadoClubesCCO.md` **não podem ser gerados** enquanto a revisão do `resultadoParcialCCO.pdf` pela FECORI não estiver concluída. Somente após a autorização final da FECORI, execute com a flag `--oficial`.

Confira os arquivos gerados em `Dados/<ano>/resultados/` e execute `python .agents/scripts/verificar-projeto.py` antes de propor o commit.

