from control.configuration import Config
import pika
import json

class RabbitOperations:
    def __init__(self):
        pass

    async def publish_event_in_queue(self,message,exchange):
        connection=None
        try:
            connection= pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel= connection.channel()
            channel.basic_publish(exchange=exchange,routing_key="",body=message)
            print("Message published succesfully in: ",exchange)
        except Exception as err:
            print(f"Error publishing the message in {exchange}",err)
        finally:
            if connection and not connection.is_closed:
                connection.close()