import time
import config
from assistant.utils import Message
from startup import (
    get_audio_manager, get_kfc_agent, get_order_cart,
    get_conversation_manager, get_wakeword_detector
)
from web_builder.builder import start_webview_server, display

config.ENABLE_TTS_VERBOSITY = True
config.ENABLE_LLM_VERBOSITY = True
config.ENABLE_STT_VERBOSITY = True
config.ENABLE_WEBVIEW_VERBOSITY = True

def test_agent():
    audio_manager = get_audio_manager()
    agent = get_kfc_agent()
    
    while True:
        user = input("User: ")
        response, finished = agent.invoke(user)
        audio_manager.speak(response)
        if not config.ENABLE_LLM_VERBOSITY:
            print("Assistant:", response)
        if finished:
            print("Order placed successfully")
            break

def test_audio_manager():
    audio_manager = get_audio_manager()
    # audio_manager.play_initial_response()
    # audio_manager.play_disfluent_filler()
    # audio_manager.speak("This is a sample audio test")
    
    audio_manager.play_intermediate_response("confirm_order")
    audio_manager.play_intermediate_response("show_beverages")
    audio_manager.play_intermediate_response("show_side_dishes")
    audio_manager.play_intermediate_response("show_main_dishes")
    audio_manager.play_intermediate_response("add_item_to_cart")
    audio_manager.play_intermediate_response("get_cart_contents")
    audio_manager.play_intermediate_response("remove_item_from_cart")
    audio_manager.play_intermediate_response("modify_item_quantity_in_cart")
    
    
    audio_manager.wait_until_done()
     
def test_stt_listen():
    def open_callback():
        """Function called on open"""
        pass
    
    def data_callback():
        """Function called when transcript is complete is order confirmed then return True to close the connection"""
        pass
    
    
    manager = get_conversation_manager()
    manager.run(on_open=open_callback, on_data=data_callback)
     
def test_wake_word():
    detector = get_wakeword_detector()
    while True:
        listened = detector.detect(["hi", "hello"], 1.25)
        if listened:
            print(listened)
            break
        
def test_webview():
    view = start_webview_server()
    i=0
    while True:
        i+=1
        # Try giving StreamData Object with contents
        view.update_view(f"<h2>This is a live update count {i}</h2>")
        time.sleep(1)

def test_agent_console_input():
    kfc_agent = get_kfc_agent()
    order_cart = get_order_cart()
    audio_manager = get_audio_manager()
    kfc_agent.update_audio_manager(audio_manager)
    order_cart.update_audio_manager(audio_manager)
    
    start_webview_server()
    
    response = audio_manager.play_initial_response()
    order_cart.add_messages_to_state(Message(role="assistant", content=response), is_started=True)
    display(order_cart.get_view_data())

    while True:
        user = input("User: ")
        order_cart.add_messages_to_state(Message(role="user", content=user))
        display(order_cart.get_view_data())
    
        response, order_confirmed = kfc_agent.invoke(user)
        print("Assistant:", response)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        
        order_cart.add_messages_to_state(Message(role="assistant", content=response))
        display(order_cart.get_view_data())

        if order_confirmed:
            order_cart.reset_cart()
            kfc_agent.save_interaction()
            print("Loop Ended")
            break
            
if __name__=="__main__":
    # test_agent()
    # test_webview()
    # test_wake_word()
    # test_stt_listen()
    # test_audio_manager()
    test_agent_console_input()
    pass