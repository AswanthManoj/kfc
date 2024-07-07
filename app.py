import time
import threading
from web_builder.builder import WebViewApp
from config import WAKE_WORDS, WAKE_WAIT_DELAY
from startup import (
    get_conversation_manager, get_wakeword_detector,
    get_audio_manager, get_order_cart, get_kfc_agent
)

#####################################
# Assistant thread with voice input #
#####################################
def main1(app: WebViewApp):
    kfc_agent = get_kfc_agent()
    order_cart = get_order_cart()
    audio_manager = get_audio_manager()
    wake_detector = get_wakeword_detector()
    conversation_manager = get_conversation_manager()
    
    order_cart.update_webview_manager(app)
    order_cart.update_audio_manager(audio_manager)
    
    app.display("Assistant starting up...")
    
    def open_callback():
        """Function called on open"""
        response = audio_manager.play_initial_response()
        app.display(response)
        
    def data_callback(text: str) -> bool:
        """Function called when transcript is complete is order confirmed then return True to close the connection"""
        response, order_confirmed = kfc_agent.invoke(text)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        return order_confirmed
    
    while True:
        if wake_detector.detect(WAKE_WORDS, WAKE_WAIT_DELAY):
            conversation_manager.run(
                on_open=open_callback, 
                on_data=data_callback,
            )
    
#######################################
# Assistant thread with console input #
#######################################
def main2(app: WebViewApp):
    kfc_agent = get_kfc_agent()
    order_cart = get_order_cart()
    audio_manager = get_audio_manager()
    
    order_cart.update_webview_manager(app)
    order_cart.update_audio_manager(audio_manager)
    
    app.display("Assistant starting up...")
    audio_manager.play_initial_response()
    app.display("Active")
    
    while True:
        user = input("User: ")
        response, order_confirmed = kfc_agent.invoke(user)
        print("Assistant:", response)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        if order_confirmed:
            print("Loop Ended")
            break


if __name__ == '__main__':
    app = WebViewApp()
    # Start a separate thread for other tasks
    task_thread = threading.Thread(target=main2, args=(app,))
    task_thread.start()

    # Run webview on the main thread
    app.run_webview()

    # Join the task thread when done
    task_thread.join()

