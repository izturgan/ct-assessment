"""
run_scoring.py
===============
Запускает LLM-оценку (4 агента через n8n) для всех эссе в базе,
у которых ещё нет записи в llm_scores.

Делает это последовательно, с паузой между запросами, чтобы не
перегружать локально развёрнутую модель GPT OSS 120B.

Запуск:
    python run_scoring.py
    python run_scoring.py --limit 10      (только первые 10)
    python run_scoring.py --essay-ids 1,2,3   (конкретные ID)
"""

import argparse
import time

import requests

API_BASE = "http://127.0.0.1:8000"
TRIGGER_URL = f"{API_BASE}/api/essays/trigger-scoring/"
N8N_WEBHOOK = "https://neuron.finreg.kz/webhook/nurgissa-postgres"

# Таймаут на одно эссе — агент думает долго (4 последовательных вызова LLM)
SCORING_TIMEOUT = 180
PAUSE_BETWEEN_ESSAYS = 3  # секунды


def get_pending_essay_ids(limit: int = None) -> list:
    """Находит essay_id, у которых ещё нет записи в llm_scores."""
    query = (
        "SELECT e.id FROM essays e "
        "LEFT JOIN llm_scores ls ON ls.essay_id = e.id "
        "WHERE ls.id IS NULL "
        "ORDER BY e.id"
    )
    if limit:
        query += f" LIMIT {limit}"

    resp = requests.post(
        N8N_WEBHOOK,
        json={"query": query},
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # n8n webhook в этой конфигурации возвращает только первую строку.
    # Поэтому получаем полный список другим способом — через диапазон ID.
    if isinstance(data, dict) and "id" in data:
        # Если вернулась только одна строка — придётся итерировать вручную.
        # Используем fallback: получить общее количество и пройтись по всем ID.
        return None
    if isinstance(data, list):
        return [row["id"] for row in data]
    return None


def get_all_essay_ids_fallback(limit: int = None) -> list:
    """
    Fallback метод: получает максимальный essay_id и id уже оценённых эссе,
    вычисляет разницу. Используется когда webhook возвращает одну строку.
    """
    # Получаем max essay id
    resp = requests.post(
        N8N_WEBHOOK,
        json={"query": "SELECT MAX(id) as max_id FROM essays"},
        verify=False, timeout=30,
    )
    max_id = int(resp.json().get("max_id", 0))

    # Получаем id всех уже оценённых эссе — собираем по одному, т.к. webhook
    # отдаёт одну строку за раз. Поэтому проще просто пройтись по всем ID
    # от 1 до max_id и для каждого проверить наличие.
    pending = []
    for eid in range(1, max_id + 1):
        check = requests.post(
            N8N_WEBHOOK,
            json={"query": f"SELECT COUNT(*) as cnt FROM llm_scores WHERE essay_id = {eid}"},
            verify=False, timeout=30,
        )
        cnt = int(check.json().get("cnt", 0))
        if cnt == 0:
            pending.append(eid)
        if limit and len(pending) >= limit:
            break

    return pending


def trigger_scoring(essay_id: int) -> bool:
    try:
        resp = requests.post(
            TRIGGER_URL,
            json={"essay_id": essay_id},
            timeout=SCORING_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"  essay_id={essay_id} -> job_id={data.get('job_id', 'n/a')} | status={data.get('status')}")
        return True
    except requests.exceptions.Timeout:
        print(f"  essay_id={essay_id} -> TIMEOUT (model may still be processing)")
        return False
    except requests.RequestException as e:
        print(f"  essay_id={essay_id} -> ERROR: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LLM scoring for pending essays")
    parser.add_argument("--limit", type=int, default=None, help="Max number of essays to score")
    parser.add_argument("--essay-ids", type=str, default=None,
                       help="Comma-separated list of specific essay IDs")
    args = parser.parse_args()

    if args.essay_ids:
        essay_ids = [int(x) for x in args.essay_ids.split(",")]
    else:
        print("Finding essays pending scoring...")
        essay_ids = get_all_essay_ids_fallback(limit=args.limit)

    if not essay_ids:
        print("No pending essays found. All essays may already be scored.")
        exit(0)

    print(f"\nFound {len(essay_ids)} essays to score: {essay_ids}\n")
    print("Starting scoring (this will take a while — each essay requires "
          "4 sequential LLM calls)...\n")

    success_count = 0
    for i, eid in enumerate(essay_ids):
        print(f"[{i+1}/{len(essay_ids)}] Scoring essay_id={eid}...")
        ok = trigger_scoring(eid)
        if ok:
            success_count += 1
        time.sleep(PAUSE_BETWEEN_ESSAYS)

    print(f"\nDone. {success_count}/{len(essay_ids)} essays scored successfully.")