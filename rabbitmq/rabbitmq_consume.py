import pika, sys, os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')

def subscribe_to_rabbitmq():
    rabbitmq = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = rabbitmq.channel()

    channel.queue_declare(queue='tasks')
    channel.basic_consume(queue='tasks', on_message_callback=consume_queue, auto_ack=True)
    channel.start_consuming()

def consume_queue(ch, method, properties, body):
    print(f" [x] Received {ch} {method} {body} {properties}")

