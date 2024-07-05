from config import (
    LLM_MODEL, WAKE_WORDS, 
    WAKE_WAIT_DELAY, WAKE_WORD_MODEL
)
from tools import get_available_tools
from startup import get_audio_manager, get_socket_manager
from agent import ConversationManager, Agent, WakeWordDetector


def main():
    tools = get_available_tools()
    audio_manager = get_audio_manager()
    socket_manager = get_socket_manager()
    detector = WakeWordDetector(WAKE_WORD_MODEL)
    agent = Agent(model_name=LLM_MODEL, tools=tools)
    manager = ConversationManager(agent=agent, audio_manager=audio_manager, socket_manager=socket_manager)
    
    while True:
        if detector.detect(WAKE_WORDS, WAKE_WAIT_DELAY):
            manager.run()

if __name__=="__main__":
    main()
    
    
# audio_manager = get_audio_manager()
# audio_manager.speak("Hi..., hello there I am a assistant")
# audio_manager.speak("Who is here to talk.")
# audio_manager.speak("About a KFC drive-way voice assistant.")
# audio_manager.speak("And as you guessed, its me.")
# audio_manager.wait_until_done()