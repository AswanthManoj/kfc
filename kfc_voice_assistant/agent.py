import ast
import websocket
import yaml, json
import numpy as np
from io import BytesIO
import sounddevice as sd
import assemblyai as aai
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.playback import play
from config import SYSTEM_PROMPT
from langchain_groq import ChatGroq
from langchain_core.tools import BaseTool
from typing import List, Dict, Optional, Tuple
import requests, os, queue, random, time, threading
from config import RATE, CHANNELS, ROTATE_LLM_API_KEYS
from langchain_core.messages import ( 
    AIMessage, HumanMessage, SystemMessage, ToolMessage
)
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from sound_path import disfluencies_data, initial_responses_data, intermediate_responses_data
from utils import MicrophoneStream, Item, Order, Menu, StreamData, StreamTranscript, rotate_key


#################################
# ASSISTANT INTERACTION CLASSES #
#################################
class Agent:
    def __init__(self, model_name: str, tools: Dict[str, BaseTool]) -> None:
        self.model = ChatGroq(
            max_tokens=1000,
            model=model_name,
            temperature = 0.0,
            groq_api_key=os.getenv("GROQ_API_KEY"), 
        )
        self.available_tools = tools
        self.api_keys = os.getenv("GROQ_API_KEYS")
        if ROTATE_LLM_API_KEYS:
            if self.api_keys is None:
                raise ("To enable api key rotation, a list of groq api keys are required to be set in the `.env`.")
            else:
                self.api_keys = ast.literal_eval(self.api_keys)
        self.agent = self.model.bind_tools(list(tools.values()))
        self.messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
    def add_user_message(self, text:str):
        self.messages.append(HumanMessage(content=text))
    
    def invoke(self, text:str) -> Tuple[str, bool]:
        tries=0
        is_order_confirmed = False
        self.add_user_message(text)
        tool_call_identified = True
        while tool_call_identified:
            if ROTATE_LLM_API_KEYS:
                self.model.groq_api_key=rotate_key(tries)
            tries+=1
            print("Current try: ", tries)
            response: AIMessage = self.agent.invoke(self.messages)
            self.messages.append(response)
            for tool_call in response.tool_calls:
                if tool_call["name"]=="confirm_order":
                    is_order_confirmed = True
                selected_tool = self.available_tools[tool_call["name"]]
                tool_output = selected_tool.invoke(tool_call["args"])
                self.messages.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))
            if len(response.tool_calls) == 0:
                tool_call_identified = False
        return response.content, is_order_confirmed
    
class SocketManager:
    def __init__(self, host: str="localhost", port: int=8000, entry: str="ws_receive"):
        self.host = host
        self.port = port
        self.entry = entry
        self.url = f"ws://{host}:{port}/{entry}"
        self.ws = None
    
    def connect(self):
        try:
            self.ws = websocket.create_connection(self.url)
            print("Connected to WebSocket server.")
        except Exception as e:
            print(f"Failed to connect: {e}")
    
    def send_message(self, message: dict|BaseModel):
        if not self.ws:
            self.connect()
        try:
            if not isinstance(message, dict):
                message = message.model_dump()
            self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"Failed to send message: {e}")

class AudioManager:
    def __init__(
        self, 
        model_name: str, 
        disfluence_folder: str = "disfluencies", 
        initial_response_folder: str = "responses/initial_responses", 
        intermediate_response_folder: str = "responses/intermediate_responses"
    ) -> None:
        self.model_name = model_name
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.base_url = "https://api.deepgram.com/v1/speak"
        self.params = {"model": model_name, "encoding": "mp3"}
        self.headers = {"Content-Type": "application/json", "Authorization": f"Token {self.api_key}"}

        self.disfluencies: Dict[str, AudioSegment] = {}
        self.initial_responses: Dict[str, AudioSegment] = {}
        self.intermediate_responses: Dict[str, Dict[str, AudioSegment]] = {}

        self.__load_disfluencies__(disfluence_folder)
        self.__load_initial_responses__(initial_response_folder)
        self.__load_intermediate_responses__(intermediate_response_folder)

        self.audio_queue = queue.Queue()
        self.playback_thread = threading.Thread(target=self.__audio_playback_worker__, daemon=True)
        self.playback_thread.start()
        
    def __load_disfluencies__(self, folder: str):
        for filler, filename in disfluencies_data.items():
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                self.disfluencies[filler] = AudioSegment.from_file(path, format="mp3")
            else:
                print(f"File {filename} not found in {folder}. Skipping {filler}.")

    def __load_initial_responses__(self, folder: str):
        for text, filename in initial_responses_data.items():
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                self.initial_responses[text] = AudioSegment.from_file(path, format="mp3")
            else:
                print(f"File {filename} not found in {folder}.")

    def __load_intermediate_responses__(self, folder: str):
        for category, responses in intermediate_responses_data.items():
            self.intermediate_responses[category] = {}
            for text, filename in responses.items():
                path = os.path.join(folder, category, filename)
                if os.path.isfile(path):
                    self.intermediate_responses[category][text] = AudioSegment.from_file(path, format="mp3")
                else:
                    print(f"File {filename} for {category} not found in {folder}.")

    def __audio_playback_worker__(self):
        while True:
            try:
                if self.audio_queue:
                    audio_segment, delay = self.audio_queue.get()
                    if delay:
                        time.sleep(delay)
                    play(audio_segment)
                    self.audio_queue.task_done()
            except:
                pass
    
    def __add_to_queue__(self, audio_segment: AudioSegment, delay: Optional[float]=None):
        self.audio_queue.put((audio_segment, delay))
    
    def play_disfluent_filler(self):
        if random.choice([True, True]):
            choice = random.choice(list(self.disfluencies.keys()))
            self.__add_to_queue__(self.disfluencies[choice], 1)
    
    def play_initial_response(self) -> str:
        choice = random.choice(list(self.initial_responses.keys()))
        self.__add_to_queue__(self.initial_responses[choice])
        return choice

    def play_intermediate_response(self, category: str) -> str:
        if category in self.intermediate_responses:
            choice = random.choice(list(self.intermediate_responses[category].keys()))
            self.__add_to_queue__(self.intermediate_responses[category][choice])
            return choice
        else:
            print(f"Category {category} not found.")
            return ""
        
    def speak(self, text: str) -> None:
        try:
            with requests.post(self.base_url, stream=False, json={"text": text}, params=self.params, headers=self.headers) as r:
                audio_segment = AudioSegment.from_mp3(BytesIO(r.content))
                self.__add_to_queue__(audio_segment)
        except Exception as e:
            print(f"Exception in speak: {e}")

    def wait_until_done(self) -> bool:
        try:
            self.audio_queue.join()
            return True
        except queue.Empty:
            return False

class ConversationManager:
    def __init__(self, audio_manager: AudioManager, socket_manager: SocketManager, agent: Agent):
        self.agent = agent
        self.transcriber = None
        self.is_speaking = False
        self.microphone_stream = None
        self.audio_manager = audio_manager
        self.socket_manager = socket_manager
        # self.pause_transcription = threading.Event()
        aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")

    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        print(f"Starting up assistant with session id: {session_opened.session_id}")
        self.socket_manager.send_message(StreamTranscript(is_initiated=True).model_dump())
        self.audio_manager.play_initial_response()

    def on_data(self, transcript: aai.RealtimeTranscript):
        # if self.pause_transcription.is_set():
        #     return
        # self.socket_manager.send_message(StreamTranscript(text=transcript.text).model_dump())
        if not transcript.text:
            return
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            print("User:", transcript.text)
            self.socket_manager.send_message(StreamTranscript(text=transcript.text, is_partial=False).model_dump())
            self.process_response(transcript.text)

    def on_error(self, error: aai.RealtimeError):
        print("An error occurred:", error)

    def on_close(self):
        print("Closing Session")

    def process_response(self, text: str):
        # self.pause_transcription.set()
        self.microphone_stream.pause()
        
        response, order_confirmed = self.agent.invoke(text)
        self.audio_manager.speak(response)
        self.audio_manager.wait_until_done()
        
        if order_confirmed:
            self.microphone_stream.close()
            self.transcriber.close()
        self.microphone_stream.resume()
        # self.pause_transcription.clear()
       
    def run(self):
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=16_000,
            on_data=self.on_data,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
        )
        self.transcriber.connect()
        
        self.microphone_stream = MicrophoneStream(sample_rate=16_000)
        self.transcriber.stream(self.microphone_stream)
        
        self.transcriber.close()
        self.microphone_stream.close()

class WakeWordDetector:
    def __init__(self, model_id: str="openai/whisper-tiny.en", cache_dir: str="downloads") -> None:
        self.processor = WhisperProcessor.from_pretrained(model_id, cache_dir=cache_dir)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_id, cache_dir=cache_dir)
    
    def detect(self, wake_words: List[str], wait_time: float=1.25) -> bool:
        print("Listening for wake word...", end="\r")
        audio_data = sd.rec(int(wait_time * RATE), samplerate=RATE, channels=CHANNELS)
        sd.wait()
        
        audio_data = audio_data.flatten()
        audio_data = audio_data.astype(np.float32)
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0
        
        input_features = self.processor(audio_data, sampling_rate=RATE, return_tensors="pt").input_features
        predicted_ids = self.model.generate(input_features)
        transcription = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

        if any (wake_word in transcription.strip().lower() for wake_word in wake_words):
            print("Wake word detected")
            return True
        return False



###############################
# ASSISTANT DATA TOOL CLASSES #
###############################
class KFCMenu:
    def __init__(self, audio_manager: AudioManager, socket_manager: SocketManager, beverages: Optional[List[Item]] = None, main_dishes: Optional[List[Item]] = None, side_dishes: Optional[List[Item]] = None) -> None:
        self.beverages=beverages
        self.main_dishes=main_dishes
        self.side_dishes=side_dishes
        self.audio_manager = audio_manager
        self.socket_manager = socket_manager
        self.stream_data = StreamData(
            menu=[
                Menu(menu_type="beverage", items=self.beverages),
                Menu(menu_type="main_dish", items=self.main_dishes),
                Menu(menu_type="side_dish", items=self.side_dishes),
            ]
        )
    
    def get_main_dishes(self) -> str:
        self.audio_manager.play_intermediate_response("get_main_dishes")
        stream_data = self.stream_data
        stream_data.action="get_main_dishes"
        self.socket_manager.send_message(stream_data.model_dump())
        dishes = []
        for dish in self.main_dishes:
            d = dish.model_dump(exclude=["image_url_path"])
            d['price_per_unit'] = f"${dish.price_per_unit}"
            dishes.append(d)
        return yaml.dump(dishes)

    def get_sides(self) -> str:
        self.audio_manager.play_intermediate_response("get_sides")
        stream_data = self.stream_data
        stream_data.action="get_sides"
        self.socket_manager.send_message(stream_data.model_dump())
        dishes = []
        for dish in self.side_dishes:
            d = dish.model_dump(exclude=["image_url_path"])
            d['price_per_unit'] = f"${dish.price_per_unit}"
            dishes.append(d)
        return yaml.dump(dishes)

    def get_beverages(self) -> str:
        self.audio_manager.play_intermediate_response("get_beverages")
        stream_data = self.stream_data
        stream_data.action="get_beverages"
        self.socket_manager.send_message(stream_data.model_dump())
        beverages = []
        for bev in self.beverages:
            b = bev.model_dump(exclude=["image_url_path"])
            b['price_per_unit'] = f"${bev.price_per_unit}"
            beverages.append(b)
        return yaml.dump(beverages)
    
    def get_item_by_name(self, name: str) -> Optional[Item]:
        for category in [self.main_dishes, self.side_dishes, self.beverages]:
            for item in category:
                if name == item.name:
                    return item
        return None
    
class OrderCart(KFCMenu):
    
    def __init__(self, audio_manager: AudioManager, socket_manager: SocketManager, beverages: Optional[List[Item]] = None, main_dishes: Optional[List[Item]] = None, side_dishes: Optional[List[Item]] = None) -> None:
        super().__init__(audio_manager, socket_manager, beverages, main_dishes, side_dishes)
        self.orders: List[Order] = []
    
    def add_item(self, item_name: str, quantity: int = 1) -> str:
        is_new = True
        item = self.get_item_by_name(item_name)
        if item is None:
            return yaml.dump({"error": "Item not found from the menu."})
        
        self.audio_manager.play_intermediate_response("add_item")
        
        result = dict(name=item.name, total_quantity=quantity, price_per_unit=f"${item.price_per_unit}")
        for i, order in enumerate(self.orders):
            if order.name == item_name:
                self.orders[i].total_quantity += quantity
                result['total_quantity'] = self.orders[i].total_quantity
                result['price_per_unit'] = f"${order.price_per_unit}"
                is_new = False
                break
        if is_new:
            self.orders.append(Order(name=item_name, price_per_unit=item.price_per_unit, total_quantity=quantity))
        
        stream_data = self.stream_data
        stream_data.action="add_item"
        stream_data.cart = self.orders
        stream_data.update()
        self.socket_manager.send_message(stream_data.model_dump())
        
        return yaml.dump(result)

    def remove_item(self, item_name: str, quantity: int = 1, remove_all: bool = False) -> str:
        result = dict(name=item_name, action="not_found")
        for i, order in enumerate(self.orders):
            if order.name == item_name:
                self.audio_manager.play_intermediate_response("remove_item")
                if (order.total_quantity <= quantity) or remove_all:
                    self.orders.pop(i)
                    result['action'] = "fully_removed"
                else:
                    self.orders[i].total_quantity -= quantity
                    result['action'] = "partially_removed"
                    result['remaining_quantity'] = self.orders[i].total_quantity
                break
        
        stream_data = self.stream_data
        stream_data.cart = self.orders
        stream_data.action="remove_item"
        stream_data.update()
        self.socket_manager.send_message(stream_data.model_dump())
            
        return yaml.dump(result)

    def modify_quantity(self, item_name: str, new_quantity: int) -> str:
        result = dict(name=item_name, action="not_found")
        for order in self.orders:
            if order.name == item_name:
                self.audio_manager.play_intermediate_response("modify_quantity")
                if new_quantity <= 0:
                    self.orders.remove(order)
                    result['action'] = "removed"
                else:
                    order.total_quantity = new_quantity
                    result['action'] = "updated"
                    result['new_quantity'] = new_quantity
                break
            
        stream_data = self.stream_data
        stream_data.cart = self.orders
        stream_data.action="modify_quantity"
        stream_data.update()
        self.socket_manager.send_message(stream_data.model_dump())
        
        return yaml.dump(result)

    def confirm_order(self) -> str:
        self.audio_manager.play_intermediate_response("confirm_order")
        confirmation = {
            "status": "confirmed",
            "message": "Your order has been confirmed.",
            "items": [{"name": order.name, "quantity": order.total_quantity} for order in self.orders]
        }
        
        stream_data = self.stream_data
        stream_data.cart = self.orders
        stream_data.action="confirm_order"
        stream_data.update()
        self.socket_manager.send_message(stream_data.model_dump())
        
        self.reset_cart()
        return yaml.dump(confirmation)

    def get_cart_contents(self) -> str:
        contents = []
        total_price = 0
        for order in self.orders:
            total_price += (order.total_quantity * order.price_per_unit)
            contents.append({"name": order.name, "quantity": order.total_quantity})
            
        stream_data = self.stream_data
        stream_data.cart = self.orders
        stream_data.action="get_cart_contents"
        stream_data.update()
        self.socket_manager.send_message(stream_data.model_dump())    
            
        if contents:
            return f"{yaml.dump(contents)}\n\nTotal Price of items: ${total_price}"
        return "The cart is currently empty."

    def reset_cart(self) -> None:
        self.orders = []





            




