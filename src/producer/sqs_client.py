import boto3
import json
import uuid
import logging
from typing import List

from src.producer.config import settings

logger = logging.getLogger(__name__)

class SQSClient:
    def __init__(self):
        client_kwargs = {
            "region_name": settings.aws_region
        }
        if settings.aws_endpoint_url:
            client_kwargs["endpoint_url"] = settings.aws_endpoint_url
        if settings.aws_access_key_id:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            
        self.sqs = boto3.client('sqs', **client_kwargs)
        try:
            # We fetch the QueueUrl dynamically from its name
            response = self.sqs.get_queue_url(QueueName='alt-ticker-queue.fifo')
            self.queue_url = response['QueueUrl']
            logger.info(f"SQS Queue URL initialized: {self.queue_url}")
        except Exception as e:
            logger.warning(f"Could not get queue URL. Ensure 'alt-ticker-queue' exists. Details: {e}")
            self.queue_url = None

    async def push_trades(self, trades: List[dict]):
        if not self.queue_url or not trades:
            return
            
        entries = []
        for trade in trades:
            entries.append({
                'Id': str(uuid.uuid4()),
                'MessageBody': json.dumps(trade),
                'MessageGroupId': trade.get('symbol', 'default'),
                'MessageDeduplicationId': str(trade.get('id', uuid.uuid4()))
            })
            
        try:
            # boto3 is synchronous, we run it directly here since it's fast enough for SQS
            # send_message_batch takes maximum 10 items
            response = self.sqs.send_message_batch(
                QueueUrl=self.queue_url,
                Entries=entries
            )
            
            if 'Failed' in response:
                logger.error(f"Failed to push some trades to SQS: {response['Failed']}")
                
        except Exception as e:
            logger.error(f"Error pushing to SQS: {e}")
            raise e
