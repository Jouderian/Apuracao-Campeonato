---
description: Decisão de adotar Python 3.12+ e desacoplar a ingestão do banco Microsoft Access do motor de cálculo por meio de extração higienizada e manifesto SHA-256.
---

# ADR 001: Arquitetura Python e Extração Higienizada do Access

> Registrada em 2026-11-08.

## Contexto
O projeto precisa calcular os resultados individuais e por clubes do Campeonato Cearense de Orientação (CCO e CCOS) a partir de arquivos gerados por software de apuração em Microsoft Access (`.mdb` / `.accdb`). Além disso:
- O repositório no GitHub é **público**, o que exige atenção estrita à LGPD caso os arquivos `.mdb`/`.accdb` contenham dados pessoais de atletas (CPF, endereço, telefone, data de nascimento completa).
- Drivers ODBC do Microsoft Access (`Microsoft Access Database Engine`) são nativos de ambientes Windows, enquanto o GitHub Actions roda preferencialmente em contenedores Linux (`ubuntu-latest`).
- Os demais projetos correlatos do autor (`Regulamentos-de-Orientacao` e `carreira`) já utilizam Python 3.12+ para automação, validação e geração de documentos.

## Decisão
1. **Linguagem:** Adotar **Python 3.12+** como linguagem única do projeto.
2. **Arquitetura em 3 camadas desacopladas (`src/`):**
   - `src/extracaoAccess/`: lê o arquivo `.mdb`/`.accdb` localmente (via `pyodbc` / driver ACE no Windows), calcula o hash SHA-256 do arquivo bruto e exporta um snapshot estruturado e higienizado (sem dados pessoais sensíveis) em `Dados/<ano>/entradas/`.
   - `src/motorCalculo/`: núcleo de funções puras em Python padrão que recebe os dados higienizados das etapas e aplica as regras esportivas dos Arts. 31 a 35 do Regulamento.
   - `src/relatorios/`: gera as tabelas e documentos finais de classificação em Markdown, PDF e Excel.
3. **Proteção LGPD e Congelamento SHA-256:**
   - Os arquivos `.mdb` e `.accdb` são bloqueados no `.gitignore`.
   - O arquivo [`Dados/arquivosCongelados.sha256`](../../../Dados/arquivosCongelados.sha256) registra o hash SHA-256 de cada banco original utilizado, garantindo que qualquer auditoria possa comprovar qual arquivo bruto deu origem à extração.

## Consequências
- **Positivas:**
  * Nenhum dado pessoal sensível de atletas vaza no repositório público.
  * O motor de cálculo e a suíte de testes (`pytest`) rodam em qualquer sistema operacional (Windows, Linux, macOS) e no CI do GitHub Actions em poucos segundos, sem precisar instalar o Microsoft Access no servidor de CI.
  * Os snapshots extraídos em texto (`JSON`/`CSV`) permitem visualizar diffs claros no Git caso haja retificação oficial de súmula após recurso julgado pelo Júri Técnico.
- **Negativas/Atenção:**
  * A etapa inicial de extração do arquivo `.mdb`/`.accdb` exige que o operador tenha o driver ODBC do Microsoft Access instalado na máquina local (ou ferramenta equivalente de leitura de Jet/ACE).
  * É necessário manter sincronizado o hash em `Dados/arquivosCongelados.sha256` sempre que um arquivo de etapa for importado.

