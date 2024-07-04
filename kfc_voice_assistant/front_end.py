import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse


app = FastAPI()


class WebSocketManager:
    def __init__(self):
        self.transmit_client: WebSocket = None
    
    # Receives data for visualizing from the agent
    async def recieve(self, websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                if self.transmit_client:
                    await self.transmit_client.send_json(data)
        finally:
            pass
    
    # Transmits received data to display on client side root endpoint
    async def transmit(self, websocket: WebSocket):
        await websocket.accept()
        self.transmit_client = websocket


ws_manager = WebSocketManager()

# Route for receiving data from the agent
@app.websocket("/ws_receive")
async def websocket_receive(websocket: WebSocket):
    await ws_manager.recieve(websocket)

# Route for transmiting the visual data to display
@app.websocket("/ws_transmit")
async def websocket_transmit(websocket: WebSocket):
    await ws_manager.transmit(websocket)


# Root endpoint, serves HTML
@app.get("/")
async def read_root():
    html_content = """
    <html>
    <head>
        <title>KFC</title>
    </head>
    <body>
        <h1>Data Received:</h1>
        <ul id="messages"></ul>
        <script>
            var ws = new WebSocket("ws://" + window.location.host + "/ws_show");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var messageElement = document.createElement('li');
                var messageText = document.createTextNode(event.data);
                messageElement.appendChild(messageText);
                messages.appendChild(messageElement);
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
