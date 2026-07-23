from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class ProducerSettings(BaseSettings):
    aws_region: str = "eu-north-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_endpoint_url: str | None = None  # To point to LocalStack
    
    s3_bucket_name: str = "alt-raw-data"
    sqs_queue_name: str = "alt-ticker-queue.fifo"
    
    exchange_id: str = "binance"
    slack_webhook_url: str | None = None
    symbols: str = "BTC/USDT,ETH/USDT"
    
    s3_dump_interval_seconds: int = 300  # 5 minutes
    
    @property
    def symbol_list(self) -> List[str]:
        return [s.strip() for s in self.symbols.split(",") if s.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = ProducerSettings()
