import wave
import ast, queue
import numpy as np
from io import BytesIO
import sounddevice as sd
import assemblyai as aai
from pydub import AudioSegment
from pydub.playback import play
from config import SYSTEM_PROMPT
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from web_builder.builder import WebViewApp
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
        
        
        
class Agent:
    """
    Represents an AI agent capable of processing messages and invoking tools.

    This class manages interactions with a language model, handles tool calls,
    and maintains conversation history. It is designed to work with a menu-based
    system, processing user inputs and potentially confirming orders.

    Attributes:
        api_keys (List[str]): List of API keys for the language model.
        model (ChatGroq): The language model used for generating responses.
        available_tools (Dict[str, BaseTool]): A dictionary of available tools.
        agent (Any): The agent bound with tools.
        system_prompt (str): The system prompt used to guide the agent's behavior.
        messages (List): The conversation history.
    """
    def __init__(self, model_name: str, tools: Dict[str, BaseTool], menu_items: List[Menu]) -> None:
        """
        Initialize the Agent with a specified model and set of tools.

        Args:
            model_name (str): The name of the language model to use.
            tools (Dict[str, BaseTool]): A dictionary of available tools.
            menu_items (List[Menu]): A list of the menu items available to be added to the system prompt.

        Raises:
            ValueError: If API keys are not set correctly when rotation is enabled.
        """
        self.audio_manager = None
        self.available_tools = tools
        self.set_llm_engine(model_name)
        self.agent = self.model.bind_tools(list(tools.values()))
        
        if ENABLE_LLM_VERBOSITY:
            print(f"LLM: Starting Agent with api_keys: {self.api_keys}")    
        
        self.format_system_prompt(menu_items)
        
    def update_audio_manager(self, audio_manager: AudioManager):
        self.audio_manager = audio_manager
    
    def set_llm_engine(self, model_name: str):
        self.backend = "oai"
        if "gpt" in model_name:
            self.api_keys = [os.getenv("OPENAI_API_KEY")]
            self.model = ChatOpenAI(
                max_tokens=1500,
                model=model_name,
                temperature = 0.1,
                api_key=self.api_keys[0]
            )
            api_keys = os.getenv("OPENAI_API_KEYS")
        else:
            self.backend = "groq"
            self.api_keys = [os.getenv("GROQ_API_KEY")]
            self.model = ChatGroq(
                max_tokens=1500,
                model=model_name,
                temperature = 0.1,
                api_key=self.api_keys[0], 
            )
            api_keys = os.getenv("GROQ_API_KEYS")
        
        if ROTATE_LLM_API_KEYS:
            if api_keys is None:
                if self.backend=="oai":
                    raise ("To enable api key rotation, a list of api keys are required to be set in the `.env`. `OPENAI_API_KEYS=['api-key1', 'api-key2']`")
                else:
                    raise ("To enable api key rotation, a list of api keys are required to be set in the `.env`. `GROQ_API_KEYS=['api-key1', 'api-key2']`")
            else:
                self.api_keys = ast.literal_eval(api_keys)
            
    
    def rotate_key(self, keys: List[str], idx: int):
        key = keys[idx%len(keys)]
        if self.backend=="oai":
            self.model.openai_api_key=key
        else:
            self.model.groq_api_key=key
      
    def format_system_prompt(self, menu_items: List[Menu]):
        """
        Format the system prompt with the provided menu items.

        Args:
            menu_items (List[Menu]): List of menu items to be formatted into the system prompt.

        Raises:
            ValueError: If menu_items is None.
        """
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

        This method adds the user's input to the conversation history, invokes the
        language model, processes any tool calls, and returns the final response
        along with an order confirmation flag.

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
                self.rotate_key(self.api_keys, tries)
            tries+=1
            if self.audio_manager is not None:
                self.audio_manager.play_disfluent_filler()
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

       
       
        
class MicrophoneStream:
    """
    A class that provides a streaming interface for microphone input.

    This class captures audio from the microphone, buffers it, and provides
    methods to stream the audio data. It supports pausing and resuming the
    audio capture, as well as writing the audio to WAV files.

    Attributes:
        sample_rate (int): The sample rate of the audio capture.
        chunk_size (int): The size of each audio chunk in frames.
        file_duration (int): The duration of each WAV file in seconds.

    """
    def __init__(self, sample_rate: int=44100, chunk_size: int=4410, file_duration: int=5):
        """
        Initialize the MicrophoneStream.

        Args:
            sample_rate (int): The sample rate of the audio capture. Defaults to 44100.
            chunk_size (int): The size of each audio chunk in frames. Defaults to 4410.
            file_duration (int): The duration of each WAV file in seconds. Defaults to 5.
        """
        self.file_index = 0
        self.frames_written = 0
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.audio_buffer = queue.Queue()
        self.file_duration = file_duration
        self.stream = sd.InputStream(
            channels=1,
            blocksize=self.chunk_size,
            samplerate=self.sample_rate,
            callback=self.__audio_callback__
        )

        self.stream.start()
        self._open = True
        self._paused = False
        if ENABLE_STT_VERBOSITY:
            print("STT: Audio stream started.")
        self.__prepare_new_file__()
    
    def __prepare_new_file__(self):
        """
        Prepare a new WAV file for writing audio data.
        """
        self.current_file = wave.open(f"part_{self.file_index}.wav", 'wb')
        self.current_file.setnchannels(1)
        self.current_file.setsampwidth(2)  # Assuming 16-bit audio
        self.current_file.setframerate(self.sample_rate)
        self.frames_written = 0
        self.file_index += 1
    
    def __audio_callback__(self, indata, frames, time, status):
        """
        Callback function for the sounddevice InputStream.

        Args:
            indata (numpy.ndarray): The input audio data.
            frames (int): The number of frames in the input.
            time (CData): The timestamps of the input.
            status (CallbackFlags): Indicates if an error occurred.
        """
        if status and ENABLE_STT_VERBOSITY:
            print(f"STT: Status: {status}")
        if not self._paused:
            audio_bytes = (indata * 32767).astype(np.int16).tobytes()
            self.audio_buffer.put(audio_bytes)
    
    def __write_to_file__(self):
        """
        Write buffered audio data to the current WAV file.
        """
        while not self.audio_buffer.empty():
            data = self.audio_buffer.get()
            self.current_file.writeframes(data)
            self.frames_written += len(data)
            if self.frames_written >= self.sample_rate * self.file_duration:
                self.current_file.close()
                self.__prepare_new_file__()
                
    def __read__(self, size):
        """
        Read a chunk of audio data from the buffer.

        Args:
            size (int): The number of bytes to read.

        Returns:
            bytes: The audio data.
        """
        requested_frames = size // 2
        frames_to_deliver = b''
        while len(frames_to_deliver) < size:
            if self._paused:
                return np.zeros(size, dtype='int16').tobytes()
            try:
                frames_to_deliver += self.audio_buffer.get(timeout=0.5)
            except queue.Empty:
                if not self._open:
                    break
                return np.zeros(size, dtype='int16').tobytes()
        return frames_to_deliver[:size]

    def __iter__(self):
        """
        Return the iterator object (self).

        Returns:
            MicrophoneStream: The iterator object.
        """
        return self

    def __next__(self):
        """
        Get the next chunk of audio data.

        Returns:
            bytes: The next chunk of audio data.

        Raises:
            StopIteration: If the stream is closed or no more data is available.
        """
        if not self._open:
            raise StopIteration
        
        data = self.__read__(self.chunk_size)
        if not data:
            raise StopIteration
        
        return data

    def close(self):
        """
        Close the audio stream and associated resources.
        """
        self.stream.stop()
        self.stream.close()
        self._open = False
        if ENABLE_STT_VERBOSITY:
            print("STT: Audio stream closed.")
        self.current_file.close()
        
    def run(self):
        """
        Run the main loop of the MicrophoneStream, continuously writing audio to file.
        """
        try:
            while self._open:
                self.__write_to_file__()
        finally:
            self.close()

    def pause(self):
        """
        Pause the audio capture.
        """
        self._paused = True
        if ENABLE_STT_VERBOSITY:
            print("STT: Recording paused.")

    def resume(self):
        """
        Resume the audio capture.
        """
        self._paused = False
        if ENABLE_STT_VERBOSITY:
            print("Recording resumed.")



class ConversationManager:
    """
    Manages the conversation flow, including speech-to-text transcription.

    This class handles real-time transcription of audio and triggers
    appropriate callbacks for conversation management. It uses AssemblyAI's
    real-time transcription API to convert speech to text and manages the
    microphone input stream.

    Attributes:
        transcriber (aai.RealtimeTranscriber): The AssemblyAI real-time transcriber.
        is_speaking (bool): Flag indicating whether the user is currently speaking.
        microphone_stream (MicrophoneStream): The microphone input stream.
        end_utterance_silence_threshold (Optional[int]): Threshold for end of utterance detection.
    """
    def __init__(self, end_utterance_silence_threshold: Optional[int]=None):
        """Initialize the ConversationManager.
        
        Args:
            end_utterance_silence_threshold (optional[str]): The threshold to control end of utterance detection.
        """
        self.transcriber = None
        self.is_speaking = False
        self.microphone_stream = None
        aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")
        self.end_utterance_silence_threshold = end_utterance_silence_threshold

    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        """
        Callback method triggered when the transcription session is opened.

        Args:
            session_opened (aai.RealtimeSessionOpened): Object containing session information.
        """
        if ENABLE_STT_VERBOSITY:
            print(f"STT: Starting up assistant with session id: {session_opened.session_id}")
        if self.open_callback:
            self.open_callback()
       
    def on_data(self, transcript: aai.RealtimeTranscript):
        """
        Callback method triggered when new transcription data is received.

        This method handles final transcripts, pauses the microphone stream,
        calls the data callback if set, and resumes the microphone stream.

        Args:
            transcript (aai.RealtimeTranscript): The received transcript data.
        """
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
        else:
            self.stream_callback(transcript.text)

    def on_error(self, error: aai.RealtimeError):
        """
        Callback method triggered when an error occurs during transcription.

        Args:
            error (aai.RealtimeError): The error that occurred.
        """
        if ENABLE_STT_VERBOSITY:
            print("STT: An error occurred:", error)

    def on_close(self):
        """
        Callback method triggered when the transcription session is closed.
        """
        if ENABLE_STT_VERBOSITY:
            print("STT: Closed connection for listening")
            
    def run(self, on_open: Optional[Callable]=None, on_data: Optional[Callable]=None, on_stream: Optional[Callable]=None, end_utterance_threshold: Optional[int]=None):
        """
        Start the conversation management process.

        This method initializes the transcriber, connects to the AssemblyAI API,
        and starts streaming audio from the microphone for transcription.

        Args:
            on_stream (Optional[Callable]): Callback function to call when transcript streams.
            on_open (Optional[Callable]): Callback function when the connection is opened.
            on_data (Optional[Callable]): Callback function when new transcription data is received.
        """
        self.open_callback=on_open
        self.data_callback=on_data
        self.stream_callback = on_stream
        
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=44_100,
            on_data=self.on_data,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
            end_utterance_silence_threshold=self.end_utterance_silence_threshold or end_utterance_threshold
        )
        self.transcriber.connect()
        if ENABLE_STT_VERBOSITY:
            print("STT: Connected to assembly ai socket endpoint.")
        
        try:
            self.microphone_stream = MicrophoneStream(sample_rate=16_000)
            self.transcriber.stream(self.microphone_stream)
        finally:
            self.transcriber.close()
            self.microphone_stream.close()
            if ENABLE_STT_VERBOSITY:
                print("STT: Transcriber and microphone is closing.")



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
        self.i=1
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
        print(f"Listening for wake word{'.'*self.i}", end="\r")
        if self.i>3:
            self.i=1
        self.i+=1
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
            print("STT DETECTOR: Wake word detected")
            return transcription.strip().lower()
        return False
