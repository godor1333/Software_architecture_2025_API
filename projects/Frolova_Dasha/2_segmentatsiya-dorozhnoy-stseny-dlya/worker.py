"""Consume frame events from Kafka and save segmentation outputs."""
import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer
from app import MinioFrameStore, store_frame

async def main():
    consumer=AIOKafkaConsumer('frames.created',bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS','kafka:9092'),group_id='scene-segmentation',auto_offset_reset='earliest',enable_auto_commit=False)
    await consumer.start()
    try:
        async for message in consumer:
            event=json.loads(message.value.decode('utf-8'))
            def process():
                store=MinioFrameStore()
                response=store.client.get_object(event.get('bucket','scene-frames'),event['source_object'])
                try: content=response.read()
                finally: response.close(); response.release_conn()
                return store_frame(event['frame_id'],event['flight_id'],content)
            result=await asyncio.to_thread(process)
            await consumer.commit()
            print(json.dumps({'frame_id':result['frame_id'],'flight_id':result['flight_id'],
                              'width':result['width'],'height':result['height'],
                              'dominant_class':result['dominant_class'],
                              'published':'frames.segmented'}, ensure_ascii=False),flush=True)
    finally:
        await consumer.stop()

if __name__=='__main__': asyncio.run(main())
