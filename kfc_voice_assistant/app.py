import uvicorn
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

app.mount("/images", StaticFiles(directory="images"), name="images")
templates = Jinja2Templates(directory="templates")


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
                    html_content = self.construct_html_div(data)
                    await self.transmit_client.send_text(html_content)
        except WebSocketDisconnect:
            pass
        finally:
            if self.transmit_client == websocket:
                self.transmit_client = None
    
    # Transmits received data to display on client side root endpoint
    async def transmit(self, websocket: WebSocket):
        await websocket.accept()
        self.transmit_client = websocket
        
    def construct_html_div(self, data):
        """Construct the HTML div content based on the received data
        This is just an example, adjust according to your data structure"""
        html = f"""
        <div class="data-container">
            <p>{data}</p>
        </div>
        """
        return html


ws_manager = WebSocketManager()


# Route for receiving data from the agent
@app.websocket("/ws_receive")                      
async def websocket_receive(websocket: WebSocket):
    await ws_manager.recieve(websocket)

# Route for transmiting the visual data to display
@app.websocket("/ws_transmit")                      
async def websocket_transmit(websocket: WebSocket):
    await ws_manager.transmit(websocket)



@app.get("/")
async def read_root():
    html_content = """
    <html>
    <head>
        <title>KFC</title>
        <style>
            body, html {
                height: 100%;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: Arial, sans-serif;
            }
            #content {
                text-align: center;
            }
            img {
                max-width: 100%;
                max-height: 80vh;
            }
            #data-display {
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div id="content">
            <img src="/images/poster1.jpg" alt="Poster" id="poster"/>
            <div id="data-display"></div>
        </div>
        <script>
            var ws = new WebSocket("ws://" + window.location.host + "/ws_transmit");
            ws.onmessage = function(event) {
                var dataDisplay = document.getElementById('data-display');
                dataDisplay.innerHTML = event.data;
                document.getElementById('poster').style.display = 'none';
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)