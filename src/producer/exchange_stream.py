import ccxt.pro as ccxt
import asyncio
import logging
import json
import urllib.request
import urllib.error
from typing import List, Callable, Awaitable
from src.producer.config import settings

logger = logging.getLogger(__name__)

class ExchangeStream:
    def __init__(self, callbacks: List[Callable[[dict], Awaitable[None]]]):
        self.callbacks = callbacks
        self.symbols = settings.symbol_list
        self.running = False
        
        # Determine the fallback sequence
        primary = settings.exchange_id.lower()
        base_fallbacks = ["binance", "kraken", "coinbase"]
        if primary in base_fallbacks:
            base_fallbacks.remove(primary)
        self.exchanges_to_try = [primary] + base_fallbacks
        self.current_exchange_idx = 0
        self.exchange = None

    def _send_alert(self, message: str):
        if not settings.slack_webhook_url:
            return
        logger.info(f"Sending alert to Slack: {message}")
        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(
            settings.slack_webhook_url, 
            data=payload, 
            headers={'Content-Type': 'application/json'}
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    async def _init_exchange(self):
        if self.exchange:
            await self.exchange.close()
        
        exchange_name = self.exchanges_to_try[self.current_exchange_idx]
        logger.info(f"Initializing connection to '{exchange_name}' for {self.symbols}...")
        self.exchange = getattr(ccxt, exchange_name)()

    async def start(self):
        self.running = True
        
        await self._init_exchange()

        retry_count = 0
        max_retries_per_exchange = 3

        while self.running:
            try:
                tasks = [self._watch_symbol(sym) for sym in self.symbols]
                await asyncio.gather(*tasks)
                
                # If we exit cleanly without exception (exchange disconnected), reset retry count
                retry_count = 0
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream error on {self.exchanges_to_try[self.current_exchange_idx]}: {e}")
                
                retry_count += 1
                if retry_count > max_retries_per_exchange:
                    logger.warning(f"Max retries reached. Triggering fallback...")
                    self._send_alert(f"🚨 *ALT Producer Alert* 🚨\nSwitching fallback. Exchange `{self.exchanges_to_try[self.current_exchange_idx]}` failed.")
                    self.current_exchange_idx = (self.current_exchange_idx + 1) % len(self.exchanges_to_try)
                    retry_count = 0
                    await self._init_exchange()
                    await asyncio.sleep(2)
                else:
                    # Exponential backoff
                    backoff_time = 2 ** retry_count
                    logger.info(f"Reconnecting in {backoff_time}s (Attempt {retry_count}/{max_retries_per_exchange})...")
                    await asyncio.sleep(backoff_time)
                
    async def _watch_symbol(self, symbol: str):
        while self.running:
            try:
                # CCXT watch_trades can throw exceptions on drop
                trades = await self.exchange.watch_trades(symbol)
                for trade in trades:
                    for callback in self.callbacks:
                        await callback(trade)
            except Exception as e:
                logger.error(f"Error watching {symbol}: {e}")
                raise e

    async def stop(self):
        self.running = False
        if self.exchange:
            await self.exchange.close()
        logger.info(f"Exchange connection closed.")
