from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# Example event structures based on spec
# {"event": "inventory.update", "data": {"ingredient_id": "uuid", "new_quantity_grams": 1500}}
# {"event": "alerts.low_stock", "data": {"ingredient_id": "uuid", "name": "Carrot", "quantity_grams": 40, "threshold": 50}}
# {"event": "serve.attempt", "data": {"meal_id": "uuid", "portions": 10, "status": "validating" | "success" | "error", "message": "Optional error message"}}

async def broadcast_inventory_update(ingredient_id: str, new_quantity_grams: int):
    await manager.broadcast({
        "event": "inventory.update",
        "data": {"ingredient_id": str(ingredient_id), "new_quantity_grams": new_quantity_grams}
    })

async def broadcast_low_stock_alert(ingredient_id: str, name: str, quantity_grams: int, threshold: int):
    await manager.broadcast({
        "event": "alerts.low_stock",
        "data": {
            "ingredient_id": str(ingredient_id),
            "name": name,
            "quantity_grams": quantity_grams,
            "threshold": threshold
        }
    })

async def broadcast_serve_attempt(meal_id: str, portions: int, status: str, message: str = None, websocket: WebSocket = None):
    payload = {
        "event": "serve.attempt",
        "data": {
            "meal_id": str(meal_id),
            "portions": portions,
            "status": status,
        }
    }
    if message:
        payload["data"]["message"] = message
    
    if websocket: # If a specific client initiated, send to them first or only them
        await manager.send_personal_message(payload, websocket)
    else: # Or broadcast to all if it's a general update after completion
        await manager.broadcast(payload)

# WebSocket endpoint itself
from fastapi import APIRouter

router = APIRouter()

@router.websocket("/ws/inventory")
async def websocket_inventory_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We can receive messages from client if needed, but spec focuses on server-to-client
            data = await websocket.receive_text() 
            # For now, just keep connection alive. Could echo or process client messages.
            # await manager.send_personal_message(f"Message text was: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Optionally log disconnects
    except Exception as e:
        # Log other exceptions
        print(f"WebSocket Error: {e}")
        manager.disconnect(websocket)

