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
import requests, os, queue, random, time, threading
from langchain_core.messages import ( 
    AIMessage, HumanMessage, SystemMessage, ToolMessage
)
from typing import List, Dict, Optional, Tuple, Callable
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from config import ( RATE, CHANNELS, ROTATE_LLM_API_KEYS, ENABLE_SOCKET_VERBOSITY,
    ENABLE_LLM_VERBOSITY, ENABLE_STT_VERBOSITY, ENABLE_TOOL_VERBOSITY, ENABLE_TTS_VERBOSITY
)
from sound_path import disfluencies_data, initial_responses_data, intermediate_responses_data
from utils import MicrophoneStream, Item, Order, Menu, StreamData, StreamMessages, rotate_key


#################################
# ASSISTANT INTERACTION CLASSES #
#################################
class Agent:
    """
    Represents an AI agent capable of processing messages and invoking tools.

    This class manages interactions with a language model, handles tool calls,
    and maintains conversation history.
    """
    def __init__(self, model_name: str, tools: Dict[str, BaseTool]) -> None:
        """
        Initialize the Agent with a specified model and set of tools.

        Args:
            model_name (str): The name of the language model to use.
            tools (Dict[str, BaseTool]): A dictionary of available tools.
        """
        self.api_keys = [os.getenv("GROQ_API_KEY")]
        self.model = ChatGroq(
            max_tokens=1000,
            model=model_name,
            temperature = 0.0,
            groq_api_key=self.api_keys[0], 
        )
        self.available_tools = tools
        if ROTATE_LLM_API_KEYS:
            api_keys = os.getenv("GROQ_API_KEYS")
            if api_keys is None:
                raise ("To enable api key rotation, a list of groq api keys are required to be set in the `.env`.")
            else:
                self.api_keys = ast.literal_eval(api_keys)
        if ENABLE_LLM_VERBOSITY:
            print(f"LLM: Starting Agent with api_keys: {self.api_keys}")    
        self.agent = self.model.bind_tools(list(tools.values()))
        self.messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
    def add_user_message(self, text:str):
        """
        Add a user message to the conversation history.

        Args:
            text (str): The user's message.
        """
        self.messages.append(HumanMessage(content=text))
    
    def invoke(self, text:str) -> Tuple[str, bool]:
        """
        Process a user input, potentially make tool calls, and generate a response.

        Args:
            text (str): The user's input text.

        Returns:
            Tuple[str, bool]: The agent's response and whether an order was confirmed.
        """
        tries=0
        is_order_confirmed = False
        self.add_user_message(text)
        tool_call_identified = True
        if ENABLE_LLM_VERBOSITY:
            print(f"LLM INPUT: {text}")
        
        while tool_call_identified:
            if ROTATE_LLM_API_KEYS:
                self.model.groq_api_key=rotate_key(self.api_keys, tries)
            tries+=1
            response: AIMessage = self.agent.invoke(self.messages)
            self.messages.append(response)
            
            for tool_call in response.tool_calls:
                if ENABLE_LLM_VERBOSITY:
                    print(f"LLM TOOL CALL: {tool_call['name']} - {tool_call['args']}")
                if tool_call["name"]=="confirm_order":
                    is_order_confirmed = True
                
                selected_tool = self.available_tools[tool_call["name"]]
                tool_output = selected_tool.invoke(tool_call["args"])
                if ENABLE_LLM_VERBOSITY:
                    print(f"LLM TOOL OUTPUT: {tool_output}")
                self.messages.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))
            
            if len(response.tool_calls) == 0:
                tool_call_identified = False
                if ENABLE_LLM_VERBOSITY:
                    print(f"LLM RESPONSE: {response.content}")
        return response.content, is_order_confirmed
    
class SocketManager:
    """
    Manages WebSocket connections for real-time communication.

    This class handles connecting to a WebSocket server and sending messages.
    """
    def __init__(self, host: str="localhost", port: int=8000, entry: str="ws_receive"):
        """
        Initialize the SocketManager with connection details.

        Args:
            host (str): The WebSocket server host.
            port (int): The server port.
            entry (str): The entry point for the WebSocket connection.
        """
        self.host = host
        self.port = port
        self.entry = entry
        self.url = f"ws://{host}:{port}/{entry}"
        self.ws = None
        self.connect()
    
    def connect(self):
        """Establish a connection to the WebSocket server."""
        try:
            self.ws = websocket.create_connection(self.url, timeout=2)
            if ENABLE_SOCKET_VERBOSITY:
                print("Connected to WebSocket server.")
        except Exception as e:
            if ENABLE_SOCKET_VERBOSITY:
                print(f"Failed to connect: {e}")
    
    def send_message(self, message: dict|BaseModel):
        """
        Send a message through the WebSocket connection.

        Args:
            message (dict | BaseModel): The message to send.
        """
        if not self.ws:
            self.connect()
        try:
            if not isinstance(message, dict):
                message = message.model_dump()
            if ENABLE_SOCKET_VERBOSITY:
                print(f"SOCKET: {message}")
            self.ws.send(json.dumps(message))
        except Exception as e:
            if ENABLE_SOCKET_VERBOSITY:
                print(f"Failed to send message: {e}")

class AudioManager:
    """
    Manages audio playback and text-to-speech functionality.

    This class handles loading and playing audio files, as well as
    generating speech from text using an API.
    """
    def __init__(
        self, 
        model_name: str, 
        disfluence_folder: str = "disfluencies", 
        initial_response_folder: str = "responses/initial_responses", 
        intermediate_response_folder: str = "responses/intermediate_responses"
    ) -> None:
        """
        Initialize the AudioManager with necessary audio resources.

        Args:
            model_name (str): The name of the text-to-speech model.
            disfluence_folder (str): Path to disfluency audio files.
            initial_response_folder (str): Path to initial response audio files.
            intermediate_response_folder (str): Path to intermediate response audio files.
        """
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
        """Play a random disfluency audio."""
        if random.choice([True, True]):
            choice = random.choice(list(self.disfluencies.keys()))
            if ENABLE_TTS_VERBOSITY:
                print(f"TTS PRE-REC: {choice}")
            self.__add_to_queue__(self.disfluencies[choice], 1)
    
    def play_initial_response(self) -> str:
        """
        Play a random initial response audio.

        Returns:
            str: The text of the played response.
        """
        choice = random.choice(list(self.initial_responses.keys()))
        if ENABLE_TTS_VERBOSITY:
            print(f"TTS PRE-REC: {choice}")
        self.__add_to_queue__(self.initial_responses[choice])
        return choice

    def play_intermediate_response(self, category: str) -> str:
        """
        Play a random intermediate response audio from a specific category of tool invocation.

        Args:
            category (str): The category of the intermediate response.

        Returns:
            str: The text of the played response.
        """
        if category in self.intermediate_responses:
            choice = random.choice(list(self.intermediate_responses[category].keys()))
            if ENABLE_TTS_VERBOSITY:
                print(f"TTS PRE-REC: {choice}")
            self.__add_to_queue__(self.intermediate_responses[category][choice])
            return choice
        else:
            if ENABLE_TTS_VERBOSITY:
                print(f"TTS: Category {category} not found.")
            return ""
        
    def speak(self, text: str) -> None:
        """
        Generate and play speech from the given text.

        Args:
            text (str): The text to convert to speech.
        """
        try:
            with requests.post(self.base_url, stream=False, json={"text": text}, params=self.params, headers=self.headers) as r:
                audio_segment = AudioSegment.from_mp3(BytesIO(r.content))
                if ENABLE_TTS_VERBOSITY:
                    print(f"TTS LLM-SPEAK: {text}")
                self.__add_to_queue__(audio_segment)
        except Exception as e:
            if ENABLE_TTS_VERBOSITY:
                print(f"TTS LLM-SPEAK: Exception in speak: {e}")

    def wait_until_done(self) -> bool:
        try:
            self.audio_queue.join()
            return True
        except queue.Empty:
            return False

class ConversationManager:
    """
    Manages the conversation flow, including speech-to-text transcription.

    This class handles real-time transcription of audio and triggers
    appropriate callbacks for conversation management.
    """
    def __init__(self):
        """Initialize the ConversationManager."""
        self.transcriber = None
        self.is_speaking = False
        self.microphone_stream = None
        aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")

    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        if ENABLE_STT_VERBOSITY:
            print(f"STT: Starting up assistant with session id: {session_opened.session_id}")
        if self.open_callback:
            self.open_callback()
       
    def on_data(self, transcript: aai.RealtimeTranscript):
        if not transcript.text:
            return
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            close = False
            if ENABLE_STT_VERBOSITY:
                print(f"STT: {transcript.text}")
            
            self.microphone_stream.pause()
            
            if self.data_callback:
                close = self.data_callback(transcript.text)   
            if close:
                self.microphone_stream.close()
                self.transcriber.close()
                if ENABLE_STT_VERBOSITY:
                    print("STT: Closed connection for listening.")
        
            self.microphone_stream.resume()

    def on_error(self, error: aai.RealtimeError):
        if ENABLE_STT_VERBOSITY:
            print("STT: An error occurred:", error)

    def on_close(self):
        if ENABLE_STT_VERBOSITY:
            print("STT: Closed connection for listening")
            
    def run(self, on_open: Optional[Callable]=None, on_data: Optional[Callable]=None):
        """
        Start the conversation management process.

        Args:
            on_open (Optional[Callable]): Callback function when the connection is opened.
            on_data (Optional[Callable]): Callback function when new transcription data is received.
        """
        self.open_callback=on_open
        self.data_callback=on_data
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=16_000,
            on_data=self.on_data,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
        )
        self.transcriber.connect()
        if ENABLE_STT_VERBOSITY:
            print("STT: Connected to assembly ai socket endpoint.")
        
        self.microphone_stream = MicrophoneStream(sample_rate=16_000)
        self.transcriber.stream(self.microphone_stream)
        
        self.transcriber.close()
        self.microphone_stream.close()

class WakeWordDetector:
    """
    Detects wake words in audio input.

    This class uses a pre-trained model to identify specific wake words
    in audio streams.
    """
    def __init__(self, model_id: str="openai/whisper-tiny.en", cache_dir: str="downloads") -> None:
        """
        Initialize the WakeWordDetector with a specified model.

        Args:
            model_id (str): The ID of the pre-trained model to use.
            cache_dir (str): Directory to cache the downloaded model.
        """
        self.processor = WhisperProcessor.from_pretrained(model_id, cache_dir=cache_dir)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_id, cache_dir=cache_dir)
    
    def detect(self, wake_words: List[str], wait_time: float=1.25) -> bool|str:
        """
        Listen for and detect wake words in audio input.

        Args:
            wake_words (List[str]): List of wake words to detect.
            wait_time (float): Duration to listen for wake words.

        Returns:
            bool | str: False if no wake word detected, or the transcribed audio if detected.
        """
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
            return transcription.strip().lower()
        return False



###############################
# ASSISTANT DATA TOOL CLASSES #
###############################
class KFCMenu:
    """
    Represents the KFC menu and provides methods to access menu items.

    This class manages the available menu items and their details.
    """
    def __init__(self, audio_manager: AudioManager, socket_manager: SocketManager, beverages: Optional[List[Item]] = None, main_dishes: Optional[List[Item]] = None, side_dishes: Optional[List[Item]] = None) -> None:
        """
        Initialize the KFCMenu with menu items and necessary managers.

        Args:
            audio_manager (AudioManager): The AudioManager instance.
            socket_manager (SocketManager): The SocketManager instance.
            beverages (Optional[List[Item]]): List of available beverages.
            main_dishes (Optional[List[Item]]): List of available main dishes.
            side_dishes (Optional[List[Item]]): List of available side dishes.
        """
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
            
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'get_main_dishes':", yaml.dump(dishes))
            
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
            
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'get_sides':", yaml.dump(dishes))
            
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
            
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'get_beverages':", yaml.dump(beverages))
            
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
        
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'add_item':", yaml.dump(result))
        
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
            
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'remove_item':", yaml.dump(result))
            
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
        
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'modify_quantity':", yaml.dump(result))
        
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
        
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'confirm_order':", yaml.dump(confirmation))
        
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
            
        if ENABLE_TOOL_VERBOSITY:
            print("TOOL 'get_cart_contents':", f"{yaml.dump(contents)}\n\nTotal Price of items: ${total_price}")    
            
        if contents:
            return f"{yaml.dump(contents)}\n\nTotal Price of items: ${total_price}"
        return "The cart is currently empty."

    def reset_cart(self) -> None:
        self.orders = []




'''
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
        if ENABLE_STT_VERBOSITY:
            print(f"STT: Starting up assistant with session id: {session_opened.session_id}")
        response = self.audio_manager.play_initial_response()
        self.socket_manager.send_message(StreamMessages(
            role="assistant",
            content=response, is_initiated=True
        ).model_dump())

    def on_data(self, transcript: aai.RealtimeTranscript):
        # if self.pause_transcription.is_set():
        #     return
        if not transcript.text:
            return
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            self.process_response(transcript.text)

    def on_error(self, error: aai.RealtimeError):
        print("An error occurred:", error)

    def on_close(self):
        print("Closing Session")

    def process_response(self, text: str):
        # self.pause_transcription.set()
        if ENABLE_STT_VERBOSITY and not ENABLE_LLM_VERBOSITY:
            print(f"STT: {text}")
        self.socket_manager.send_message(StreamMessages(
            role="user",
            content=text, is_partial=False
        ).model_dump())
        
        self.microphone_stream.pause()
        
        response, order_confirmed = self.agent.invoke(text)
        self.audio_manager.speak(response)
        self.audio_manager.wait_until_done()
        
        if order_confirmed:
            self.microphone_stream.close()
            self.transcriber.close()
            if ENABLE_STT_VERBOSITY:
                print("STT: Closed connection for listening")
            
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
        if ENABLE_STT_VERBOSITY:
            print("STT: Connected to assembly ai socket endpoint.")
        
        self.microphone_stream = MicrophoneStream(sample_rate=16_000)
        self.transcriber.stream(self.microphone_stream)
        
        self.transcriber.close()
        self.microphone_stream.close()
'''


            




