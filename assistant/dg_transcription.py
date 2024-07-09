import asyncio, os
from config import STT_MODEL
from dotenv import load_dotenv
from typing import Callable, Optional
from deepgram import ( 
    DeepgramClient, DeepgramClientOptions, 
    LiveTranscriptionEvents, LiveOptions, Microphone 
)


load_dotenv()

    
class ConversationManager:
    def __init__(self, model_name: str=None):
        self.model_name = model_name or STT_MODEL
        self.transcription_response = ""
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.reset_part()
        
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
            full_sentence = self.get_full_transcript()
            if len(full_sentence.strip()) > 0:
                full_sentence = full_sentence.strip()
                # Get full transcript
                if self.data_callback:
                    close = self.data_callback(full_sentence)
                self.reset_part()
                if close:
                    self.microphone.finish()
                    await self.dg_connection.finish()
                    print("STT: Closed connection for listening.")
                self.transcription_event.set()
                
    async def on_error(self, cls, error):
        print("STT: An error occurred:", error)
    
    async def on_close(self):
        print("STT: Closed connection for listening")
    
    async def __run__(self, on_open: Optional[Callable]=None, on_data: Optional[Callable]=None, on_stream: Optional[Callable]=None, end_utterance_threshold: Optional[int]=None):
        self.open_callback=on_open
        self.data_callback=on_data
        self.stream_callback = on_stream
        
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
                endpointing=300,
                language="en-US",
                sample_rate=16000,
                smart_format=False,
                encoding="linear16",
                model=self.model_name,
            ))
            self.microphone = Microphone(self.dg_connection.send)         # Open a microphone stream on the default input device
            self.microphone.start()
            await self.transcription_event.wait()
            self.microphone.finish()
            await self.dg_connection.finish()

        except Exception as e:
            print(f"Could not open socket: {e}")
            return
    
    def run(self, on_open: Optional[Callable]=None, on_data: Optional[Callable]=None, on_stream: Optional[Callable]=None, end_utterance_threshold: Optional[int]=None):
        asyncio.run(self.__run__(
            on_open=on_open,
            on_data=on_data,
            on_stream=on_stream,
            end_utterance_threshold=end_utterance_threshold
        ))
