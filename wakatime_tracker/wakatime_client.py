import requests
import logging
from wakatime_tracker.config import load_config

logger = logging.getLogger(__name__)


class WakaTimeClient:
    def __init__(self):
        self.config = load_config().wakatime
        self.base_url = self.config.base_url
        self.headers = {"Authorization": f"Basic {self.config.api_key}"}

    def get_summaries(self, start_date: str, end_date: str) -> dict | None:
        """Получение сводки за период"""

        url = f"{self.base_url}/users/{self.config.user_id}/summaries"
        params = {"start": start_date, "end": end_date}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching WakaTime data: {e}")
            raise

    @staticmethod
    def extract_project_data(summaries_data: dict) -> list[dict]:
        """Извлечение данных по проектам из ответа API"""

        project_data = []

        for day_data in summaries_data.get("data", []):
            date = day_data["range"]["date"]

            # Обрабатываем проекты
            for project in day_data.get("projects", []):
                project_data.append(
                    {
                        "date": date,
                        "name": project["name"],
                        "total_seconds": project["total_seconds"],
                        "digital": project.get("digital", ""),
                        "text": project.get("text", ""),
                        "percent": project.get("percent", 0),
                    }
                )

        return project_data
