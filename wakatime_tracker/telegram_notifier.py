import requests
import logging
from wakatime_tracker.config import load_config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.config = load_config().telegram

    def send_message(self, message: str) -> bool:
        """Отправка сообщения в Telegram"""

        try:
            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
            payload = {"chat_id": self.config.chat_id, "text": message, "parse_mode": "HTML"}

            response = requests.post(url, json=payload, timeout=10)
            logger.info(response.json())
            response.raise_for_status()
            logger.info("Telegram message sent successfully")
            return True

        except Exception as e:
            logger.error("Failed to send Telegram message", exc_info=e)
            return False

    def send_error(self, error_message: str, context: str = ""):
        """Отправка сообщения об ошибке"""

        message = f"🚨 <b>WakaTime Error</b>\n\n{error_message}"
        if context:
            message += f"\n\nContext: {context}"

        return self.send_message(message)

    def send_success(self, action: str, details: str = ""):
        """Отправка сообщения об успешном выполнении"""

        message = f"✅ <b>WakaTime Success</b>\n\n{action}"
        if details:
            message += f"\n\n{details}"

        return self.send_message(message)
