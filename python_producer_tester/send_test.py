from kafka import KafkaProducer
import json
from datetime import datetime
import sys

def json_serializer(data):
    return json.dumps(data).encode("utf-8")

producer = KafkaProducer(bootstrap_servers=['host.docker.internal:9092'],
                         value_serializer=json_serializer)

def send_message():
    message = {
        "chatter_name": "TEST",
        "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "is_vip": False,
        "content": sys.argv[1],
        "is_broadcaster": False,
        "is_subscriber": True,
        "is_mod": False,
        "channel": "nannitwitch"
    }
    producer.send('general', value=message)
    producer.flush()

if __name__ == "__main__":
    send_message()