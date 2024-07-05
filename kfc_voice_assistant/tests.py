from tools import get_available_tools
from startup import get_audio_manager, get_socket_manager
from agent import ConversationManager, Agent, WakeWordDetector
from config import (
    LLM_MODEL, WAKE_WORDS, WAKE_WAIT_DELAY, WAKE_WORD_MODEL,
    ENABLE_LLM_VERBOSITY, ENABLE_STT_VERBOSITY, ENABLE_SOCKET_VERBOSITY, ENABLE_TTS_VERBOSITY
)


def test_agent():
    tools = get_available_tools()
    audio_manager = get_audio_manager()
    agent = Agent(model_name=LLM_MODEL, tools=tools)
    
    while True:
        user = input("User: ")
        response, finished = agent.invoke(user)
        audio_manager.speak(response)
        if not ENABLE_LLM_VERBOSITY:
            print("Assistant:", response)
        if finished:
            print("Order placed successfully")
            break

def test_audio_manager():
    audio_manager = get_audio_manager()
    audio_manager.play_initial_response()
    audio_manager.play_disfluent_filler()
    audio_manager.speak("This is a sample audio test")
    
    audio_manager.play_intermediate_response("add_item")
    audio_manager.play_intermediate_response("get_sides")
    audio_manager.play_intermediate_response("remove_item")
    audio_manager.play_intermediate_response("get_beverages")
    audio_manager.play_intermediate_response("confirm_order")
    audio_manager.play_intermediate_response("get_main_dishes")
    audio_manager.play_intermediate_response("modify_quantity")
    audio_manager.play_intermediate_response("get_cart_contents")
    
    audio_manager.wait_until_done()
     
def test_stt_listen():
    def open_callback():
        """Function called on open"""
        pass
    
    def data_callback():
        """Function called when transcript is complete is order confirmed then return True to close the connection"""
        pass
    
    manager = ConversationManager()
    manager.run(on_open=open_callback, on_data=data_callback)
     
def test_wake_word():
    detector = WakeWordDetector(WAKE_WORD_MODEL)
    while True:
        listened = detector.detect(["hi", "hello"], 1.25)
        if listened:
            print(listened)
            break
        
def test_socket():
    manager = get_socket_manager()
    while True:
        user = input("Enter: ")
        if user:
            manager.send_message({"user": user})
            
            
if __name__=="__main__":
    test_agent()
    # test_audio_manager()
    # test_stt_listen()
    # test_wake_word()
    # test_socket()