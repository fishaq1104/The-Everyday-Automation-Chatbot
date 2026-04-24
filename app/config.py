from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    discord_token: str
    database_path: str = "data/bot.db"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN", "").strip()
        database_path = os.getenv("DATABASE_PATH", "data/bot.db").strip()

        if not token:
            raise ValueError(
                "DISCORD_TOKEN is missing. Set it in your environment or .env file."
            )

        return cls(discord_token=token, database_path=database_path)
