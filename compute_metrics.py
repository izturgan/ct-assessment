"""
compute_metrics.py
===================
Извлекает экспертные и LLM-оценки из базы данных (через n8n webhook),
вычисляет метрики согласованности и сохраняет результат в validation_results.

Метрики:
  - Pearson r, Spearman rho
  - Quadratic Weighted Kappa (QWK)
  - Bland-Altman bias и пределы согласия
  - R^2 для Random Forest на NLP+LLM признаках (опционально, если есть данные)

Запуск:
    python compute_metrics.py
"""

import json
import uuid

import numpy as np
import requests
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import cohen_kappa_score

N8N_WEBHOOK = "https://neuron.finreg.kz/webhook/nurgissa-postgres"


def query(sql: str):
    resp = requests.post(N8N_WEBHOOK, json={"query": sql}, verify=False, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_paired_scores():
    """
    Получает пары (expert_score_normalized, llm_score_composite) для всех
    эссе, у которых есть и экспертная, и LLM-оценка.

    Поскольку webhook возвращает только одну строку за раз, итерируем по
    essay_id и собираем данные построчно.
    """
    max_id_resp = query("SELECT MAX(id) as max_id FROM essays")
    max_id = int(max_id_resp.get("max_id", 0))

    pairs = []
    for eid in range(1, max_id + 1):
        sql = (
            f"SELECT es.score_normalized as expert, ls.score_composite as llm "
            f"FROM expert_scores es "
            f"JOIN llm_scores ls ON ls.essay_id = es.essay_id "
            f"WHERE es.essay_id = {eid} LIMIT 1"
        )
        row = query(sql)
        if row and row.get("expert") is not None and row.get("llm") is not None:
            pairs.append({
                "essay_id": eid,
                "expert": float(row["expert"]),
                "llm": float(row["llm"]),
            })

    return pairs


def compute_qwk(expert: np.ndarray, llm: np.ndarray, n_bins: int = 10) -> float:
    """Дискретизирует непрерывные баллы [0,1] в n_bins уровней и считает QWK."""
    expert_d = np.round(expert * (n_bins - 1)).astype(int)
    llm_d = np.round(llm * (n_bins - 1)).astype(int)
    return cohen_kappa_score(expert_d, llm_d, weights="quadratic")


def bland_altman(expert: np.ndarray, llm: np.ndarray) -> dict:
    diff = llm - expert
    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff))
    return {
        "bias": round(mean_diff, 4),
        "std_diff": round(std_diff, 4),
        "loa_upper": round(mean_diff + 1.96 * std_diff, 4),
        "loa_lower": round(mean_diff - 1.96 * std_diff, 4),
    }


def save_validation_result(metrics: dict, n_essays: int):
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    sql = (
        f"INSERT INTO validation_results "
        f"(run_id, n_essays, pearson_r, spearman_rho, qwk, bias_mean, loa_upper, loa_lower) "
        f"VALUES ('{run_id}', {n_essays}, {metrics['pearson_r']}, {metrics['spearman_rho']}, "
        f"{metrics['qwk']}, {metrics['bland_altman']['bias']}, "
        f"{metrics['bland_altman']['loa_upper']}, {metrics['bland_altman']['loa_lower']})"
    )
    result = query(sql)
    print(f"\nSaved to validation_results as run_id={run_id}")
    return run_id


if __name__ == "__main__":
    print("Fetching paired expert/LLM scores...")
    pairs = fetch_paired_scores()
    print(f"Found {len(pairs)} essays with both expert and LLM scores.\n")

    if len(pairs) < 5:
        print("Not enough data points for meaningful statistics. Exiting.")
        exit(1)

    expert = np.array([p["expert"] for p in pairs])
    llm = np.array([p["llm"] for p in pairs])

    r, p_value_r = pearsonr(expert, llm)
    rho, p_value_rho = spearmanr(expert, llm)
    qwk = compute_qwk(expert, llm)
    ba = bland_altman(expert, llm)

    metrics = {
        "n_essays": len(pairs),
        "pearson_r": round(float(r), 4),
        "pearson_p": round(float(p_value_r), 6),
        "spearman_rho": round(float(rho), 4),
        "spearman_p": round(float(p_value_rho), 6),
        "qwk": round(float(qwk), 4),
        "bland_altman": ba,
        "expert_mean": round(float(np.mean(expert)), 4),
        "expert_std": round(float(np.std(expert)), 4),
        "llm_mean": round(float(np.mean(llm)), 4),
        "llm_std": round(float(np.std(llm)), 4),
    }

    print("=" * 60)
    print("VALIDATION METRICS — LLM vs Expert Scores")
    print("=" * 60)
    print(json.dumps(metrics, indent=2))
    print("=" * 60)

    # Интерпретация для гипотез ВКР
    print("\nИнтерпретация относительно гипотез ВКР:")
    h1_pass = metrics["pearson_r"] > 0.70
    print(f"H1 (r > 0.70): {'ПОДТВЕРЖДЕНА' if h1_pass else 'НЕ ПОДТВЕРЖДЕНА'} "
          f"(r = {metrics['pearson_r']})")

    bias = metrics["bland_altman"]["bias"]
    h2_direction = "завышение" if bias > 0 else "занижение" if bias < 0 else "нет смещения"
    print(f"H2 (систематическое смещение): {h2_direction} "
          f"(bias = {bias})")

    run_id = save_validation_result(metrics, len(pairs))

    # Экспорт таблицы для приложения ВКР
    import csv
    with open("validation_pairs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["essay_id", "expert_score", "llm_score", "diff"])
        for p in pairs:
            writer.writerow([p["essay_id"], p["expert"], p["llm"],
                            round(p["llm"] - p["expert"], 4)])
    print("\nSaved detailed pairs to validation_pairs.csv (for thesis appendix)")