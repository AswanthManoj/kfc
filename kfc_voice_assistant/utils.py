import threading
from typing import List, Optional
from pydantic import BaseModel, model_validator
from assemblyai.extras import AssemblyAIExtrasNotInstalledError


###################
# PYDANTIC MODELS #
###################
class Item(BaseModel):
    name:           str
    price_per_unit: float
    image_url_path: str = ""

class Order(Item):
    total_quantity: int = 0
    
class Menu(BaseModel):
    items:     List[Item] = []
    menu_type: str = "main_dish"
    
class StreamData(BaseModel):
    cart:        List[Order] = []
    menu:        List[Menu] = []
    action:      Optional[str] = None
    total_price: float = 0
    
    @model_validator(mode="before")
    def calculate_total_price(cls, values):
        cart: List[Order] = values.get('cart') or []
        total_price = sum(order.price_per_unit * order.total_quantity for order in cart)
        values['total_price'] = total_price
        return values

    def update(self):
        self.total_price = sum(order.price_per_unit * order.total_quantity for order in self.cart)
    
class StreamMessages(BaseModel):
    is_initiated: bool = False          # Indicates if the agent loop started after hearing wake word
    role:         Optional[str] = None  # can be "assistant" or "user"
    content:      Optional[str] = None

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
        try:
            import pyaudio
        except ImportError:
            raise AssemblyAIExtrasNotInstalledError

        self._pyaudio = pyaudio.PyAudio()
        self.sample_rate = sample_rate

        self._chunk_size = int(self.sample_rate * 0.1)
        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=self._chunk_size,
        )

        self._open = True
        self._paused = False
        self._pause_lock = threading.Lock()

    def __iter__(self):
        """
        Returns the iterator object.
        """
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
                    return b'\x00' * self._chunk_size  # Return silence when paused
                return self._stream.read(self._chunk_size)
        except KeyboardInterrupt:
            raise StopIteration

    def close(self):
        """
        Closes the stream.
        """
        self._open = False

        if self._stream.is_active():
            self._stream.stop_stream()

        self._stream.close()
        self._pyaudio.terminate()

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


def rotate_key(keys: List[str], idx: int) -> str:
    return keys[idx%len(keys)]
