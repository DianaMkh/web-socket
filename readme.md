# WebSocket Server with Graceful Shutdown (FastAPI)

This project implements a WebSocket server using FastAPI. It supports real-time notifications to connected clients and includes a graceful shutdown mechanism that ensures the service stops only when all clients disconnect or 30 minutes have passed since the shutdown signal was received.

## Features

* WebSocket endpoint at `/ws`
* Tracks active WebSocket connections
* Broadcasts a test notification every 10 seconds
* Graceful shutdown triggered by `SIGINT` or `SIGTERM`
* Logging of remaining connections and time until forced shutdown

## Requirements

* Python 3.10+
* FastAPI
* Uvicorn

## Setup Instructions

1. **Install dependencies**:

   ```bash
   pip install fastapi uvicorn
   ```

2. **Run the server**:

   ```bash
   uvicorn main:app
   ```

3. **Connect to WebSocket**:
   You can use browser dev tools, `websocat`, or any WebSocket client:

   ```bash
   websocat ws://localhost:8000/ws
   ```

## Testing the WebSocket

1. Start the server.
2. Connect one or more WebSocket clients.
3. Observe a test notification sent to all clients every 10 seconds.
4. Terminate the server with `Ctrl+C` or send `SIGINT`/`SIGTERM`.
5. The server will:

   * Wait for all clients to disconnect, or
   * Shut down forcibly after 30 minutes.

You will see log messages showing how many clients remain connected and how much time is left until forced shutdown.

## Notes

* The graceful shutdown logic relies on in-process signal handling.
* For correct behavior, use **1 worker** when running `uvicorn`. Multiple workers (`--workers > 1`) would launch separate processes with isolated memory and may break shared connection tracking.


Purpose:

This server is designed to deliver real-time notifications to connected clients using WebSocket technology. It is useful when timely information delivery is crucial—such as alerts, updates, and live feeds.

Key Features:
   WebSocket endpoint for multiple client connections.
   Sends scheduled (or on-demand) messages to all connected clients.
   Tracks and removes disconnected clients.
   Graceful shutdown support:
      Server waits until all clients disconnect OR
      Forces shutdown after 30 minutes.
   Signal handling for SIGINT and SIGTERM.
   Based on FastAPI’s new lifespan event system.

Potential Use Cases:
   Finance apps — real-time stock/crypto updates.
   Chat applications — as a base for real-time communication.
   Monitoring & alerting systems — instant delivery of alerts.
   Online multiplayer games — live game state synchronization.
   Trading dashboards — pushing updates about orders or price changes.
