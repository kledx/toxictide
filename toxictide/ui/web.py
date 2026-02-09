"""
TOXICTIDE Web UI
backend for the Dragon Stream dashboard
"""
import asyncio
import json
import threading
import time
from typing import List

import structlog
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from toxictide.bus import get_bus, ALL_TOPICS

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Remove dead connections on next cycle or let disconnect handler handle it
                pass

class WebUI:
    def __init__(self):
        self.app = FastAPI()
        self.manager = ConnectionManager()
        self.bus = get_bus()
        self.stop_event = threading.Event()
        self.thread = None

        self._setup_routes()
        self._subscribe_to_bus()

    def _setup_routes(self):
        @self.app.get("/")
        async def get():
            with open("toxictide/ui/templates/dashboard.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)

    def _subscribe_to_bus(self):
        # Substitute all relevant topics to broadcast to WS
        for topic in ALL_TOPICS:
            self.bus.subscribe(topic, self._handle_event)

    def _handle_event(self, payload):
        # This runs in the main loop thread, so we need to be careful
        # We need to broadcast this to the websocket loop
        # For simplicity in this threaded MVP, we'll use a queue or just
        # fire-and-forget if we can access the loop.
        
        # Since logic runs in separate thread, we rely on the fact that
        # broadcast is async. But we are calling from sync bus handler.
        # We need a bridge.
        
        try:
            # Serialize payload
            if hasattr(payload, "model_dump_json"):
                data = payload.model_dump_json()
            else:
                # Basic types or dicts
                try:
                    data = json.dumps(payload, default=str)
                except:
                    data = str(payload)
            
            msg = json.dumps({
                "type": "event",
                 "topic": "bus_event", # Simplify for now, or pass real topic if we can closure it
                 "data": data, # We might need to wrap the topic in the payload or use a partial
                 "ts": time.time()
            })
            
            # Simple hack for threaded broadcast: create a task in the loop if available
            # Note: This is tricky with uvicorn running in its own thread/loop.
            # A robust way is to use a thread-safe queue.
            # For this MVP, we will try to get the running loop of the uvicorn thread? No.
            # We will use run_coroutine_threadsafe if we can get the loop, 
            # OR better: use FastAPI's background tasks? No, this is outside request context.
            
            # Implementation Detail:
            # We will assign the loop when uvicorn starts (tricky).
            # ALTERNATIVE: The bus handler just pushes to a thread-safe queue, 
            # and a background task in FastAPI reads from it.
            pass

        except Exception as e:
            logger.error("webui_event_error", error=str(e))

    # We need a better way to bridge Sync Bus -> Async WS
    # Let's use a queue.
    
import queue

# Global queue for bridging
# Global queue for bridging
event_queue = queue.Queue(maxsize=1000)

def bus_handler(topic, payload):
    try:
        # Pydantic support
        if hasattr(payload, "model_dump_json"):
             content = json.loads(payload.model_dump_json())
        else:
             content = payload
             
        message = {
            "topic": topic,
            "payload": content,
            "ts": time.time()
        }
        try:
            event_queue.put_nowait(message)
        except queue.Full:
            pass # Drop event if queue is full (client too slow or not connected)
    except Exception as e:
        logger.error("bus_bridge_error", error=str(e))

class WebUIv2:
    def __init__(self, host="0.0.0.0", port=8000):
        self.app = FastAPI()
        self.manager = ConnectionManager()
        self.host = host
        self.port = port
        self.bus = get_bus()
        
        self._setup_routes()
        
    def _setup_routes(self):
        @self.app.get("/")
        async def get():
            # Use relative path suitable for where main.py is run
            try:
                with open("toxictide/ui/templates/dashboard.html", "r", encoding="utf-8") as f:
                     return HTMLResponse(content=f.read())
            except FileNotFoundError:
                return HTMLResponse(content="<h1>Dashboard HTML not found</h1>")

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            try:
                while True:
                    # Check queue for new messages
                    # This is a bit polling-ish, but simple for threaded interop
                    while not event_queue.empty():
                        msg = event_queue.get()
                        await self.manager.broadcast(json.dumps(msg, default=str))
                    
                    await asyncio.sleep(0.1) # 100ms refresh rate
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
                
    def start(self):
        # Subscribe to all topics with the bridge handler
        # effectively bridging Sync EventBus -> Queue -> Async Websocket
        for topic in ALL_TOPICS:
            # Use a closure or partial to capture topic if needed, 
            # but our handler generic signature is (payload).
            # Wait, bus.py: handler(payload). Topic is not passed.
            # We need a wrapper.
            self.bus.subscribe(topic, self._make_handler(topic))
            
        # Run uvicorn in a separate thread
        thread = threading.Thread(target=self._run_server, daemon=True)
        thread.start()
        logger.info("webui_started", url=f"http://{self.host}:{self.port}")

    def _run_server(self):
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="error")

    def _make_handler(self, topic):
        def handler(payload):
            bus_handler(topic, payload)
        return handler

