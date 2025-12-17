
import logging
import sys
# это логгер конфиг
# настройка цветов для логов
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[41;97m',
        'RESET': '\033[0m'
    }

    def format(self, record):
        s = super().format(record)
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS.get('RESET', '')
        return f"{color}{s}{reset}"

def setup_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColorFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass
    return root_logger

def get_logger(name: str = None):
    return logging.getLogger(name)