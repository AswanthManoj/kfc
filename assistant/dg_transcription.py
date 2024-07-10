import asyncio, os
from dotenv import load_dotenv
from typing import Callable, Optional
from deepgram import ( 
    DeepgramClient, DeepgramClientOptions, 
    LiveTranscriptionEvents, LiveOptions, Microphone 
)
from config import STT_MODEL, ENABLE_STT_VERBOSITY


load_dotenv()

    
class ConversationManager:
    def __init__(self, model_name: str=None):
        self.reset_part()
        self.transcription_response = ""
        self.run_callback_in_thread =False
        self.model_name = model_name or STT_MODEL
        self.end_utterance_silence_threshold = 300
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        
    def handle_full_sentence(self, full_sentence):
        self.transcription_response = full_sentence
        print(f"Human: {full_sentence}")
        
    def reset_part(self):
        self.transcript_parts = []

    def add_part(self, part):
        self.transcript_parts.append(part)

    def get_full_transcript(self):
        return ' '.join(self.transcript_parts)
    
    def reset(self):
        self.transcription_response = ""
        
    async def on_open(self, cls, data):
        print(f"STT: Starting up live transcript connection ")
        if self.open_callback:
            self.open_callback()
    
    async def on_data(self, cls, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if not result.speech_final:
            self.add_part(sentence)
            # Get partial transcript
            if self.stream_callback:
                text=self.get_full_transcript()
                self.stream_callback(text)
        else:
            self.add_part(sentence)
            # Get full transcript
            full_sentence = self.get_full_transcript()
            if len(full_sentence.strip()) > 0:
                full_sentence = full_sentence.strip()
                if self.data_callback:
                    try:
                        if self.run_callback_in_thread:
                            asyncio.create_task(self.run_data_callback(full_sentence))
                        else:
                            close = self.data_callback(full_sentence)   
                            if close:
                                self.microphone.finish()
                                await self.dg_connection.finish()
                                print("STT: Closed connection for listening.")
                    except Exception as e:
                        print(f"Error executing callback: {e}")
                self.reset_part()
                self.transcription_event.set()
    
    async def run_data_callback(self, transcript: str):
        try:
            close = self.data_callback(transcript)   
            if close:
                self.microphone.finish()
                await self.dg_connection.finish()
                print("STT: Closed connection for listening.")
        except Exception as e:
            print(f"Error in run_data_callback: {e}")
                
    async def on_error(self, cls, error):
        print("STT: An error occurred:", error)
    
    async def on_close(self):
        print("STT: Closed connection for listening")
    
    async def __run__(self, on_open: Optional[Callable]=None, on_data: Optional[Callable]=None, on_stream: Optional[Callable]=None, end_utterance_threshold: Optional[int]=None):
        self.open_callback=on_open
        self.data_callback=on_data
        self.stream_callback = on_stream
        self.end_utterance_silence_threshold = end_utterance_threshold or self.end_utterance_silence_threshold
        self.transcription_event = asyncio.Event()
        
        try:
            deepgram: DeepgramClient = DeepgramClient(
                api_key=self.api_key, 
                config=DeepgramClientOptions(
                    api_key=self.api_key,
                    options={"keepalive": "true"}
                )
            )
            self.dg_connection = deepgram.listen.asynclive.v("1")
            self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self.on_close)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_data)
            await self.dg_connection.start(LiveOptions(
                channels=1,
                punctuate=True,
                language="en-US",
                sample_rate=16000,
                smart_format=False,
                encoding="linear16",
                model=self.model_name,
                endpointing=self.end_utterance_silence_threshold,
            ))
            self.microphone = Microphone(self.dg_connection.send)         # Open a microphone stream on the default input device
            self.microphone.start()
            await self.transcription_event.wait()
            self.microphone.finish()
            await self.dg_connection.finish()

        except Exception as e:
            print(f"Could not open socket: {e}")
            return
    
    def run(self, on_open: Optional[Callable]=None, on_data: Optional[Callable]=None, on_stream: Optional[Callable]=None, end_utterance_threshold: Optional[int]=None, run_callback_in_thread: bool=False):
        self.run_callback_in_thread = run_callback_in_thread
        asyncio.run(self.__run__(
            on_open=on_open,
            on_data=on_data,
            on_stream=on_stream,
            end_utterance_threshold=end_utterance_threshold
        ))
