from config import (
    LLM_MODEL, WAKE_WORDS, 
    WAKE_WAIT_DELAY, WAKE_WORD_MODEL
)
from utils import StreamMessages
from tools import get_available_tools
from startup import get_audio_manager, get_socket_manager
from agent import ConversationManager, Agent, WakeWordDetector


def main():
    tools = get_available_tools()
    manager = ConversationManager()
    audio_manager = get_audio_manager()
    socket_manager = get_socket_manager()
    detector = WakeWordDetector(WAKE_WORD_MODEL)
    agent = Agent(model_name=LLM_MODEL, tools=tools)

    def open_callback():
        """Function called on open"""
        response = audio_manager.play_initial_response()
        socket_manager.send_message(
            StreamMessages(
                is_initiated=True, 
                role="assistant", content=response).model_dump()
        )
    
    def data_callback(text: str) -> bool:
        """Function called when transcript is complete is order confirmed then return True to close the connection"""
        response, order_confirmed = agent.invoke(text)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        return order_confirmed
    
    while True:
        if detector.detect(WAKE_WORDS, WAKE_WAIT_DELAY):
            manager.run(
                on_open=open_callback, 
                on_data=data_callback,
            )

if __name__=="__main__":
    main()
    
    
