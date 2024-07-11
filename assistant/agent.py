
from datetime import datetime
import json
import wave, os
import threading
import ast, queue
import numpy as np
from io import BytesIO
import sounddevice as sd
import assemblyai as aai
from pydub import AudioSegment
from pydub.playback import play
from config import SYSTEM_PROMPT
from assemblyai import RealtimeWord
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from assistant.utils import StreamData, Menu
import requests, os, queue, random, time, threading
from langchain_core.messages import ( 
    AIMessage, HumanMessage, SystemMessage, ToolMessage
)
from typing import List, Dict, Optional, Tuple, Callable
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from sound_path import disfluencies_data, initial_responses_data, intermediate_responses_data
from config import ( CHANNELS, ROTATE_LLM_API_KEYS, STT_END_OF_UTTERANCE_THRESHOLD, STT_MICROPHONE_BACKEND, 
    CONVERSATION_FOLDER, ENABLE_LLM_VERBOSITY, ENABLE_STT_VERBOSITY, ENABLE_TTS_VERBOSITY, 
    STT_MODEL_SAMPLE_RATE, WAKE_SAMPLE_RATE, AUTO_LISTEN_WITHOUT_CLOSE, STT_WORD_PROB_BOOSTS
)




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

        self.disfluence_index = 0
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
        # if random.choice([True, False]):
        l = list(self.disfluencies.keys())
        choice = l[self.disfluence_index%len(l)]
        self.disfluence_index+=1
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
        
    # def save_interaction(self):
    #     if not CONVERSATION_FILE_NAME:
    #         print("No file name specified for saving the conversation.")
    #         return

    #     try:
    #         messages = [{"role": msg.type, "content": msg.content} for msg in self.messages] if hasattr(self, 'messages') else []
            
    #         existing_data = []
    #         if os.path.exists(CONVERSATION_FILE_NAME):
    #             with open(CONVERSATION_FILE_NAME, 'r') as f:
    #                 existing_data = json.load(f)
    #             if not isinstance(existing_data, list):
    #                 existing_data = []
            
    #         if messages:
    #             existing_data.append(messages)
            
    #         with open(CONVERSATION_FILE_NAME, 'w') as f:
    #             json.dump(existing_data, f, indent=4)
    #         print(f"Successfully saved interaction to {CONVERSATION_FILE_NAME}")
        
    #     except json.JSONDecodeError:
    #         print(f"Error decoding existing JSON in {CONVERSATION_FILE_NAME}")
    #     except IOError as e:
    #         print(f"IOError when saving to {CONVERSATION_FILE_NAME}: {str(e)}")
    #     except Exception as e:
    #         print(f"Unexpected error when saving interaction: {str(e)}")
    
    def save_interaction(self):
        # Create the directory if it doesn't exist
        save_dir = CONVERSATION_FOLDER
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating directory {save_dir}: {str(e)}")
            return

        # Generate filename with current datetime
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat-{current_time}.json"
        full_path = os.path.join(save_dir, filename)

        try:
            # Check if self.messages exists and is iterable
            if not hasattr(self, 'messages'):
                print("Error: self.messages not found")
                return
            if not hasattr(self.messages, '__iter__'):
                print("Error: self.messages is not iterable")
                return

            # Prepare messages
            messages = [{"role": msg.type, "content": msg.content} for msg in self.messages]
            
            # Check if messages list is empty
            if not messages:
                print("No messages to save.")
                return

            # Save messages to file
            with open(full_path, 'w') as f:
                json.dump(messages, f, indent=4)
            print(f"Successfully saved interaction to {full_path}")

        except AttributeError as e:
            print(f"AttributeError: {str(e)}")
        except TypeError as e:
            print(f"TypeError when processing messages: {str(e)}")
        except json.JSONEncodeError as e:
            print(f"Error encoding messages to JSON: {str(e)}")
        except IOError as e:
            print(f"IOError when saving to {full_path}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error when saving interaction: {str(e)}")
        
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
    def __init__(self, sample_rate: int=44100, chunk_size: int=4410, file_duration: int=5):
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
            callback=self.audio_callback
        )

        self.stream.start()
        self._open = True
        if ENABLE_STT_VERBOSITY:
            print("STT: Audio stream started.")
        self.prepare_new_file()
    
    def prepare_new_file(self):
        self.current_file = wave.open(f"part_{self.file_index}.wav", 'wb')
        self.current_file.setnchannels(1)
        self.current_file.setsampwidth(2)  # Assuming 16-bit audio
        self.current_file.setframerate(self.sample_rate)
        self.frames_written = 0
        self.file_index += 1
    
    def audio_callback(self, indata, frames, time, status):
        if status and ENABLE_STT_VERBOSITY:
            print(f"STT: Status: {status}")
        audio_bytes = (indata * 32767).astype(np.int16).tobytes()
        self.audio_buffer.put(audio_bytes)
    
    def write_to_file(self):
        while not self.audio_buffer.empty():
            data = self.audio_buffer.get()
            self.current_file.writeframes(data)
            self.frames_written += len(data)
            if self.frames_written >= self.sample_rate * self.file_duration:
                self.current_file.close()
                self.prepare_new_file()
                
    def read(self, size):
        requested_frames = size // 2
        frames_to_deliver = b''
        while len(frames_to_deliver) < size:
            frames_to_deliver += self.audio_buffer.get()
        return frames_to_deliver[:size]

    def __iter__(self):
        return self

    def __next__(self):
        if self._open:
            try:
                data = self.read(self.chunk_size)
                if data:
                    return data
                else:
                    raise StopIteration
            except queue.Empty:
                raise StopIteration
        else:
            raise StopIteration

    def close(self):
        self.stream.stop()
        self.stream.close()
        self._open = False
        if ENABLE_STT_VERBOSITY:
            print("STT: Audio stream closed.")
        self.current_file.close()
        
    def run(self):
        try:
            while self._open:
                self.write_to_file()
        finally:
            self.close()



class ConversationManager:
    def __init__(self):
        self.buffer=[]
        self.transcriber=None
        self.is_listening=False
        self.run_callback_in_thread=False
        self.end_utterance_silence_threshold=None
        aai.settings.api_key=os.getenv("ASSEMBLY_API_KEY")

    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        if ENABLE_STT_VERBOSITY:
            print(f"STT: Starting up assistant with session id: {session_opened.session_id}")
       
    def on_data(self, transcript: aai.RealtimeTranscript):
        if not transcript.text:
            return
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            self.stop_transcriber()
            if ENABLE_STT_VERBOSITY:
                print(f"STT: Stop listening | {transcript.text}")
            
            finished = self.assistant_action(transcript.text)
            if not finished:
                self.start_transcriber()
                if ENABLE_STT_VERBOSITY:
                    print("STT: Started listening...")
    
    def get_from_buffer(self) -> str:
        return "".join(self.buffer)
    
    def add_to_buffer(self, words:List[RealtimeWord]):
        self.buffer.append(words[-1].text)
    
    def clear_buffer(self):
        self.buffer = []
        
    def start_buffer_listening(self):
        self.is_listening=True
        
    def stop_buffer_listening(self):
        self.is_listening=False
        
    def process_with_buffer(self):
        full_transcript = self.get_from_buffer()
        self.clear_buffer()
        finished = self.assistant_action(full_transcript)
        if not finished:
            self.start_buffer_listening()
            if ENABLE_STT_VERBOSITY:
                print("STT: Started listening...")
        else:
            self.clear_buffer()
            self.stop_transcriber()
    
    def on_data_without_close(self, transcript: aai.RealtimeTranscript):
        if not transcript.text:
            return
        if isinstance(transcript, aai.RealtimeFinalTranscript) and self.is_listening:
            self.add_to_buffer(transcript.words)
            self.stop_buffer_listening()
            if ENABLE_STT_VERBOSITY:
                print(f"STT: Stop listening | {transcript.text}")
            
            thread = threading.Thread(target=self.process_with_buffer)
            thread.start()
        elif self.is_listening:
            self.add_to_buffer(transcript.words)
            
    def on_error(self, error: aai.RealtimeError):
        if ENABLE_STT_VERBOSITY:
            print("STT: An error occurred:", error)

    def on_close(self):
        if ENABLE_STT_VERBOSITY:
            print("STT: Closed connection for listening")
          
    def stop_transcriber(self):
        if self.transcriber:
            self.transcriber.close()
            self.transcriber = None
            
    def start_transcriber(self):
        self.transcriber = aai.RealtimeTranscriber(
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
            sample_rate=STT_MODEL_SAMPLE_RATE,
            end_utterance_silence_threshold=STT_END_OF_UTTERANCE_THRESHOLD,
            word_boost=STT_WORD_PROB_BOOSTS if STT_WORD_PROB_BOOSTS else [],
            on_data=self.on_data_without_close if AUTO_LISTEN_WITHOUT_CLOSE else self.on_data,
        )
        self.transcriber.connect()
        if STT_MICROPHONE_BACKEND=="sounddevice":
            microphone_stream = MicrophoneStream(sample_rate=STT_MODEL_SAMPLE_RATE)
        elif STT_MICROPHONE_BACKEND=="pyaudio":
            microphone_stream = aai.extras.MicrophoneStream(sample_rate=STT_MODEL_SAMPLE_RATE)
        else:
            raise (f"STT: Microphone backend should set to be either `pyaudio` or `sounddevice`, but given {STT_MICROPHONE_BACKEND}")
        self.transcriber.stream(microphone_stream)
     
    def interact(self, assistant_action: Callable) -> bool:
        self.assistant_action = assistant_action
        if AUTO_LISTEN_WITHOUT_CLOSE:
            self.start_buffer_listening()
        self.start_transcriber()
        return True
        


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
        audio_data = sd.rec(int(wait_time * WAKE_SAMPLE_RATE), samplerate=WAKE_SAMPLE_RATE, channels=CHANNELS)
        sd.wait()
        
        audio_data = audio_data.flatten()
        audio_data = audio_data.astype(np.float32)
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0
        
        input_features = self.processor(audio_data, sampling_rate=WAKE_SAMPLE_RATE, return_tensors="pt").input_features
        predicted_ids = self.model.generate(input_features)
        transcription = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

        if any (wake_word in transcription.strip().lower() for wake_word in wake_words):
            print("STT DETECTOR: Wake word detected")
            return transcription.strip().lower()
        return False
