import json
import logging

from wakatime_tracker.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class JSONImporter:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _import_from_file(self, file_path: str) -> dict:
        """Импортирование данных из JSON файла"""

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_count = 0
            error_count = 0

            for day_data in data.get("days", []):
                date = day_data["date"]

                # Обрабатываем проекты
                for project in day_data.get("projects", []):
                    try:
                        project_info = self._extract_project_data(project, date)
                        self.db.save_project_data(date, project_info)
                        imported_count += 1

                    except Exception as e:
                        logger.error(f"Error importing project {project.get('name', 'unknown')} for {date}: {e}")
                        error_count += 1

            logger.info(f"JSON import completed: {imported_count} projects imported, {error_count} errors")
            return {
                "imported_count": imported_count,
                "error_count": error_count,
                "total_days": len(data.get("days", [])),
            }

        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
            raise

    @staticmethod
    def _extract_project_data(project: dict, date: str) -> dict:
        """Извлечение данных проекта из JSON структуры"""

        return {
            "date": date,
            "name": project["name"],
            "total_seconds": project["grand_total"]["total_seconds"],
            "digital": project["grand_total"].get("digital", ""),
            "text": project["grand_total"].get("text", ""),
            "percent": project["grand_total"].get("percent", 0),
        }

    def import_initial_data(self, file_path: str = "/wakatime_tracker/data/initial_data.json"):
        """Импортир начальные данных из экспортированного из wakatime файла"""

        try:
            result = self._import_from_file(file_path)
            return result
        except FileNotFoundError:
            logger.warning(f"JSON file not found at {file_path}")
            return {"imported_count": 0, "error_count": 0, "total_days": 0}
