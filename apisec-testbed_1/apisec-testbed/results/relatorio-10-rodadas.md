# Relatório Consolidado — 10 Rodadas de Testes (`vulneravel` vs. `protegido`)

Total de rodadas executadas por perfil: **10** (`r1` a `r10`).

Desvio padrão reportado como $\sigma$ populacional ($N=10$).


## 1. Consistência das 10 Vulnerabilidades OWASP API Top 10 (10/10 rodadas)

| ID | Vulnerável (rodadas expostas) | Protegido (rodadas mitigadas) | Regressões no Protegido | Consistência |
|---|---|---|---|---|
| VULN-SQLI-01 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-SQLI-02 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-SQLI-03 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-BOLA-01 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-BOLA-02 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-AUTH-01 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-AUTH-02 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-MISC-01 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-MISC-02 | 10/10 | 10/10 | 0 | 100% consistente |
| VULN-MISC-03 | 10/10 | 10/10 | 0 | 100% consistente |

## 2. Teste de Força Bruta em Rajada (`brute_force.py`, 100 tentativas/rodada)

| Perfil | HTTP 401 (média ± dp) | HTTP 429 (média ± dp) | Veredito nas 10 rodadas |
|---|---|---|---|
| vulneravel | 100.0 ± 0.0 | 0.0 ± 0.0 | 10/10 `VULN-AUTH-01` |
| protegido | 48.1 ± 12.3 | 50.9 ± 11.8 | 10/10 `SEM-ACHADO` |

## 3. Latência, Throughput e Taxa de Bloqueio (`loadtest.py`)

| Perfil | Rota | p50 (ms) | p90 (ms) | p95 (ms) | p99 (ms) | Throughput (RPS) | Erro/Bloq (%) |
|---|---|---|---|---|---|---|---|
| vulneravel | `GET /api/products` | 90.84 ± 34.41 | 134.45 ± 59.66 | 205.28 ± 36.52 | 344.79 ± 42.83 | 348.9 ± 14.6 | 0.0% ± 0.0% |
| vulneravel | `GET /api/products/search?q=roteador&order=name` | 91.08 ± 34.58 | 136.13 ± 59.89 | 208.53 ± 42.59 | 351.97 ± 50.25 | 348.9 ± 14.6 | 0.0% ± 0.0% |
| vulneravel | `GET /api/orders/1` | 93.42 ± 34.75 | 140.05 ± 60.40 | 210.80 ± 55.31 | 352.36 ± 51.90 | 348.9 ± 14.6 | 0.0% ± 0.0% |
| protegido | `GET /api/products` | 75.02 ± 19.83 | 131.10 ± 61.67 | 199.56 ± 62.96 | 319.59 ± 62.40 | 357.4 ± 6.7 | 91.2% ± 3.3% |
| protegido | `GET /api/products/search?q=roteador&order=name` | 75.45 ± 19.73 | 133.18 ± 61.14 | 200.48 ± 64.30 | 316.59 ± 63.09 | 357.4 ± 6.7 | 91.2% ± 3.2% |
| protegido | `GET /api/orders/1` | 75.01 ± 18.99 | 133.21 ± 60.91 | 200.90 ± 62.45 | 325.76 ± 63.54 | 357.4 ± 6.7 | 91.3% ± 3.4% |

## 4. Consumo de Recursos sob Carga (`recursos.py`)

| Perfil | Container | CPU Média (%) | RAM Média (MiB) |
|---|---|---|---|
| vulneravel | `apisec-cadvisor` | 2.15 ± 1.18 | 37.8 ± 2.7 |
| vulneravel | `apisec-gateway` | 57.83 ± 26.94 | 236.5 ± 11.7 |
| vulneravel | `apisec-grafana` | 0.72 ± 1.28 | 55.8 ± 3.6 |
| vulneravel | `apisec-keycloak` | 2.17 ± 1.01 | 898.2 ± 18.3 |
| vulneravel | `apisec-prometheus` | 0.47 ± 0.39 | 36.7 ± 10.0 |
| vulneravel | `apisec-redis` | 4.40 ± 1.17 | 10.5 ± 0.7 |
| vulneravel | `apisec-target` | 34.23 ± 20.92 | 216.8 ± 7.6 |
| protegido | `apisec-cadvisor` | 1.47 ± 0.83 | 40.5 ± 1.2 |
| protegido | `apisec-gateway` | 57.90 ± 26.77 | 208.4 ± 10.9 |
| protegido | `apisec-grafana` | 0.42 ± 0.39 | 53.2 ± 0.4 |
| protegido | `apisec-keycloak` | 3.36 ± 3.25 | 1005.2 ± 24.7 |
| protegido | `apisec-prometheus` | 0.25 ± 0.09 | 40.1 ± 1.9 |
| protegido | `apisec-redis` | 5.01 ± 1.23 | 10.7 ± 0.3 |
| protegido | `apisec-target` | 26.96 ± 14.65 | 183.4 ± 7.5 |
