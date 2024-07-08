import ast, yaml
import numpy as np
from io import BytesIO
import sounddevice as sd
import assemblyai as aai
from pydub import AudioSegment
from pydub.playback import play
from config import SYSTEM_PROMPT
from langchain_groq import ChatGroq
from langchain_core.tools import BaseTool
from assistant.utils import StreamData, Menu
import requests, os, queue, random, time, threading
from langchain_core.messages import ( 
    AIMessage, HumanMessage, SystemMessage, ToolMessage
)
from typing import List, Dict, Optional, Tuple, Callable
from assemblyai.extras import AssemblyAIExtrasNotInstalledError
from config import ( RATE, CHANNELS, ROTATE_LLM_API_KEYS,
    ENABLE_LLM_VERBOSITY, ENABLE_STT_VERBOSITY, ENABLE_TTS_VERBOSITY
)
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from sound_path import disfluencies_data, initial_responses_data, intermediate_responses_data



#################################
# ASSISTANT INTERACTION CLASSES #
#################################
class Agent:
    """
    Represents an AI agent capable of processing messages and invoking tools.

    This class manages interactions with a language model, handles tool calls,
    and maintains conversation history.
    """
    def __init__(self, model_name: str, tools: Dict[str, BaseTool], menu_items: List[Menu]) -> None:
        """
        Initialize the Agent with a specified model and set of tools.

        Args:
            model_name (str): The name of the language model to use.
            tools (Dict[str, BaseTool]): A dictionary of available tools.
            menu_items: List[Menu]: A list of the menu items available to be added to the system prompt.
        """
        self.api_keys = [os.getenv("GROQ_API_KEY")]
        self.model = ChatGroq(
            max_tokens=1000,
            model=model_name,
            temperature = 0.0,
            groq_api_key=self.api_keys[0], 
        )
        self.available_tools = tools
        self.agent = self.model.bind_tools(list(tools.values()))

        if ROTATE_LLM_API_KEYS:
            api_keys = os.getenv("GROQ_API_KEYS")
            if api_keys is None:
                raise ("To enable api key rotation, a list of groq api keys are required to be set in the `.env`.")
            else:
                self.api_keys = ast.literal_eval(api_keys)
        
        if ENABLE_LLM_VERBOSITY:
            print(f"LLM: Starting Agent with api_keys: {self.api_keys}")    
        
        self.format_system_prompt(menu_items)
    
    def rotate_key(self, keys: List[str], idx: int) -> str:
        return keys[idx%len(keys)]
      
    def format_system_prompt(self, menu_items: List[Menu]):
        if menu_items is None:
            raise ("LLM: Agent requires the menu items added to its system prompt. Please call pass parameter to `menu_items`.")
        else:
            string = ""
            for m in menu_items:
                if m.menu_type=="main_dishes":
                    string += "Available Main Dishes:\n"
                    for i, item in enumerate(m.items):
                        string += f"\t{i+1}. Name: {item.name}, Price per unit: {item.price_per_unit}\n"
                    string+="\n"
                elif m.menu_type=="side_dishes":
                    string += "Available Side Dishes:\n"
                    for i, item in enumerate(m.items):
                        string += f"\t{i+1}. Name: {item.name}, Price per unit: {item.price_per_unit}\n"
                    string+="\n"
                elif m.menu_type=="beverages":
                    string += "Available Beverages:\n"
                    for i, item in enumerate(m.items):
                        string += f"\t{i+1}. Name: {item.name}, Price per unit: {item.price_per_unit}\n"
                    string+="\n"
                    
            self.system_prompt = SYSTEM_PROMPT.format(menu=string)
            self.messages = [SystemMessage(content=self.system_prompt)]
        
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
                self.model.groq_api_key=self.rotate_key(self.api_keys, tries)
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
        
class MicrophoneStream:
    def __init__(
        self,
        sample_rate: int = 44_100,
    ):
        """
        Creates a stream of audio from the microphone.

        Args:
            sample_rate: The sample rate to record audio at.
        """
        self.sample_rate = sample_rate
        self._chunk_size = int(self.sample_rate * 0.1)
        
        self._stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self._chunk_size,
            callback=self._audio_callback
        )

        self._buffer = []
        self._open = True
        self._paused = False
        self._pause_lock = threading.Lock()
    
    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        with self._pause_lock:
            if not self._paused:
                self._buffer.append(indata.copy())

    def __iter__(self):
        """
        Returns the iterator object.
        """
        self._stream.start()
        return self

    def __next__(self):
        """
        Reads a chunk of audio from the microphone.
        """
        if not self._open:
            raise StopIteration

        try:
            with self._pause_lock:
                if self._paused:
                    return np.zeros(self._chunk_size, dtype='int16').tobytes()  # Return silence when paused
                while not self._buffer:
                    if not self._open:
                        raise StopIteration
                return self._buffer.pop(0).tobytes()
        except KeyboardInterrupt:
            raise StopIteration

    def close(self):
        """
        Closes the stream.
        """
        self._open = False
        self._stream.stop()
        self._stream.close()

    def pause(self):
        """
        Pauses the recording process.
        """
        with self._pause_lock:
            self._paused = True

    def resume(self):
        """
        Resumes the recording process.
        """
        with self._pause_lock:
            self._paused = False

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


            




