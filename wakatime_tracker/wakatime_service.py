import logging
from datetime import datetime, timedelta

from wakatime_tracker.database.manager import DatabaseManager
from wakatime_tracker.wakatime_client import WakaTimeClient
from wakatime_tracker.telegram_notifier import TelegramNotifier
import time

logger = logging.getLogger(__name__)


class WakaTimeService:
    def __init__(self):
        self.db = DatabaseManager()
        self.wakatime_client = WakaTimeClient()
        self.telegram_notifier = TelegramNotifier()

    def collect_data_for_date(self, date: str) -> bool:
        """Сбор данных за конкретную дату"""

        try:
            logger.info(f"Collecting data for date: {date}")

            # Получаем данные из WakaTime
            summaries = self.wakatime_client.get_summaries(date, date)
            if not summaries or "data" not in summaries:
                logger.warning(f"No data found for date {date}")
                return False

            # Извлекаем данные проектов
            project_data = self.wakatime_client.extract_project_data(summaries)

            # Сохраняем в базу
            for project in project_data:
                self.db.save_project_data(date, project)

            success_msg = f"Collected data for {date}: {len(project_data)} projects"
            logger.info(success_msg)
            self.telegram_notifier.send_success("Data collection completed", success_msg)

            return True

        except Exception as e:
            error_msg = f"Failed to collect data for {date}: {str(e)}"
            logger.error(error_msg)
            self.telegram_notifier.send_error(error_msg, f"Date: {date}")
            return False

    def collect_historical_data(self, start_date: str, end_date: str):
        """Сбор данных за период"""

        logger.info(f"Collecting historical data from {start_date} to {end_date}")

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        current = start
        success_count = 0
        total_days = (end - start).days + 1

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if self.collect_data_for_date(date_str):
                success_count += 1

            # Пауза чтобы не превысить лимиты API
            time.sleep(1)
            current += timedelta(days=1)

        summary = f"Historical data collection completed: {success_count}/{total_days} days"
        logger.info(summary)
        self.telegram_notifier.send_success("Historical data collection", summary)

    def collect_yesterday_data(self):
        """Сбор данных за вчера"""

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.collect_data_for_date(yesterday)
