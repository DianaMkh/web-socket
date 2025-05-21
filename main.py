import asyncio
import signal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
from threading import Event
from datetime import datetime, timedelta
import uvicorn
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Define the lifespan first
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create and store the connection manager in the app state
    app.state.manager = ConnectionManager()
    app.state.shutdown_event = Event()
    app.state.shutdown_requested_at = None

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def handle_signal(signum, frame):
        if not app.state.shutdown_event.is_set():
            logger.info(f"Signal {signum} received, initiating graceful shutdown...")
            loop.create_task(graceful_shutdown(app))

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Start background tasks
    notify_task = asyncio.create_task(notify_clients_periodically(app))

    yield

    # Shutdown logic
    await graceful_shutdown(app)
    notify_task.cancel()
    try:
        await notify_task
    except asyncio.CancelledError:
        logger.info("Notification task cancelled")


# Now create the app with the lifespan
app = FastAPI(lifespan=lifespan)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {self.count()}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Remaining connections: {self.count()}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {str(e)}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def is_empty(self) -> int:
        return len(self.active_connections) == 0

    def count(self) -> int:
        return len(self.active_connections)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await app.state.manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        app.state.manager.disconnect(websocket)


@app.get("/status")
async def get_status():
    """Return server status information including connected clients count"""
    shutdown_time = None
    if app.state.shutdown_requested_at:
        shutdown_time = app.state.shutdown_requested_at.isoformat()

    return {
        "active_connections": app.state.manager.count(),
        "shutdown_requested": app.state.shutdown_event.is_set(),
        "shutdown_requested_at": shutdown_time
    }


async def notify_clients_periodically(app: FastAPI):
    """Sends notifications to all connected clients periodically"""
    while not app.state.shutdown_event.is_set():
        await asyncio.sleep(10)
        count = app.state.manager.count()
        if count > 0:
            logger.info(f"Broadcasting notification to {count} clients")
            await app.state.manager.broadcast("Test notification")


async def graceful_shutdown(app: FastAPI):
    """Handle graceful shutdown with timeout"""
    app.state.shutdown_requested_at = datetime.utcnow()
    logger.info("Shutdown signal received. Waiting for clients to disconnect...")

    # Send shutdown notification to clients
    await app.state.manager.broadcast("Server is shutting down soon. Please reconnect later.")

    deadline = app.state.shutdown_requested_at + timedelta(minutes=30)
    while datetime.utcnow() < deadline:
        if app.state.manager.is_empty():
            logger.info("All clients disconnected. Shutting down now.")
            break

        time_left = (deadline - datetime.utcnow()).total_seconds()
        logger.info(f"Clients remaining: {app.state.manager.count()}, time left: {int(time_left)}s")
        await asyncio.sleep(5)

    app.state.shutdown_event.set()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)