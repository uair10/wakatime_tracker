import logging
import os
import time

import schedule

from wakatime_tracker.config import load_config, SchedulerSettings
from wakatime_tracker.database.manager import DatabaseManager
from wakatime_tracker.logger import configure_logging
from wakatime_tracker.telegram_notifier import TelegramNotifier
from wakatime_tracker.wakatime_service import WakaTimeService
from wakatime_tracker.json_importer import JSONImporter


logger = logging.getLogger(__name__)


def daily_collection_job(service: WakaTimeService, telegram_notifier: TelegramNotifier):
    """Задача для ежедневного сбора данных"""

    try:
        logger.info("Running daily data collection job...")
        service.collect_yesterday_data()
    except Exception as e:
        logger.error(f"Error in daily collection job: {e}")
        telegram_notifier.send_error(f"Daily collection job failed: {str(e)}")


def import_initial_data(config: SchedulerSettings, importer: JSONImporter) -> None:
    if not config.import_initial_data:
        return
    if config.initial_data_path is None:
        logger.warning("File with initial data not set, skipping initial data import.")
    if not os.path.isfile(config.initial_data_path):
        logger.warning("Initial data file not found, skipping initial data import.")

    result = importer.import_initial_data(config.initial_data_path)
    logger.info(f"Initial data import completed: {result['imported_count']} projects imported")


def start_scheduler() -> None:
    config = load_config()
    configure_logging(config.logging)

    db = DatabaseManager()

    wakatime_service = WakaTimeService()
    tg_notifier = TelegramNotifier()
    importer = JSONImporter(db)

    # Импорт начальных данных, если база пуста
    import_initial_data(config.scheduler, importer)

    cron_parts = config.scheduler.cron_schedule.split()
    hour, minute = int(cron_parts[1]), int(cron_parts[0])

    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(daily_collection_job)
    logger.info(schedule.get_jobs())

    if config.scheduler.run_on_startup:
        daily_collection_job(wakatime_service, tg_notifier)

    while True:
        schedule.run_pending()
        logger.info(f"Scheduler started with cron: {config.scheduler.cron_schedule}")
        time.sleep(60)


if __name__ == "__main__":
    start_scheduler()
