# -*- coding: utf-8 -*-
"""Validação das entradas do motor de cálculo: estrutura do JSON extraído, dados pessoais proibidos
e conferência do hash SHA-256 do banco de origem contra o manifesto (ADR-003 e ADR-004).

Usa apenas a biblioteca padrão, para não ampliar a cadeia de suprimentos do projeto.
"""
import os
import re
from typing import Any

NOME_MANIFESTO = "arquivosCongelados.sha256"
PADRAO_SHA256 = re.compile(r"^[0-9a-f]{64}$")
TAMANHO_MAXIMO_TEXTO = 200

# Nomes de campo que nunca podem aparecer no JSON versionado (dados pessoais além do mínimo, LGPD).
CAMPOS_PROIBIDOS: frozenset[str] = frozenset({
    "anonascimento", "datanascimento", "nascimento", "birthdate", "yearofbirth", "birthyear",
    "cpf", "rg", "email", "telefone", "phone", "celular", "endereco", "street", "zip", "cep",
})

CAMPOS_ETAPA: dict[str, type | tuple[type, ...]] = {
    "numeroEtapa": int, "competitionId": int,
}
CAMPOS_CLUBE: dict[str, type | tuple[type, ...]] = {
    "clubeId": int, "sigla": str, "nome": str,
}
CAMPOS_PERFIL: dict[str, type | tuple[type, ...]] = {
    "cbo": int, "nome": str, "clubeId": int, "clubeSigla": str, "clubeNome": str,
    "clubeFiliadoCBO": bool,
}
CAMPOS_REGISTRO: dict[str, type | tuple[type, ...]] = {
    "etapa": int, "competitionId": int, "runnerPk": int, "cbo": int, "nome": str,
    "clubeId": int, "clubeSigla": str, "clubeNome": str, "clubeFiliadoCBO": bool,
    "categoria": str, "statusCodigo": int, "statusSigla": str, "classifyYN": bool,
    "tempo": (str, type(None)), "tempoSegundos": (int, type(None)),
}


class EntradaInvalidaError(ValueError):
    """Entrada recusada: o motor de cálculo não deve processá-la."""


def _tipoOk(valor: Any, esperado: type | tuple[type, ...]) -> bool:
    tipos = esperado if isinstance(esperado, tuple) else (esperado,)
    # bool é subclasse de int: só aceita bool onde bool é o tipo esperado.
    if isinstance(valor, bool) and bool not in tipos:
        return False
    return isinstance(valor, tipos)


def _validarCampos(
    origem: str, item: Any, campos: dict[str, type | tuple[type, ...]], erros: list[str],
) -> None:
    if not isinstance(item, dict):
        erros.append(f"{origem}: esperado objeto, recebido {type(item).__name__}")
        return
    for campo, tipo in campos.items():
        if campo not in item:
            erros.append(f"{origem}: campo obrigatório ausente: {campo}")
        elif not _tipoOk(item[campo], tipo):
            erros.append(f"{origem}.{campo}: tipo inválido ({type(item[campo]).__name__})")


def _varrerTextoECampos(origem: str, valor: Any, erros: list[str]) -> None:
    """Recusa campos de dados pessoais proibidos, textos longos e caracteres de controle."""
    if isinstance(valor, dict):
        for chave, sub in valor.items():
            if str(chave).lower() in CAMPOS_PROIBIDOS:
                erros.append(f"{origem}.{chave}: campo de dado pessoal proibido (ADR-003)")
            _varrerTextoECampos(f"{origem}.{chave}", sub, erros)
    elif isinstance(valor, list):
        for i, sub in enumerate(valor):
            _varrerTextoECampos(f"{origem}[{i}]", sub, erros)
    elif isinstance(valor, str):
        if len(valor) > TAMANHO_MAXIMO_TEXTO:
            erros.append(f"{origem}: texto com mais de {TAMANHO_MAXIMO_TEXTO} caracteres")
        if any(ord(c) < 32 for c in valor):
            erros.append(f"{origem}: texto com caractere de controle")


def validarDadosHelga(dados: Any) -> None:
    """Valida o JSON extraído do Helga; levanta EntradaInvalidaError listando todos os problemas."""
    erros: list[str] = []
    if not isinstance(dados, dict):
        raise EntradaInvalidaError("JSON extraído: esperado objeto na raiz")

    if not isinstance(dados.get("fonte"), str) or not dados.get("fonte"):
        erros.append("fonte: texto obrigatório ausente")
    elif os.path.basename(dados["fonte"]) != dados["fonte"]:
        erros.append("fonte: deve ser apenas o nome do arquivo, sem pastas")
    hashFonte = dados.get("sha256Fonte")
    if not isinstance(hashFonte, str) or not PADRAO_SHA256.match(hashFonte):
        erros.append("sha256Fonte: esperado SHA-256 em hexadecimal minúsculo (64 caracteres)")

    for chave, tipo in (("etapas", list), ("clubes", list), ("registrosEtapas", list), ("perfisAtletas", dict)):
        if not isinstance(dados.get(chave), tipo):
            erros.append(f"{chave}: ausente ou com tipo inválido (esperado {tipo.__name__})")
    if erros:
        raise EntradaInvalidaError("; ".join(erros))

    for i, etapa in enumerate(dados["etapas"]):
        _validarCampos(f"etapas[{i}]", etapa, CAMPOS_ETAPA, erros)
    for i, clube in enumerate(dados["clubes"]):
        _validarCampos(f"clubes[{i}]", clube, CAMPOS_CLUBE, erros)
    for cbo, perfil in dados["perfisAtletas"].items():
        _validarCampos(f"perfisAtletas[{cbo}]", perfil, CAMPOS_PERFIL, erros)
    for i, registro in enumerate(dados["registrosEtapas"]):
        _validarCampos(f"registrosEtapas[{i}]", registro, CAMPOS_REGISTRO, erros)
    _varrerTextoECampos("json", dados, erros)

    if not erros:
        etapasConhecidas = {e["numeroEtapa"] for e in dados["etapas"]}
        for i, registro in enumerate(dados["registrosEtapas"]):
            if registro["etapa"] not in etapasConhecidas:
                erros.append(f"registrosEtapas[{i}].etapa: etapa {registro['etapa']} inexistente em etapas")

    if erros:
        resumo = erros[:20]
        if len(erros) > 20:
            resumo.append(f"... e mais {len(erros) - 20} problema(s)")
        raise EntradaInvalidaError("; ".join(resumo))


CAMPOS_PERCURSO: dict[str, type | tuple[type, ...]] = {
    "percursoId": int, "competitionId": int, "numero": int, "nome": str,
    "distanciaM": (int, type(None)), "subidaM": (int, type(None)),
}
CAMPOS_CATEGORIA_PERCURSO: dict[str, type | tuple[type, ...]] = {
    "competitionId": int, "categoriaId": int, "categoria": str, "percursoId": int,
}
CAMPOS_PARTICIPACAO: dict[str, type | tuple[type, ...]] = {
    "competitionId": int, "runnerPk": int, "percursoId": (int, type(None)),
    "horaLargada": (str, type(None)), "horaChegada": (str, type(None)),
}


def validarDadosPercursos(dados: Any) -> None:
    """Valida o JSON de percursos (spec analise-desempenho, Camada A); levanta EntradaInvalidaError."""
    erros: list[str] = []
    if not isinstance(dados, dict):
        raise EntradaInvalidaError("JSON de percursos: esperado objeto na raiz")

    if not isinstance(dados.get("fonte"), str) or not dados.get("fonte"):
        erros.append("fonte: texto obrigatório ausente")
    elif os.path.basename(dados["fonte"]) != dados["fonte"]:
        erros.append("fonte: deve ser apenas o nome do arquivo, sem pastas")
    hashFonte = dados.get("sha256Fonte")
    if not isinstance(hashFonte, str) or not PADRAO_SHA256.match(hashFonte):
        erros.append("sha256Fonte: esperado SHA-256 em hexadecimal minúsculo (64 caracteres)")
    for chave in ("percursos", "categoriaPercurso", "participacoes"):
        if not isinstance(dados.get(chave), list):
            erros.append(f"{chave}: ausente ou com tipo inválido (esperado list)")
    if erros:
        raise EntradaInvalidaError("; ".join(erros))

    for i, percurso in enumerate(dados["percursos"]):
        _validarCampos(f"percursos[{i}]", percurso, CAMPOS_PERCURSO, erros)
    for i, item in enumerate(dados["categoriaPercurso"]):
        _validarCampos(f"categoriaPercurso[{i}]", item, CAMPOS_CATEGORIA_PERCURSO, erros)
    for i, participacao in enumerate(dados["participacoes"]):
        _validarCampos(f"participacoes[{i}]", participacao, CAMPOS_PARTICIPACAO, erros)
    _varrerTextoECampos("json", dados, erros)

    if not erros:
        idsConhecidos = {p["percursoId"] for p in dados["percursos"]}
        for i, item in enumerate(dados["categoriaPercurso"]):
            if item["percursoId"] not in idsConhecidos:
                erros.append(f"categoriaPercurso[{i}].percursoId: percurso {item['percursoId']} inexistente")
        for i, participacao in enumerate(dados["participacoes"]):
            percursoId = participacao["percursoId"]
            if percursoId is not None and percursoId not in idsConhecidos:
                erros.append(f"participacoes[{i}].percursoId: percurso {percursoId} inexistente")

    if erros:
        resumo = erros[:20]
        if len(erros) > 20:
            resumo.append(f"... e mais {len(erros) - 20} problema(s)")
        raise EntradaInvalidaError("; ".join(resumo))


CAMPOS_POSTO: dict[str, type | tuple[type, ...]] = {
    "ordem": int, "codigoPosto": int, "distanciaM": (int, type(None)),
}
CAMPOS_PERCURSO_POSTOS: dict[str, type | tuple[type, ...]] = {"percursoId": int, "postos": list}
CAMPOS_PASSAGEM: dict[str, type | tuple[type, ...]] = {
    "ordem": int, "codigoPosto": int, "tempoParcialSegundos": int,
}
CAMPOS_PARTICIPACAO_PARCIAIS: dict[str, type | tuple[type, ...]] = {
    "competitionId": int, "runnerPk": int, "percursoId": int, "tempoOficialSegundos": int,
    "passagens": list, "postosConferem": bool,
}
CAMPOS_OCORRENCIA: dict[str, type | tuple[type, ...]] = {
    "competitionId": int, "runnerPk": int, "motivo": str,
}


def validarDadosParciais(dados: Any) -> None:
    """Valida o JSON de parciais (spec analise-desempenho, Camada B); levanta EntradaInvalidaError."""
    erros: list[str] = []
    if not isinstance(dados, dict):
        raise EntradaInvalidaError("JSON de parciais: esperado objeto na raiz")

    if not isinstance(dados.get("fonte"), str) or not dados.get("fonte"):
        erros.append("fonte: texto obrigatório ausente")
    elif os.path.basename(dados["fonte"]) != dados["fonte"]:
        erros.append("fonte: deve ser apenas o nome do arquivo, sem pastas")
    hashFonte = dados.get("sha256Fonte")
    if not isinstance(hashFonte, str) or not PADRAO_SHA256.match(hashFonte):
        erros.append("sha256Fonte: esperado SHA-256 em hexadecimal minúsculo (64 caracteres)")
    for chave in ("percursos", "participacoes", "ocorrencias"):
        if not isinstance(dados.get(chave), list):
            erros.append(f"{chave}: ausente ou com tipo inválido (esperado list)")
    if erros:
        raise EntradaInvalidaError("; ".join(erros))

    for i, percurso in enumerate(dados["percursos"]):
        _validarCampos(f"percursos[{i}]", percurso, CAMPOS_PERCURSO_POSTOS, erros)
        if isinstance(percurso, dict) and isinstance(percurso.get("postos"), list):
            for j, posto in enumerate(percurso["postos"]):
                _validarCampos(f"percursos[{i}].postos[{j}]", posto, CAMPOS_POSTO, erros)
    for i, participacao in enumerate(dados["participacoes"]):
        _validarCampos(f"participacoes[{i}]", participacao, CAMPOS_PARTICIPACAO_PARCIAIS, erros)
        if isinstance(participacao, dict) and isinstance(participacao.get("passagens"), list):
            for j, passagem in enumerate(participacao["passagens"]):
                _validarCampos(f"participacoes[{i}].passagens[{j}]", passagem, CAMPOS_PASSAGEM, erros)
    for i, ocorrencia in enumerate(dados["ocorrencias"]):
        _validarCampos(f"ocorrencias[{i}]", ocorrencia, CAMPOS_OCORRENCIA, erros)
    _varrerTextoECampos("json", dados, erros)

    if not erros:
        idsConhecidos = {p["percursoId"] for p in dados["percursos"]}
        for i, participacao in enumerate(dados["participacoes"]):
            if participacao["percursoId"] not in idsConhecidos:
                erros.append(f"participacoes[{i}].percursoId: percurso {participacao['percursoId']} inexistente")

    if erros:
        resumo = erros[:20]
        if len(erros) > 20:
            resumo.append(f"... e mais {len(erros) - 20} problema(s)")
        raise EntradaInvalidaError("; ".join(resumo))


def lerManifestoSha256(caminhoManifesto: str) -> dict[str, str]:
    """Lê o manifesto `<sha256>  <ano>/<arquivo>` e retorna {caminho: hash}."""
    congelados: dict[str, str] = {}
    with open(caminhoManifesto, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            partes = linha.split()
            if len(partes) == 2 and PADRAO_SHA256.match(partes[0]):
                congelados[partes[1]] = partes[0]
    return congelados


def conferirHashNoManifesto(dados: dict[str, Any], ano: int, pastaDados: str) -> None:
    """Exige que o `sha256Fonte` do JSON conste, igual, em Dados/arquivosCongelados.sha256."""
    caminhoManifesto = os.path.join(pastaDados, NOME_MANIFESTO)
    if not os.path.isfile(caminhoManifesto):
        raise EntradaInvalidaError(f"manifesto ausente: {caminhoManifesto}")
    esperado = lerManifestoSha256(caminhoManifesto).get(f"{ano}/{dados['fonte']}")
    if esperado is None:
        raise EntradaInvalidaError(f"{ano}/{dados['fonte']} ausente do manifesto {NOME_MANIFESTO}")
    if esperado != dados["sha256Fonte"]:
        raise EntradaInvalidaError(f"sha256Fonte diverge do manifesto para {ano}/{dados['fonte']}")
