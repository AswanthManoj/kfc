from assistant.agent import ( AudioManager, 
    WakeWordDetector, ConversationManager, Agent
)
from assistant.tools import get_available_tools
from assistant.menu import get_order_cart, get_menu_items
from config import (
    TTS_MODEL, DISFLUENCE, LLM_MODEL,
    INITIAL_RESPONSE, INTERMEDIATE_RESPONSE, WAKE_WORD_MODEL
)


agent = None
order_cart = None
audio_manager = None
wake_word_detector = None
conversation_manager = None

def get_kfc_agent() -> Agent:
    global agent
    if agent is None:
        agent = Agent(
            model_name=LLM_MODEL,
            tools=get_available_tools(),
            menu_items=get_menu_items()
        )
    return agent

def get_audio_manager() -> AudioManager:
    global audio_manager
    if audio_manager is None:
        audio_manager = AudioManager(
            model_name=TTS_MODEL,
            disfluence_folder=DISFLUENCE,
            initial_response_folder=INITIAL_RESPONSE,
            intermediate_response_folder=INTERMEDIATE_RESPONSE
        )
    return audio_manager

def get_wakeword_detector() -> WakeWordDetector:
    global wake_word_detector
    if wake_word_detector is None:
        wake_word_detector = WakeWordDetector(
            model_id=WAKE_WORD_MODEL
        )
    return wake_word_detector

def get_conversation_manager() -> ConversationManager:
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    return conversation_manager
    
    
order_cart = get_order_cart()
order_cart.update_audio_manager(
    get_audio_manager()
)

