#!/usr/bin/env python3
"""
Exibe no terminal um resumo consolidado e formatado de todos os resultados da pasta results/:
  1. Metricas de acuracia (TP, FP, FN, Regressoes, TPR, Precisao, FDR, F1) - Vulneravel vs Protegido
  2. Matriz Ferramenta x Vulnerabilidade (OWASP API Top 10)
  3. Comparativo de Forca Bruta (brute-force-*.json)
  4. Latencia e Throughput por rota (latencia-*.csv)
  5. Media de CPU (%) e RAM (MB) por container (recursos-*-carga.csv)

Uso:
    python analysis/visualizar.py
"""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")


def titulo(texto):
    print("\n" + "=" * 88)
    print(f" {texto}")
    print("=" * 88)


def mostrar_csv(caminho, formato_colunas=None):
    if not os.path.exists(caminho):
        print(f"  [arquivo ausente: {caminho}]")
        return
    with open(caminho, encoding="utf-8") as fh:
        linhas = list(csv.reader(fh))
    if not linhas:
        return
    larguras = [max(len(str(linha[i])) for linha in linhas) for i in range(len(linhas[0]))]
    cabecalho = " | ".join(str(val).ljust(larguras[i]) for i, val in enumerate(linhas[0]))
    print("  " + cabecalho)
    print("  " + "-+-".join("-" * l for l in larguras))
    for linha in linhas[1:]:
        print("  " + " | ".join(str(val).ljust(larguras[i]) for i, val in enumerate(linha)))


def mostrar_brute_force():
    titulo("3. RESULTADO DO TESTE DE FORCA BRUTA EM RAJADA (VULN-AUTH-01)")
    for perfil in ("vulneravel", "protegido"):
        p = os.path.join(RESULTS, f"brute-force-{perfil}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            print(f"  Perfil {perfil.upper():10s} -> tentativas={d['attempts']} | "
                  f"status={d['status']} | HTTP 429={d['http_429']} | veredito={d['veredito']}")


def mostrar_recursos():
    titulo("5. CONSUMO MEDIO DE RECURSOS SOB CARGA (CPU % e RAM MiB)")
    for perfil in ("vulneravel", "protegido"):
        p = os.path.join(RESULTS, f"recursos-{perfil}-carga.csv")
        if not os.path.exists(p):
            continue
        cpus = defaultdict(list)
        mems = defaultdict(list)
        with open(p, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cpus[row["container"]].append(float(row["cpu_pct"]))
                mems[row["container"]].append(float(row["mem_mb"]))
        print(f"\n  [Perfil {perfil.upper()}]")
        print(f"  {'Container':22s} | {'CPU Media (%)':14s} | {'CPU Max (%)':12s} | {'RAM Media (MiB)':15s}")
        print("  " + "-" * 72)
        for c in sorted(cpus):
            c_vals, m_vals = cpus[c], mems[c]
            print(f"  {c:22s} | {sum(c_vals)/len(c_vals):14.2f} | {max(c_vals):12.2f} | {sum(m_vals)/len(m_vals):15.1f}")


def main():
    titulo("1. METRICAS DE ACURACIA POR FERRAMENTA (ETAPA B)")
    for perfil in ("vulneravel", "protegido"):
        print(f"\n  >>> Perfil: {perfil.upper()}")
        mostrar_csv(os.path.join(RESULTS, f"metricas-acuracia-{perfil}.csv"))

    titulo("2. MATRIZ FERRAMENTA x VULNERABILIDADE (PERFIL VULNERAVEL)")
    mostrar_csv(os.path.join(RESULTS, "matriz-ferramenta-vulnerabilidade-vulneravel.csv"))

    mostrar_brute_force()

    titulo("4. LATENCIA (ms), THROUGHPUT (RPS) E TAXA DE BLOQUEIO/ERRO (ETAPA C)")
    for perfil in ("vulneravel", "protegido"):
        print(f"\n  >>> Perfil: {perfil.upper()}")
        mostrar_csv(os.path.join(RESULTS, f"latencia-{perfil}.csv"))

    mostrar_recursos()
    print("\n" + "=" * 88)


if __name__ == "__main__":
    main()

