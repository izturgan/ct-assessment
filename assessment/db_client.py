import json
import requests
from django.conf import settings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class N8nDBClient:
    def __init__(self):
        self.webhook_url = settings.N8N_DB_WEBHOOK
        self._session = requests.Session()
        self._session.verify = False

    def _format_value(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (dict, list)):
            escaped = json.dumps(value, ensure_ascii=False).replace("'", "''")
            return f"'{escaped}'"
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def execute(self, query: str, params=None) -> list[dict]:
        if params:
            formatted = [self._format_value(p) for p in params]
            parts = query.split("%s")
            if len(parts) != len(formatted) + 1:
                raise ValueError(
                    f"Query has {len(parts) - 1} placeholders but {len(formatted)} params were given"
                )
            query = "".join(p + v for p, v in zip(parts, formatted)) + parts[-1]

        response = self._session.post(
            self.webhook_url,
            json={"query": query},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        return [data] if data else []
