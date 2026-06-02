import os
import logging
from pathlib import Path

_ROOT = Path(__file__).parent.parent

TEMPLATES_DIR = _ROOT / "templates"

# โหลด .env อัตโนมัติ (ถ้าไม่มีไฟล์ก็ไม่ error)
def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        env_path = _ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)  # override=False: env จริงชนะ .env
    except ImportError:
        pass  # python-dotenv ไม่ได้ติดตั้ง — ข้ามไป

_load_dotenv()


def setup_logging(level: str | None = None) -> None:
    level = level or os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(name)s] %(message)s",
    )
