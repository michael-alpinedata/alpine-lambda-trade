import pytest
import json
from src.producer.sqs_client import SQSClient
from src.producer.config import settings

@pytest.mark.asyncio
async def test_sqs_push(sqs_client):
    # Align settings with the conftest.py fixture (eu-north-1)
    settings.aws_region = "eu-north-1"

    # Match the exact hardcoded queue name from src/producer/sqs_client.py
    queue_name = "alt-ticker-queue.fifo"
    
    # SQS requires the 'FifoQueue' attribute when creating a .fifo queue
    sqs_client.create_queue(
        QueueName=queue_name,
        Attributes={'FifoQueue': 'true'}
    )

    # Initialize the client AFTER the queue is created
    client = SQSClient()

    trade = {
        "id": "1",
        "symbol": "BTC/USDT",
        "price": 50000.0,
        "amount": 1.0,
        "side": "buy",
        "timestamp": 1629811200000,
        "datetime": "2021-08-24T12:00:00.000Z"
    }

    await client.push_trades([trade])
    
    # Verify the message was pushed to SQS
    response = sqs_client.get_queue_url(QueueName=queue_name)
    queue_url = response['QueueUrl']
    
    messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
    assert 'Messages' in messages
    assert len(messages['Messages']) == 1
    
    record_data = json.loads(messages['Messages'][0]['Body'])
    assert record_data['id'] == "1"
    assert record_data['symbol'] == "BTC/USDT"
    