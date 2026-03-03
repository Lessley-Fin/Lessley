import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aio_pika

# --- RabbitMQ Configuration ---
RABBITMQ_URL = "amqp://guest:guest@localhost/"
QUEUE_NAME = "personalize_calc_history_queue"
ROUTING_KEY = "Personalize.calc_history"


async def process_calc_history_message(message: aio_pika.abc.AbstractIncomingMessage):
    """
    This function is triggered every time a message hits the queue.
    """
    async with message.process():
        body = message.body.decode()
        data = json.loads(body)
        user_id = data.get("user_id")

        print(f"[x] Received calculation request for User: {user_id}")
        # TODO: 1. Fetch Open Finance Data for this user
        # TODO: 2. Run Gap Analysis & Logic Check via Optimizer
        # TODO: 3. Publish personalize.money_calc or personalize.suggestion


async def consume_rabbitmq():
    """
    Background task to maintain the RabbitMQ connection and listen for events.
    """
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()

        # Declare the exchange and queue to ensure they exist
        exchange = await channel.declare_exchange(
            "lessley_events", aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        # Bind the queue to the specific event topic
        await queue.bind(exchange, routing_key=ROUTING_KEY)

        print(f"[*] Waiting for messages on '{ROUTING_KEY}'. To exit press CTRL+C")
        await queue.consume(process_calc_history_message)

        # Keep the connection open indefinitely
        await asyncio.Future()
    except Exception as e:
        print(f"RabbitMQ connection failed: {e}")


# --- FastAPI Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch the RabbitMQ consumer as a background task
    task = asyncio.create_task(consume_rabbitmq())
    yield
    # Shutdown: Clean up tasks when the server stops
    task.cancel()


# --- Application Initialization ---
app = FastAPI(
    title="Lessley Personalization Engine",
    description="AI-driven financial gap analysis and recommendations",
    version="1.0.0",
    lifespan=lifespan,
)


# --- REST Endpoints ---
@app.get("/health")
async def health_check():
    """Simple HTTP endpoint for the API Gateway or Kubernetes to verify the service is alive."""
    return {"status": "healthy", "service": "Personalization"}
