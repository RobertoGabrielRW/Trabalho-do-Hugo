#!/usr/bin/env python3
"""
Aglutina todos os dados de testes e metricas da pasta results/ (bateria principal +
10 rodadas r1..r10 nos perfis vulneravel e protegido) e gera um unico arquivo Excel
completo com 8 abas e 6 graficos comparativos de alta resolucao:

    results/APISec-Benchmark-Completo.xlsx

Uso:
    python analysis/gerar_excel.py
"""
import csv
import json
import os
import statistics as st
import tempfile
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.abspath(os.path.join(HERE, "..", "results"))
GT_PATH = os.path.join(HERE, "ground_truth.json")
OUT_XLSX = os.path.join(RESULTS_DIR, "APISec-Benchmark-Completo.xlsx")

# Paleta visual consistente
NAVY = "0F2537"
BLUE_HDR = "1E3A8A"
SUB_HDR = "DBEAFE"
ZEBRA = "F8FAFC"
WHITE = "FFFFFF"
GREEN_BG = "DCFCE7"
GREEN_TXT = "166534"
RED_BG = "FEE2E2"
RED_TXT = "991B1B"
AMBER_BG = "FEF3C7"
AMBER_TXT = "92400E"
BORDER_CLR = "CBD5E1"

THIN_SIDE = Side(style="thin", color=BORDER_CLR)
CELL_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

FONT_TITLE = Font(name="Calibri", size=14, bold=True, color=WHITE)
FONT_SUBTITLE = Font(name="Calibri", size=10, italic=True, color="E2E8F0")
FONT_SEC = Font(name="Calibri", size=11, bold=True, color=NAVY)
FONT_TH = Font(name="Calibri", size=10, bold=True, color=WHITE)
FONT_TD = Font(name="Calibri", size=10, color="1E293B")
FONT_TD_BOLD = Font(name="Calibri", size=10, bold=True, color="1E293B")


# ----------------------------------------------------------------- helpers IO
def read_csv_dicts(path):
    """Le um arquivo CSV como lista de dicionarios (retorna [] se ausente)."""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_json_safe(path, default=None):
    """Le um JSON retornando valor padrao se o arquivo nao existir."""
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def to_num(val):
    """Converte string para int ou float quando aplicavel para formatacao numerica no Excel."""
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return val
        try:
            if "." not in s and "e" not in s.lower():
                return int(s)
            return float(s)
        except ValueError:
            return val
    return val


# ----------------------------------------------------------------- helpers Excel
def style_banner(ws, max_col, title, subtitle):
    """Cria faixa de cabecalho executivo nas linhas 1 e 2 da aba."""
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
    c1 = ws.cell(row=1, column=1, value=title)
    c1.font = FONT_TITLE
    c1.fill = PatternFill("solid", fgColor=NAVY)
    c1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 28

    c2 = ws.cell(row=2, column=1, value=subtitle)
    c2.font = FONT_SUBTITLE
    c2.fill = PatternFill("solid", fgColor=BLUE_HDR)
    c2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20


def write_table(ws, start_row, headers, rows, title=None, header_color=NAVY, num_formats=None):
    """Escreve uma tabela formatada com cabecalho, bordas, zebra e formatacao condicional simples."""
    num_formats = num_formats or {}
    r = start_row
    if title:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(headers))
        sc = ws.cell(row=r, column=1, value=title)
        sc.font = FONT_SEC
        sc.fill = PatternFill("solid", fgColor=SUB_HDR)
        sc.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[r].height = 22
        r += 1

    hdr_fill = PatternFill("solid", fgColor=header_color)
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=col_idx, value=h)
        cell.font = FONT_TH
        cell.fill = hdr_fill
        cell.border = CELL_BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[r].height = 24
    header_row = r
    r += 1

    for row_idx, row_vals in enumerate(rows):
        row_fill = PatternFill("solid", fgColor=(WHITE if row_idx % 2 == 0 else ZEBRA))
        for col_idx, raw_val in enumerate(row_vals, start=1):
            val = to_num(raw_val)
            cell = ws.cell(row=r, column=col_idx, value=val)
            cell.font = FONT_TD
            cell.fill = row_fill
            cell.border = CELL_BORDER

            col_name = headers[col_idx - 1]
            if col_name in num_formats and isinstance(val, (int, float)):
                cell.number_format = num_formats[col_name]
            elif isinstance(val, float):
                cell.number_format = "0.000" if abs(val) < 10 else "0.00"

            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            sval = str(val).strip()
            if sval in ("TP", "Exposta", "VULN-AUTH-01", "vulneravel", "INCONSISTENTE"):
                cell.fill = PatternFill("solid", fgColor=RED_BG)
                cell.font = Font(name="Calibri", size=10, bold=True, color=RED_TXT)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif sval in ("Mitigada", "SEM-ACHADO", "protegido", "100% consistente", "0"):
                if col_name in ("Regressoes no Protegido", "Regressoes", "REGRESSOES") or sval != "0":
                    cell.fill = PatternFill("solid", fgColor=GREEN_BG)
                    cell.font = Font(name="Calibri", size=10, bold=True, color=GREEN_TXT)
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            elif sval == "FN":
                cell.fill = PatternFill("solid", fgColor=AMBER_BG)
                cell.font = Font(name="Calibri", size=10, bold=True, color=AMBER_TXT)
                cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[r].height = 19
        r += 1

    return header_row, r


def autofit_columns(ws, min_width=10, max_width=48):
    """Ajusta largura das colunas automaticamente com base no maior conteudo textual."""
    widths = {}
    for row in ws.iter_rows(min_row=3):
        for cell in row:
            if cell.value is None or cell.row in (1, 2):
                continue
            # Ignora celulas mescladas de titulo de secao
            if any(cell.coordinate in rng for rng in ws.merged_cells.ranges):
                continue
            txt = str(cell.value)
            col_idx = cell.column
            widths[col_idx] = max(widths.get(col_idx, min_width), min(len(txt) + 3, max_width))
    for col_idx, w in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w


# ----------------------------------------------------------------- geracao dos 6 graficos
def make_charts(tmpdir, data_bundle):
    """Gera os 6 graficos em PNG de alta resolucao via matplotlib e devolve os caminhos."""
    plt.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 10.5,
        "axes.titleweight": "bold",
        "axes.edgecolor": "#CBD5E1",
        "axes.linewidth": 0.8,
    })
    chart_paths = {}

    # ---------------- Grafico 1: Acuracia (Vulneravel) + Alertas/Regressoes (Protegido)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 4.5), dpi=180)
    acc_vuln = data_bundle["acc_vuln"]
    acc_prot = data_bundle["acc_prot"]
    tools = [r["ferramenta"].upper() for r in acc_vuln]
    x = list(range(len(tools)))
    w = 0.2
    tprs = [float(r["TPR_recall"]) for r in acc_vuln]
    precs = [float(r["precisao"]) for r in acc_vuln]
    fdrs = [float(r["FDR"]) for r in acc_vuln]
    f1s = [float(r["F1"]) for r in acc_vuln]

    b1 = ax1.bar([i - 1.5 * w for i in x], tprs, w, label="TPR (Recall)", color="#1D4ED8")
    b2 = ax1.bar([i - 0.5 * w for i in x], precs, w, label="Precisão", color="#16A34A")
    b3 = ax1.bar([i + 0.5 * w for i in x], fdrs, w, label="FDR (Ruído)", color="#DC2626")
    b4 = ax1.bar([i + 1.5 * w for i in x], f1s, w, label="F1-Score", color="#D97706")
    for bars in (b1, b2, b3, b4):
        for bar in bars:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.02, f"{h:.2f}",
                     ha="center", va="bottom", fontsize=7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(tools)
    ax1.set_ylim(0, 1.32)
    ax1.set_title("Acurácia por Ferramenta (Perfil Vulnerável)", color="#0F2537", fontsize=10)
    ax1.set_ylabel("Score (0 a 1)")
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.legend(fontsize=7.5, loc="upper center", ncol=2)

    # Subplot 2: Alertas totais & Regressoes
    fp_v = [int(r["FP"]) for r in acc_vuln]
    fp_p = [int(r["FP"]) for r in acc_prot]
    reg_p = [int(r["REGRESSOES"]) for r in acc_prot]
    w2 = 0.26
    bv = ax2.bar([i - w2 for i in x], fp_v, w2, label="FP (Vulnerável)", color="#EF4444")
    bp = ax2.bar(x, fp_p, w2, label="FP (Protegido)", color="#3B82F6")
    br = ax2.bar([i + w2 for i in x], reg_p, w2, label="Regressões (Protegido)", color="#16A34A")
    for bars in (bv, bp, br):
        for bar in bars:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2, h + 2.5, f"{int(h)}",
                     ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(tools)
    ax2.set_ylim(0, max(fp_v + [10]) * 1.22)
    ax2.set_title("Falsos Positivos e Regressões", color="#0F2537", fontsize=10)
    ax2.set_ylabel("Contagem de Alertas")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.legend(fontsize=7.5, loc="upper right")

    fig.suptitle("Gráfico 1 — Eficácia de Detecção (Etapa B) e Controle de Regressões",
                 fontsize=11.5, fontweight="bold", color="#0F2537", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p1 = os.path.join(tmpdir, "chart1_acuracia.png")
    fig.savefig(p1)
    plt.close(fig)
    chart_paths["c1"] = p1

    # ---------------- Grafico 2: Consistencia das 10 Vulnerabilidades nas 10 Rodadas
    fig, ax = plt.subplots(figsize=(9.4, 4.5), dpi=180)
    v_ids = data_bundle["vuln_ids"]
    v_exp = data_bundle["vuln_exposed_counts"]
    p_mit = data_bundle["vuln_mitigated_counts"]
    y_pos = list(range(len(v_ids)))
    h_bar = 0.36
    b_exp = ax.barh([y - h_bar / 2 for y in y_pos], v_exp, h_bar,
                    label="Rodadas Expostas — Perfil Vulnerável", color="#DC2626")
    b_mit = ax.barh([y + h_bar / 2 for y in y_pos], p_mit, h_bar,
                    label="Rodadas Mitigadas — Perfil Protegido", color="#16A34A")
    for bar in b_exp:
        w_val = bar.get_width()
        ax.text(w_val + 0.15, bar.get_y() + bar.get_height() / 2, f"{int(w_val)}/10",
                va="center", fontsize=7.5, color="#991B1B", fontweight="bold")
    for bar in b_mit:
        w_val = bar.get_width()
        ax.text(w_val + 0.15, bar.get_y() + bar.get_height() / 2, f"{int(w_val)}/10 (0 reg.)",
                va="center", fontsize=7.5, color="#166534", fontweight="bold")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(v_ids, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 12.2)
    ax.set_xlabel("Quantidade de Rodadas Confirmadas (de 10)")
    ax.set_title("Gráfico 2 — Consistência das 10 Vulnerabilidades OWASP API Top 10 (10 Rodadas)",
                 color="#0F2537", pad=26)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=8)
    fig.tight_layout()
    p2 = os.path.join(tmpdir, "chart2_consistencia.png")
    fig.savefig(p2)
    plt.close(fig)
    chart_paths["c2"] = p2

    # ---------------- Grafico 3: Brute Force r1..r10 (HTTP 401 vs HTTP 429)
    fig, ax = plt.subplots(figsize=(9.4, 4.5), dpi=180)
    rounds = [f"r{i}" for i in range(1, 11)]
    bf_v_401 = data_bundle["bf_rounds"]["vulneravel"]["401"]
    bf_v_429 = data_bundle["bf_rounds"]["vulneravel"]["429"]
    bf_p_401 = data_bundle["bf_rounds"]["protegido"]["401"]
    bf_p_429 = data_bundle["bf_rounds"]["protegido"]["429"]

    ax.plot(rounds, bf_v_401, marker="o", linewidth=2.2, color="#DC2626",
            label="Vulnerável — HTTP 401 (Sem bloqueio)")
    ax.plot(rounds, bf_v_429, marker="x", linestyle="--", linewidth=1.8, color="#991B1B",
            label="Vulnerável — HTTP 429 (0 bloqueios)")
    ax.plot(rounds, bf_p_401, marker="s", linewidth=2.0, color="#F59E0B",
            label="Protegido — HTTP 401 (Antes do burst)")
    ax.plot(rounds, bf_p_429, marker="^", linewidth=2.3, color="#16A34A",
            label="Protegido — HTTP 429 (Bloqueio Rate Limit)")
    for i, val in enumerate(bf_p_429):
        ax.annotate(f"{val}", (rounds[i], val), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=7.5, color="#166534", fontweight="bold")
    ax.set_ylim(-6, 118)
    ax.set_xlabel("Rodada Experimental")
    ax.set_ylabel("Respostas (em 100 tentativas paralelas)")
    ax.set_title("Gráfico 3 — Força Bruta em Rajada nas 10 Rodadas (VULN-AUTH-01)",
                 color="#0F2537", pad=40)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=7.8, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2)
    fig.tight_layout()
    p3 = os.path.join(tmpdir, "chart3_bruteforce.png")
    fig.savefig(p3)
    plt.close(fig)
    chart_paths["c3"] = p3

    # ---------------- Grafico 4: Latencia por Rota (p50, p90, p95, p99 - Media +- DP)
    fig, ax = plt.subplots(figsize=(9.4, 4.5), dpi=180)
    routes = ["GET /api/products", "GET /api/products/search?q=roteador&order=name", "GET /api/orders/1"]
    short_routes = ["/products", "/search", "/orders/1"]
    pct_keys = ["p50_ms", "p90_ms", "p95_ms", "p99_ms"]
    pct_lbls = ["p50", "p90", "p95", "p99"]

    x_labels = []
    v_means, v_stds = [], []
    p_means, p_stds = [], []
    lat_stats = data_bundle["lat_stats"]
    for sr, rfull in zip(short_routes, routes):
        for pk, pl in zip(pct_keys, pct_lbls):
            x_labels.append(f"{sr}\n{pl}")
            vm, vs = lat_stats["vulneravel"][rfull][pk]
            pm, ps = lat_stats["protegido"][rfull][pk]
            v_means.append(vm); v_stds.append(vs)
            p_means.append(pm); p_stds.append(ps)

    xi = list(range(len(x_labels)))
    w3 = 0.36
    ax.bar([i - w3 / 2 for i in xi], v_means, w3, yerr=v_stds, capsize=3,
           label="Vulnerável (Média ± DP)", color="#DC2626", alpha=0.88)
    ax.bar([i + w3 / 2 for i in xi], p_means, w3, yerr=p_stds, capsize=3,
           label="Protegido (Média ± DP)", color="#2563EB", alpha=0.88)
    ax.set_xticks(xi)
    ax.set_xticklabels(x_labels, fontsize=7.6)
    ax.set_ylabel("Latência do Cliente (ms)")
    ax.set_title("Gráfico 4 — Latência por Rota e Percentil nas 10 Rodadas (Vulnerável vs. Protegido)",
                 color="#0F2537")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(fontsize=8.5, loc="upper left")
    fig.tight_layout()
    p4 = os.path.join(tmpdir, "chart4_latencia.png")
    fig.savefig(p4)
    plt.close(fig)
    chart_paths["c4"] = p4

    # ---------------- Grafico 5: Throughput (RPS) e Taxa de Bloqueio (erro_pct) r1..r10
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 4.5), dpi=180)
    rps_v = data_bundle["rps_rounds"]["vulneravel"]
    rps_p = data_bundle["rps_rounds"]["protegido"]
    err_v = data_bundle["err_rounds"]["vulneravel"]
    err_p = data_bundle["err_rounds"]["protegido"]

    ax1.plot(rounds, rps_v, marker="o", linewidth=2.0, color="#DC2626", label="Vulnerável")
    ax1.plot(rounds, rps_p, marker="s", linewidth=2.0, color="#2563EB", label="Protegido")
    ax1.set_ylim(280, 420)
    ax1.set_xlabel("Rodada")
    ax1.set_ylabel("Throughput (req/s)")
    ax1.set_title("Throughput (RPS) por Rodada", color="#0F2537", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(fontsize=8)

    ax2.plot(rounds, err_v, marker="o", linewidth=2.0, color="#DC2626", label="Vulnerável (0% bloqueio)")
    ax2.plot(rounds, err_p, marker="^", linewidth=2.2, color="#16A34A", label="Protegido (HTTP 429 Gateway)")
    for i, val in enumerate(err_p):
        ax2.annotate(f"{val:.1f}%", (rounds[i], val), textcoords="offset points", xytext=(0, -12),
                     ha="center", fontsize=7, color="#166534", fontweight="bold")
    ax2.set_ylim(-5, 105)
    ax2.set_xlabel("Rodada")
    ax2.set_ylabel("Taxa de Rejeição / Bloqueio (%)")
    ax2.set_title("Taxa de Bloqueio por Rate Limit (%)", color="#0F2537", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(fontsize=8, loc="center")

    fig.suptitle("Gráfico 5 — Estabilidade de Vazão (RPS) e Bloqueio na Borda ao Longo das 10 Rodadas",
                 fontsize=11, fontweight="bold", color="#0F2537", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p5 = os.path.join(tmpdir, "chart5_throughput_bloqueio.png")
    fig.savefig(p5)
    plt.close(fig)
    chart_paths["c5"] = p5

    # ---------------- Grafico 6: Consumo de Recursos CPU (%) e RAM (MiB) por Container
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 4.5), dpi=180)
    res_stats = data_bundle["res_stats"]
    containers = ["apisec-gateway", "apisec-target", "apisec-redis", "apisec-keycloak",
                  "apisec-cadvisor", "apisec-grafana", "apisec-prometheus"]
    short_c = [c.replace("apisec-", "") for c in containers]
    xc = list(range(len(containers)))
    wc = 0.36

    cpu_vm = [res_stats["vulneravel"][c]["cpu"][0] for c in containers]
    cpu_vs = [res_stats["vulneravel"][c]["cpu"][1] for c in containers]
    cpu_pm = [res_stats["protegido"][c]["cpu"][0] for c in containers]
    cpu_ps = [res_stats["protegido"][c]["cpu"][1] for c in containers]

    mem_vm = [res_stats["vulneravel"][c]["mem"][0] for c in containers]
    mem_vs = [res_stats["vulneravel"][c]["mem"][1] for c in containers]
    mem_pm = [res_stats["protegido"][c]["mem"][0] for c in containers]
    mem_ps = [res_stats["protegido"][c]["mem"][1] for c in containers]

    ax1.bar([i - wc / 2 for i in xc], cpu_vm, wc, yerr=cpu_vs, capsize=2,
            label="Vulnerável", color="#DC2626", alpha=0.88)
    ax1.bar([i + wc / 2 for i in xc], cpu_pm, wc, yerr=cpu_ps, capsize=2,
            label="Protegido", color="#2563EB", alpha=0.88)
    ax1.set_xticks(xc)
    ax1.set_xticklabels(short_c, rotation=25, ha="right", fontsize=8)
    ax1.set_ylabel("CPU Média (%)")
    ax1.set_title("Uso de CPU por Container (Média ± DP)", color="#0F2537", fontsize=10)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.legend(fontsize=7.5)

    ax2.bar([i - wc / 2 for i in xc], mem_vm, wc, yerr=mem_vs, capsize=2,
            label="Vulnerável", color="#DC2626", alpha=0.88)
    ax2.bar([i + wc / 2 for i in xc], mem_pm, wc, yerr=mem_ps, capsize=2,
            label="Protegido", color="#2563EB", alpha=0.88)
    ax2.set_xticks(xc)
    ax2.set_xticklabels(short_c, rotation=25, ha="right", fontsize=8)
    ax2.set_ylabel("RAM Residente Média (MiB)")
    ax2.set_title("RAM Residente por Container (MiB)", color="#0F2537", fontsize=10)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.legend(fontsize=7.5)

    fig.suptitle("Gráfico 6 — Consumo de Recursos Computacionais sob Carga (10 Rodadas)",
                 fontsize=11, fontweight="bold", color="#0F2537", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p6 = os.path.join(tmpdir, "chart6_recursos.png")
    fig.savefig(p6)
    plt.close(fig)
    chart_paths["c6"] = p6

    return chart_paths


# ----------------------------------------------------------------- coleta dos dados
def collect_all_data():
    gt = read_json_safe(GT_PATH, {"injected": []}).get("injected", [])
    acc_vuln = read_csv_dicts(os.path.join(RESULTS_DIR, "metricas-acuracia-vulneravel.csv"))
    acc_prot = read_csv_dicts(os.path.join(RESULTS_DIR, "metricas-acuracia-protegido.csv"))
    mat_vuln = read_csv_dicts(os.path.join(RESULTS_DIR, "matriz-ferramenta-vulnerabilidade-vulneravel.csv"))
    mat_prot = read_csv_dicts(os.path.join(RESULTS_DIR, "matriz-ferramenta-vulnerabilidade-protegido.csv"))
    rel10 = read_csv_dicts(os.path.join(RESULTS_DIR, "relatorio-10-rodadas.csv"))
    rodadas_det = read_json_safe(os.path.join(RESULTS_DIR, "rodadas-detalhadas.json"), {})

    vuln_ids = [g["id"] for g in gt]
    vuln_exposed_counts = []
    vuln_mitigated_counts = []
    for vid in vuln_ids:
        v_cnt = sum(
            1 for r in rodadas_det.get("vulneravel", [])
            for item in r.get("vulns", []) if item.get("id") == vid and item.get("vulnerable")
        )
        p_cnt = sum(
            1 for r in rodadas_det.get("protegido", [])
            for item in r.get("vulns", []) if item.get("id") == vid and not item.get("vulnerable")
        )
        vuln_exposed_counts.append(v_cnt)
        vuln_mitigated_counts.append(p_cnt)

    # Brute force (principal + r1..r10)
    bf_rows = []
    bf_rounds = {"vulneravel": {"401": [], "429": []}, "protegido": {"401": [], "429": []}}
    for prof in ("vulneravel", "protegido"):
        # principal
        fname = f"brute-force-{prof}.json"
        d = read_json_safe(os.path.join(RESULTS_DIR, fname), None)
        if d:
            st_map = d.get("status", {})
            bf_rows.append([fname, prof, "principal", d.get("attempts", 0),
                            st_map.get("0", 0), st_map.get("401", 0),
                            d.get("http_429", 0), d.get("veredito", ""), d.get("achado") or "-"])
        for i in range(1, 11):
            rid = f"r{i}"
            fname_r = f"brute-force-{prof}-{rid}.json"
            dr = read_json_safe(os.path.join(RESULTS_DIR, fname_r), None)
            if dr:
                st_map = dr.get("status", {})
                c401 = int(st_map.get("401", 0))
                c429 = int(dr.get("http_429", 0))
                bf_rounds[prof]["401"].append(c401)
                bf_rounds[prof]["429"].append(c429)
                bf_rows.append([fname_r, prof, rid, dr.get("attempts", 0),
                                st_map.get("0", 0), c401, c429,
                                dr.get("veredito", ""), dr.get("achado") or "-"])

    # Latencia (principal + r1..r10)
    lat_rows = []
    lat_stats = {"vulneravel": defaultdict(dict), "protegido": defaultdict(dict)}
    rps_rounds = {"vulneravel": [], "protegido": []}
    err_rounds = {"vulneravel": [], "protegido": []}
    for prof in ("vulneravel", "protegido"):
        fname = f"latencia-{prof}.csv"
        for row in read_csv_dicts(os.path.join(RESULTS_DIR, fname)):
            lat_rows.append([fname, prof, "principal", row["rota"], row["n"],
                             row["p50_ms"], row["p90_ms"], row["p95_ms"], row["p99_ms"],
                             row["media_ms"], row["throughput_rps"], row["erro_pct"]])
        per_route_vals = defaultdict(lambda: defaultdict(list))
        for i in range(1, 11):
            rid = f"r{i}"
            fname_r = f"latencia-{prof}-{rid}.csv"
            rows_r = read_csv_dicts(os.path.join(RESULTS_DIR, fname_r))
            r_rps, r_err = [], []
            for row in rows_r:
                lat_rows.append([fname_r, prof, rid, row["rota"], row["n"],
                                 row["p50_ms"], row["p90_ms"], row["p95_ms"], row["p99_ms"],
                                 row["media_ms"], row["throughput_rps"], row["erro_pct"]])
                for k in ("p50_ms", "p90_ms", "p95_ms", "p99_ms", "media_ms", "throughput_rps", "erro_pct"):
                    per_route_vals[row["rota"]][k].append(float(row[k]))
                r_rps.append(float(row["throughput_rps"]))
                r_err.append(float(row["erro_pct"]))
            rps_rounds[prof].append(st.mean(r_rps) if r_rps else 0.0)
            err_rounds[prof].append(st.mean(r_err) if r_err else 0.0)
        for rota, metrics_d in per_route_vals.items():
            for k, vals in metrics_d.items():
                lat_stats[prof][rota][k] = (st.mean(vals), st.pstdev(vals) if len(vals) > 1 else 0.0)

    # Recursos (principal + r1..r10)
    res_raw_rows = []
    res_summary_rows = []
    res_stats = {"vulneravel": defaultdict(dict), "protegido": defaultdict(dict)}
    for prof in ("vulneravel", "protegido"):
        round_means = defaultdict(lambda: {"cpu": [], "mem": []})
        for rid_label, fname in [("principal", f"recursos-{prof}-carga.csv")] + [
            (f"r{i}", f"recursos-{prof}-carga-r{i}.csv") for i in range(1, 11)
        ]:
            rows_res = read_csv_dicts(os.path.join(RESULTS_DIR, fname))
            per_c_cpu = defaultdict(list)
            per_c_mem = defaultdict(list)
            for row in rows_res:
                res_raw_rows.append([fname, prof, rid_label, row["timestamp"],
                                     row["container"], row["cpu_pct"], row["mem_mb"]])
                per_c_cpu[row["container"]].append(float(row["cpu_pct"]))
                per_c_mem[row["container"]].append(float(row["mem_mb"]))
            for c in sorted(per_c_cpu):
                mc = st.mean(per_c_cpu[c])
                mm = st.mean(per_c_mem[c])
                res_summary_rows.append([prof, rid_label, c, len(per_c_cpu[c]),
                                         round(mc, 2), round(max(per_c_cpu[c]), 2), round(mm, 1)])
                if rid_label != "principal":
                    round_means[c]["cpu"].append(mc)
                    round_means[c]["mem"].append(mm)
        for c, dvals in round_means.items():
            res_stats[prof][c]["cpu"] = (st.mean(dvals["cpu"]), st.pstdev(dvals["cpu"]))
            res_stats[prof][c]["mem"] = (st.mean(dvals["mem"]), st.pstdev(dvals["mem"]))

    # ZAP alertas agrupados & Postman findings
    zap_summary_rows = []
    for prof in ("vulneravel", "protegido"):
        zdata = read_json_safe(os.path.join(RESULTS_DIR, f"zap-{prof}.json"), {})
        sites = zdata.get("site", zdata.get("@site", []))
        if isinstance(sites, dict):
            sites = [sites]
        for site in sites:
            for al in site.get("alerts", []):
                insts = al.get("instances", []) or []
                zap_summary_rows.append([
                    prof, al.get("pluginid", al.get("pluginId", "")),
                    al.get("name", al.get("alert", "")),
                    al.get("riskdesc", al.get("riskcode", "")),
                    len(insts),
                    al.get("cweid", ""),
                ])

    postman_rows = []
    for prof in ("vulneravel", "protegido"):
        arr = read_json_safe(os.path.join(RESULTS_DIR, f"postman-findings-{prof}.json"), [])
        for item in arr:
            postman_rows.append([
                prof, item.get("tool", "postman"), item.get("id", ""),
                item.get("route", ""), item.get("class", ""), item.get("severity", "")
            ])

    # Telemetria Prometheus
    prom_raw_rows = []
    prom_grp = defaultdict(list)
    for prof in ("vulneravel", "protegido"):
        for row in read_csv_dicts(os.path.join(RESULTS_DIR, f"telemetria-{prof}.csv")):
            val = float(row["valor"])
            prom_raw_rows.append([prof, row["metrica"], row["serie"], row["timestamp"], val])
            prom_grp[(prof, row["metrica"], row["serie"])].append(val)
    prom_summary_rows = []
    for (prof, met, ser), vals in sorted(prom_grp.items()):
        prom_summary_rows.append([
            prof, met, ser, len(vals),
            round(st.mean(vals), 4),
            round(st.pstdev(vals) if len(vals) > 1 else 0.0, 4),
            round(min(vals), 4),
            round(max(vals), 4),
        ])

    return {
        "gt": gt,
        "acc_vuln": acc_vuln,
        "acc_prot": acc_prot,
        "mat_vuln": mat_vuln,
        "mat_prot": mat_prot,
        "rel10": rel10,
        "rodadas_det": rodadas_det,
        "vuln_ids": vuln_ids,
        "vuln_exposed_counts": vuln_exposed_counts,
        "vuln_mitigated_counts": vuln_mitigated_counts,
        "bf_rows": bf_rows,
        "bf_rounds": bf_rounds,
        "lat_rows": lat_rows,
        "lat_stats": lat_stats,
        "rps_rounds": rps_rounds,
        "err_rounds": err_rounds,
        "res_raw_rows": res_raw_rows,
        "res_summary_rows": res_summary_rows,
        "res_stats": res_stats,
        "zap_summary_rows": zap_summary_rows,
        "postman_rows": postman_rows,
        "prom_raw_rows": prom_raw_rows,
        "prom_summary_rows": prom_summary_rows,
    }


# ----------------------------------------------------------------- montagem do Excel
def build_workbook():
    data = collect_all_data()
    wb = openpyxl.Workbook()

    with tempfile.TemporaryDirectory() as tmpdir:
        charts = make_charts(tmpdir, data)

        # =====================================================================
        # ABA 1: Resumo_e_Graficos
        # =====================================================================
        ws1 = wb.active
        ws1.title = "Resumo_e_Graficos"
        ws1.views.sheetView[0].showGridLines = True
        style_banner(
            ws1, 18,
            "APISec Testbed — Dashboard Consolidado de Resultados e Gráficos",
            "Unifesspa • Benchmarking Empírico de Segurança de APIs (Bateria Principal + 10 Rodadas r1..r10: Vulnerável vs. Protegido)"
        )

        kpis = [
            ["Cobertura de Vulnerabilidades (OWASP API Top 10)", "10 falhas injetadas", "10/10 expostas no Vulnerável; 10/10 mitigadas no Protegido (0 regressões)", "100% consistente"],
            ["OWASP ZAP (DAST Caixa-Preta)", "TPR=0.400 | FP=165 (Vuln.)", "FP reduzido para 17 no Protegido; 0 regressões (F1=0.023 no Vuln.)", "Foco sintático"],
            ["Postman / Newman (Lógica e Autorização)", "TPR=1.000 | F1=1.000", "Detectou 5/5 falhas de lógica no Vulnerável e 0 alertas no Protegido", "100% preciso"],
            ["Força Bruta em Rajada (10 rodadas × 100 req)", "401: 100.0 ± 0.0 (Vuln.)", "Protegido barrou 50.9 ± 11.8 req com HTTP 429 (10/10 SEM-ACHADO)", "100% consistente"],
            ["Latência p50 / Throughput (10 rodadas)", "90.8–93.4 ms | 348.9 RPS", "Protegido: 75.0–75.5 ms | 357.4 RPS (~91.2% bloqueadas no Gateway)", "Rate Limit na borda"],
            ["CPU Média Target Service (10 rodadas)", "34.23% ± 20.92% (Vuln.)", "26.96% ± 14.65% no Protegido (alívio de CPU pela filtragem na borda)", "Menor carga no SUT"],
        ]
        write_table(
            ws1, 4,
            ["Dimensão Avaliada", "Perfil VULNERÁVEL", "Perfil PROTEGIDO / Comparativo", "Conclusão"],
            kpis,
            title="Resumo Executivo do Experimento (Aglutinação Completa)",
        )
        # Ajusta larguras da Aba 1 para acomodar bem a tabela (A..D) e os 2 graficos lado a lado (A..Q)
        ws1.column_dimensions["A"].width = 38
        ws1.column_dimensions["B"].width = 24
        ws1.column_dimensions["C"].width = 56
        ws1.column_dimensions["D"].width = 22
        for col_idx in range(5, 19):
            ws1.column_dimensions[get_column_letter(col_idx)].width = 11

        # Insere os 6 graficos em grade 2x3 limpa sem sobreposicao
        placements = [
            ("c1", "A14"),
            ("c2", "J14"),
            ("c3", "A38"),
            ("c4", "J38"),
            ("c5", "A62"),
            ("c6", "J62"),
        ]
        for key, anchor in placements:
            img = XLImage(charts[key])
            img.width = 680
            img.height = 330
            ws1.add_image(img, anchor)

        # =====================================================================
        # ABA 2: Matriz_OWASP_e_Consistencia
        # =====================================================================
        ws2 = wb.create_sheet("Matriz_OWASP_e_Consistencia")
        style_banner(
            ws2, 11,
            "Matriz OWASP API Top 10 × Ferramentas e Consistência nas 10 Rodadas",
            "Cruzamento entre ground_truth.json, matriz-ferramenta-vulnerabilidade-*.csv e rodadas-detalhadas.json"
        )
        mv_map = {r["vuln_id"]: r for r in data["mat_vuln"]}
        mp_map = {r["vuln_id"]: r for r in data["mat_prot"]}
        rows_mat = []
        for idx, g in enumerate(data["gt"]):
            vid = g["id"]
            mv = mv_map.get(vid, {})
            mp = mp_map.get(vid, {})
            rows_mat.append([
                vid, g["owasp"], g["cwe"], g["class"], g["route"],
                ", ".join(g.get("detectable_by", [])),
                mv.get("zap", "-"), mv.get("postman", "-"), mv.get("brute", "-"),
                f"{data['vuln_exposed_counts'][idx]}/10",
                f"{data['vuln_mitigated_counts'][idx]}/10 (Reg={10 - data['vuln_mitigated_counts'][idx]})",
            ])
        _, next_r = write_table(
            ws2, 4,
            ["Vuln ID", "OWASP", "CWE", "Classe", "Rota", "Detectável Por",
             "ZAP (Vuln)", "Postman (Vuln)", "Brute (Vuln)",
             "Exposta (Vuln 10x)", "Mitigada (Prot 10x)"],
            rows_mat,
            title="1. Gabarito Oficial e Cobertura por Ferramenta + Taxa de Consistência (10 Rodadas)",
        )

        # Tabela 2 na Aba 2: Resultado individual rodada a rodada
        rows_r_detail = []
        for prof in ("vulneravel", "protegido"):
            for r_obj in data["rodadas_det"].get(prof, []):
                rid = r_obj["round"]
                for v in r_obj.get("vulns", []):
                    estado = "Exposta" if v["vulnerable"] else "Mitigada"
                    rows_r_detail.append([prof, rid, v["id"], v["http_status"], estado, v["detail"]])
        write_table(
            ws2, next_r + 1,
            ["Perfil", "Rodada", "Vuln ID", "HTTP Status", "Estado Observado", "Evidência / Detalhe"],
            rows_r_detail,
            title="2. Verificação Individual Rodada a Rodada (r1 a r10 nos dois perfis)",
        )
        ws2.freeze_panes = "A6"
        autofit_columns(ws2)

        # =====================================================================
        # ABA 3: Metricas_Acuracia
        # =====================================================================
        ws3 = wb.create_sheet("Metricas_Acuracia")
        style_banner(
            ws3, 11,
            "Métricas de Acurácia (Etapa B) e Achados Brutos (Postman / OWASP ZAP)",
            "Consolidação de metricas-acuracia-*.csv, postman-findings-*.json e zap-*.json"
        )
        acc_rows = []
        for r in data["acc_vuln"] + data["acc_prot"]:
            acc_rows.append([
                r["ferramenta"], r["perfil"], r["TP"], r["FP"], r["FN"],
                r["REGRESSOES"], r["TPR_recall"], r["precisao"], r["FDR"], r["F1"], r["n_alertas"]
            ])
        _, next_r = write_table(
            ws3, 4,
            ["Ferramenta", "Perfil", "TP", "FP", "FN", "REGRESSOES",
             "TPR (Recall)", "Precisão", "FDR", "F1-Score", "Nº Alertas"],
            acc_rows,
            title="1. Métricas Consolidadas de Acurácia por Ferramenta e Perfil",
            num_formats={"TPR (Recall)": "0.000", "Precisão": "0.000", "FDR": "0.000", "F1-Score": "0.000"},
        )
        _, next_r = write_table(
            ws3, next_r + 1,
            ["Perfil", "Ferramenta", "Vuln ID", "Rota", "Classe", "Severidade"],
            data["postman_rows"],
            title="2. Achados da Suíte Postman / Newman (postman-findings-*.json)",
        )
        write_table(
            ws3, next_r + 1,
            ["Perfil", "Plugin ID", "Nome do Alerta (OWASP ZAP)", "Risco / Confiança", "Instâncias", "CWE ID"],
            data["zap_summary_rows"],
            title="3. Resumo de Tipos de Alerta do OWASP ZAP (zap-vulneravel.json e zap-protegido.json)",
        )
        ws3.freeze_panes = "A6"
        autofit_columns(ws3)

        # =====================================================================
        # ABA 4: Estatisticas_10_Rodadas
        # =====================================================================
        ws4 = wb.create_sheet("Estatisticas_10_Rodadas")
        style_banner(
            ws4, 8,
            "Estatísticas Consolidadas das 10 Rodadas (Média, Desvio Padrão, Mínimo e Máximo)",
            "Dados completos de results/relatorio-10-rodadas.csv (N=10 por perfil)"
        )
        rel_rows = [
            [r["categoria"], r["perfil"], r["alvo"], r["metrica"],
             r["media"], r["desvio_padrao"], r["min"], r["max"]]
            for r in data["rel10"]
        ]
        write_table(
            ws4, 4,
            ["Categoria", "Perfil", "Alvo / Rota / Container", "Métrica",
             "Média", "Desvio Padrão (DP)", "Mínimo", "Máximo"],
            rel_rows,
            title="Resumo Estatístico Completo (10 Rodadas — Vulnerável vs. Protegido)",
        )
        ws4.freeze_panes = "A6"
        autofit_columns(ws4)

        # =====================================================================
        # ABA 5: Brute_Force_r1_a_r10
        # =====================================================================
        ws5 = wb.create_sheet("Brute_Force_r1_a_r10")
        style_banner(
            ws5, 9,
            "Teste de Força Bruta em Rajada Paralela (VULN-AUTH-01) — Todas as Execuções",
            "Aglutinação de brute-force-*.json (bateria principal + rodadas r1..r10)"
        )
        write_table(
            ws5, 4,
            ["Arquivo Origem", "Perfil", "Rodada", "Tentativas",
             "Erros Conexão (0)", "HTTP 401", "HTTP 429 (Rate Limit)", "Veredito", "Achado"],
            data["bf_rows"],
            title="Resultados Individuais de Força Bruta (100 tentativas paralelas por execução)",
        )
        ws5.freeze_panes = "A6"
        autofit_columns(ws5)

        # =====================================================================
        # ABA 6: Latencia_r1_a_r10
        # =====================================================================
        ws6 = wb.create_sheet("Latencia_r1_a_r10")
        style_banner(
            ws6, 12,
            "Teste de Carga, Latência e Vazão (Etapa C) — Todas as Execuções",
            "Aglutinação completa de latencia-*.csv (bateria principal + rodadas r1..r10)"
        )
        write_table(
            ws6, 4,
            ["Arquivo Origem", "Perfil", "Rodada", "Rota", "Nº Req",
             "p50 (ms)", "p90 (ms)", "p95 (ms)", "p99 (ms)", "Média (ms)", "Throughput (RPS)", "Erro/Bloq (%)"],
            data["lat_rows"],
            title="Medições de Latência e Throughput por Rota (Principal + r1..r10)",
            num_formats={"p50 (ms)": "0.00", "p90 (ms)": "0.00", "p95 (ms)": "0.00",
                         "p99 (ms)": "0.00", "Média (ms)": "0.00", "Throughput (RPS)": "0.0",
                         "Erro/Bloq (%)": "0.0"},
        )
        ws6.freeze_panes = "A6"
        autofit_columns(ws6)

        # =====================================================================
        # ABA 7: Recursos_CPU_RAM_r1_a_r10
        # =====================================================================
        ws7 = wb.create_sheet("Recursos_CPU_RAM_r1_a_r10")
        style_banner(
            ws7, 7,
            "Consumo de Recursos Docker (CPU % e RAM MiB) — Resumo e Amostras Brutas",
            "Aglutinação de recursos-*-carga*.csv (bateria principal + rodadas r1..r10)"
        )
        _, next_r = write_table(
            ws7, 4,
            ["Perfil", "Rodada", "Container", "Amostras", "CPU Média (%)", "CPU Máx (%)", "RAM Média (MiB)"],
            data["res_summary_rows"],
            title="1. Média por Rodada e Container (Principal + r1..r10)",
            num_formats={"CPU Média (%)": "0.00", "CPU Máx (%)": "0.00", "RAM Média (MiB)": "0.0"},
        )
        write_table(
            ws7, next_r + 1,
            ["Arquivo Origem", "Perfil", "Rodada", "Timestamp", "Container", "CPU (%)", "RAM (MiB)"],
            data["res_raw_rows"],
            title="2. Todas as Amostras Individuais de docker stats",
            num_formats={"CPU (%)": "0.00", "RAM (MiB)": "0.0"},
        )
        ws7.freeze_panes = "A6"
        autofit_columns(ws7)

        # =====================================================================
        # ABA 8: Telemetria_Prometheus
        # =====================================================================
        ws8 = wb.create_sheet("Telemetria_Prometheus")
        style_banner(
            ws8, 8,
            "Telemetria de Servidor Exportada do Prometheus (Micrometer / JVM)",
            "Aglutinação de telemetria-vulneravel.csv e telemetria-protegido.csv"
        )
        _, next_r = write_table(
            ws8, 4,
            ["Perfil", "Métrica", "Série", "Pontos", "Média", "Desvio Padrão", "Mínimo", "Máximo"],
            data["prom_summary_rows"],
            title="1. Resumo Estatístico das Séries Temporais do Prometheus",
            num_formats={"Média": "0.0000", "Desvio Padrão": "0.0000", "Mínimo": "0.0000", "Máximo": "0.0000"},
        )
        write_table(
            ws8, next_r + 1,
            ["Perfil", "Métrica", "Série", "Timestamp", "Valor"],
            data["prom_raw_rows"],
            title="2. Série Temporal Completa (telemetria-vulneravel.csv e telemetria-protegido.csv)",
        )
        ws8.freeze_panes = "A6"
        autofit_columns(ws8)

        os.makedirs(RESULTS_DIR, exist_ok=True)
        wb.save(OUT_XLSX)

    print(f"[gerar_excel] Planilha gerada com sucesso: {OUT_XLSX}")


if __name__ == "__main__":
    build_workbook()
