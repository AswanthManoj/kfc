import time
import config
from startup import (
    get_audio_manager, get_kfc_agent, 
    get_conversation_manager, get_wakeword_detector, get_order_cart
)
from web_builder.builder import generate_menu, WebViewApp

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
    app = WebViewApp()
    i=0
    while True:
        i+=1
        app.display(f"<h2>This is a live update count {i}</h2>")
        time.sleep(1)

            
if __name__=="__main__":
    # test_agent()
    # test_audio_manager()
    # test_stt_listen()
    # test_wake_word()
    test_webview()
    pass