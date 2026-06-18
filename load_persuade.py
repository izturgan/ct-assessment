"""
load_persuade.py
=================
Загружает корпус PERSUADE (Feedback Prize format) из train.csv,
собирает полные эссе из фрагментов дискурса (discourse-level rows),
вычисляет агрегированную экспертную оценку и загружает в систему
через Django API (/api/essays/upload/).

Формат входного файла train.csv:
    discourse_id, essay_id, discourse_text, discourse_type, discourse_effectiveness

discourse_effectiveness: Ineffective | Adequate | Effective
Маппинг в числовую шкалу: Ineffective=1, Adequate=2, Effective=3

Запуск:
    python load_persuade.py --n 50
    python load_persuade.py --n 50 --dry-run   (без отправки на API)
"""

import argparse
import sys
import time

import pandas as pd
import requests

API_BASE = "http://127.0.0.1:8000"
UPLOAD_URL = f"{API_BASE}/api/essays/upload/"

EFFECTIVENESS_MAP = {
    "Ineffective": 1,
    "Adequate": 2,
    "Effective": 3,
}

# Порядок типичной структуры аргументативного эссе (для сборки текста)
DISCOURSE_ORDER = [
    "Lead", "Position", "Claim", "Counterclaim", "Rebuttal",
    "Evidence", "Concluding Statement",
]


def load_and_aggregate(csv_path: str, n_essays: int, skip: int = 0) -> pd.DataFrame:
    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} discourse rows across {df['essay_id'].nunique()} essays")

    # Группируем по essay_id (с возможностью пропустить уже загруженные)
    essays = []
    all_ids = df["essay_id"].unique()
    essay_ids = all_ids[skip:skip + n_essays]
    print(f"Selecting essays [{skip}:{skip + n_essays}] from {len(all_ids)} available")

    for eid in essay_ids:
        rows = df[df["essay_id"] == eid].copy()

        # Сортируем фрагменты в логическом порядке аргументации
        rows["order_key"] = rows["discourse_type"].apply(
            lambda t: DISCOURSE_ORDER.index(t) if t in DISCOURSE_ORDER else 99
        )
        rows = rows.sort_values("order_key")

        # Склеиваем текст
        full_text = " ".join(rows["discourse_text"].astype(str).tolist())
        full_text = full_text.strip()

        if len(full_text.split()) < 30:
            continue  # слишком короткое — пропускаем

        # Агрегированная оценка: среднее по всем фрагментам, нормализованное к [0,1]
        scores = rows["discourse_effectiveness"].map(EFFECTIVENESS_MAP).dropna()
        if len(scores) == 0:
            continue
        mean_score = scores.mean()  # диапазон [1, 3]
        score_normalized = (mean_score - 1) / 2  # нормализация к [0, 1]

        essays.append({
            "essay_id_source": eid,
            "essay_text": full_text,
            "word_count": len(full_text.split()),
            "mean_effectiveness": round(mean_score, 3),
            "score_normalized": round(score_normalized, 4),
            "n_fragments": len(rows),
        })

    result_df = pd.DataFrame(essays)
    print(f"Aggregated into {len(result_df)} complete essays (after filtering)")
    return result_df


def upload_essays(df: pd.DataFrame, dry_run: bool = False) -> list:
    uploaded = []

    for idx, row in df.iterrows():
        payload = {
            "essay_text": row["essay_text"],
            "source": "persuade",
            "language": "en",
        }

        if dry_run:
            print(f"[DRY RUN] Would upload essay {row['essay_id_source']} "
                  f"({row['word_count']} words, score={row['score_normalized']})")
            continue

        try:
            resp = requests.post(UPLOAD_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            local_id = data.get("id")
            uploaded.append({
                "local_id": local_id,
                "source_id": row["essay_id_source"],
                "score_normalized": row["score_normalized"],
                "word_count": row["word_count"],
            })
            print(f"[{idx+1}/{len(df)}] Uploaded essay_id_source={row['essay_id_source']} "
                  f"-> local_id={local_id} | words={row['word_count']} | "
                  f"score={row['score_normalized']:.3f}")
        except requests.RequestException as e:
            print(f"[ERROR] Failed to upload {row['essay_id_source']}: {e}")

        time.sleep(0.2)  # лёгкая задержка чтобы не перегружать сервер

    return uploaded


def save_expert_scores(uploaded: list):
    """
    Сохраняет экспертные оценки (нормализованные баллы из PERSUADE)
    в таблицу expert_scores через n8n webhook.
    Использует тот же webhook что и для остальных таблиц.
    """
    n8n_webhook = "https://neuron.finreg.kz/webhook/nurgissa-postgres"

    for item in uploaded:
        if item["local_id"] is None:
            continue
        query = (
            f"INSERT INTO expert_scores (essay_id, score_raw, score_normalized, source) "
            f"VALUES ({item['local_id']}, {item['score_normalized']}, "
            f"{item['score_normalized']}, 'persuade_holistic')"
        )
        try:
            resp = requests.post(
                n8n_webhook,
                json={"query": query},
                verify=False,
                timeout=30,
            )
            if resp.status_code == 200:
                print(f"  expert_score saved for essay {item['local_id']}")
            else:
                print(f"  [WARN] expert_score failed for essay {item['local_id']}: {resp.text}")
        except requests.RequestException as e:
            print(f"  [ERROR] expert_score request failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load PERSUADE essays into the system")
    parser.add_argument("--csv", default="train.csv", help="Path to PERSUADE train.csv")
    parser.add_argument("--n", type=int, default=50, help="Number of essays to load")
    parser.add_argument("--skip", type=int, default=0, help="Number of essays to skip from the start")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually upload")
    args = parser.parse_args()

    df = load_and_aggregate(args.csv, args.n, skip=args.skip)

    if len(df) == 0:
        print("No essays to upload after filtering. Exiting.")
        sys.exit(1)

    print(f"\nUploading {len(df)} essays to {UPLOAD_URL}...")
    uploaded = upload_essays(df, dry_run=args.dry_run)

    if not args.dry_run and uploaded:
        print(f"\nSaving expert scores for {len(uploaded)} essays...")
        save_expert_scores(uploaded)

    print(f"\nDone. {len(uploaded)} essays uploaded.")