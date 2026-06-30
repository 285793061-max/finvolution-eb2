from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    data_dir: Path = BASE_DIR / "data"


settings = Settings()

