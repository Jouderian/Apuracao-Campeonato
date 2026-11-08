#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verificações automáticas de integridade documental, SDD, LGPD e testes do repositório.

Executado pelo CI (.github/workflows/ci.yml) e localmente antes de qualquer commit:

    python .agents/scripts/verificar-projeto.py
"""
import json
import os
import re
import sys
import unittest
from urllib.parse import unquote

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
problemas = []


def falha(arquivo, linha, msg):
    local = f"{arquivo}:{linha}" if linha else arquivo
    problemas.append(f"{local}: {msg}")


def arquivos_md():
    for raiz, dirs, nomes in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in ('.git', '.github', '__pycache__', '.venv', 'venv', '.pytest_cache')]
        for n in sorted(nomes):
            if n.endswith('.md'):
                caminho = os.path.join(raiz, n)
                yield os.path.relpath(caminho, RAIZ).replace('\\', '/'), caminho


def ler(caminho):
    with open(caminho, encoding='utf-8') as fh:
        return fh.read()


def linha_de(texto, pos):
    return texto.count('\n', 0, pos) + 1


# --------------------------------------------------------------------------
# 1. Links relativos precisam existir; caminhos absolutos são proibidos.
# --------------------------------------------------------------------------
def checar_links(rel, texto):
    base = os.path.dirname(os.path.join(RAIZ, rel))
    for m in re.finditer(r'\[[^\]]*\]\(([^)\s]+)', texto):
        link = m.group(1)
        if link.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        if link.startswith('file:') or re.match(r'^[a-zA-Z]:[\\/]', link):
            falha(rel, linha_de(texto, m.start()), f'caminho absoluto/local em link: {link}')
            continue
        alvo = unquote(link.split('#')[0])
        if alvo and not os.path.exists(os.path.normpath(os.path.join(base, alvo))):
            falha(rel, linha_de(texto, m.start()), f'link relativo inexistente: {link}')


# --------------------------------------------------------------------------
# 2. Frontmatter obrigatório em .agents/ (regra de .agents/rules/rules.md).
# --------------------------------------------------------------------------
def checar_frontmatter(rel, texto):
    if not rel.startswith('.agents/'):
        return
    if not texto.startswith('---'):
        falha(rel, 1, 'arquivo em .agents/ sem YAML frontmatter')
        return
    cabecalho = texto.split('---', 2)[1] if texto.count('---') >= 2 else ''
    if not re.search(r'(?m)^description:\s*\S', cabecalho):
        falha(rel, 1, 'frontmatter sem campo "description" preenchido')


# --------------------------------------------------------------------------
# 3. Índice das specs: toda spec tem status e aparece no índice com ele.
# --------------------------------------------------------------------------
PASTA_SPECS = '.agents/specs'
STATUS_SPEC = ('ativa', 'concluída')


def _status(caminho):
    with open(caminho, encoding='utf-8') as fh:
        inicio = fh.read(2048)
    m = re.match(r'---\n(.*?)\n---', inicio, re.S)
    s = re.search(r'(?m)^status:\s*(\S+)', m.group(1)) if m else None
    return s.group(1) if s else None


def checar_indice_specs(raiz):
    pasta = os.path.join(raiz, PASTA_SPECS)
    indice_rel = f'{PASTA_SPECS}/index.md'
    indice = os.path.join(raiz, indice_rel)
    if not os.path.isfile(indice):
        falha(indice_rel, 0, 'índice das specs ausente')
        return
    linhas = ler(indice).splitlines()
    for nome in sorted(os.listdir(pasta)):
        spec = os.path.join(pasta, nome, 'spec.md')
        if not os.path.isfile(spec):
            continue
        spec_rel = f'{PASTA_SPECS}/{nome}/spec.md'
        status = _status(spec)
        if status not in STATUS_SPEC:
            falha(spec_rel, 1, f'status da spec deve ser "ativa" ou "concluída", não {status!r}')
            continue
        linha = next((l for l in linhas if f']({nome}/spec.md)' in l), None)
        if linha is None:
            falha(indice_rel, 0, f'spec "{nome}" fora do índice')
        elif f'| {status} |' not in linha:
            falha(indice_rel, 0, f'spec "{nome}" com situação divergente: no spec.md é "{status}"')


# --------------------------------------------------------------------------
# 4. Proteção LGPD: nenhum arquivo .mdb ou .accdb deve estar rastreado no Git.
# --------------------------------------------------------------------------
def checar_manifesto_sha256(raiz):
    manifesto_rel = 'Dados/arquivosCongelados.sha256'
    caminho = os.path.join(raiz, manifesto_rel)
    if not os.path.isfile(caminho):
        falha(manifesto_rel, 0, 'manifesto Dados/arquivosCongelados.sha256 ausente')
        return
    padrao = re.compile(r'^[0-9a-f]{64}  \S+$')
    for idx, linha in enumerate(ler(caminho).splitlines(), 1):
        if not linha.strip() or linha.strip().startswith('#'):
            continue
        if not padrao.match(linha):
            falha(manifesto_rel, idx, f'linha fora do formato "<sha256>  <caminho>": {linha[:60]!r}')


# --------------------------------------------------------------------------
# 4b. Origem dos extraídos: o sha256Fonte de cada JSON deve constar no manifesto.
# --------------------------------------------------------------------------
def checar_origem_extraidos(raiz):
    manifesto = os.path.join(raiz, 'Dados', 'arquivosCongelados.sha256')
    if not os.path.isfile(manifesto):
        return
    congelados = {}
    for linha in ler(manifesto).splitlines():
        if linha.strip() and not linha.strip().startswith('#'):
            partes = linha.split()
            if len(partes) == 2:
                congelados[partes[1]] = partes[0]

    pasta_dados = os.path.join(raiz, 'Dados')
    for ano in sorted(os.listdir(pasta_dados)):
        pasta = os.path.join(pasta_dados, ano, 'extraidos')
        if not os.path.isdir(pasta):
            continue
        for nome in sorted(os.listdir(pasta)):
            if not nome.endswith('.json'):
                continue
            rel = f'Dados/{ano}/extraidos/{nome}'
            try:
                with open(os.path.join(pasta, nome), encoding='utf-8') as fh:
                    dados = json.load(fh)
            except (OSError, ValueError) as erro:
                falha(rel, 0, f'JSON ilegível: {erro}')
                continue
            fonte, hash_fonte = dados.get('fonte'), dados.get('sha256Fonte')
            if not fonte or not hash_fonte:
                falha(rel, 0, 'JSON extraído sem "fonte" e "sha256Fonte"')
                continue
            esperado = congelados.get(f'{ano}/{fonte}')
            if esperado is None:
                falha(rel, 0, f'"{ano}/{fonte}" ausente de Dados/arquivosCongelados.sha256')
            elif esperado != hash_fonte:
                falha(rel, 0, f'sha256Fonte diverge do manifesto para {ano}/{fonte}')


# --------------------------------------------------------------------------
# 5. Execução da suíte de testes unitários em tests/.
# --------------------------------------------------------------------------
def rodar_testes(raiz):
    pasta_testes = os.path.join(raiz, 'tests')
    if not os.path.isdir(pasta_testes):
        falha('tests', 0, 'diretório tests/ ausente')
        return 0
    sys.path.insert(0, raiz)
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=pasta_testes, pattern='test_*.py', top_level_dir=raiz)
    runner = unittest.TextTestRunner(verbosity=1)
    resultado = runner.run(suite)
    if not resultado.wasSuccessful():
        falha('tests', 0, f'suíte de testes falhou ({len(resultado.failures)} falhas, {len(resultado.errors)} erros)')
    return resultado.testsRun


def main():
    total_md = 0
    for rel, caminho in arquivos_md():
        total_md += 1
        texto = ler(caminho)
        checar_links(rel, texto)
        checar_frontmatter(rel, texto)

    checar_indice_specs(RAIZ)
    checar_manifesto_sha256(RAIZ)
    checar_origem_extraidos(RAIZ)
    total_testes = rodar_testes(RAIZ)

    print(f'Arquivos Markdown verificados: {total_md} | Testes executados: {total_testes}')
    if problemas:
        print(f'\n{len(problemas)} problema(s) encontrado(s):\n')
        for p in problemas:
            print(f'  - {p}')
        return 1
    print('Nenhum problema encontrado.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

