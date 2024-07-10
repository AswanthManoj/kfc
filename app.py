from assistant.utils import Message
from config import WAKE_WORDS, WAKE_WAIT_DELAY
from startup import (
    get_conversation_manager, get_wakeword_detector,
    get_audio_manager, get_order_cart, get_kfc_agent
)
from assistant.dg_transcription import ConversationManager
from web_builder.builder import start_webview_server, display



###############################################
# Assistant thread with deep-gram voice input #
###############################################     
def main1():
    kfc_agent = get_kfc_agent()
    order_cart = get_order_cart()
    audio_manager = get_audio_manager()
    wake_detector = get_wakeword_detector()
    conversation_manager = ConversationManager()
    kfc_agent.update_audio_manager(audio_manager)
    order_cart.update_audio_manager(audio_manager)

    
    def open_callback():
        """Function called on open"""
        response = audio_manager.play_initial_response()
        audio_manager.wait_until_done()
        order_cart.add_messages_to_state(Message(role="assistant", content=response), is_started=True)
        stream_data = order_cart.get_view_data()
        display(stream_data)
        
    def data_callback(text: str) -> bool:
        """Function called when transcript is complete is order confirmed then return True to close the connection"""
        order_cart.add_messages_to_state(Message(role="user", content=text))
        stream_data = order_cart.get_view_data()
        display(stream_data)
        
        response, order_confirmed = kfc_agent.invoke(text)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        
        order_cart.add_messages_to_state(Message(role="assistant", content=response))
        stream_data = order_cart.get_view_data()
        display(stream_data)
        
        if order_confirmed:
            order_cart.reset_cart()
        
        return order_confirmed
    
    # Experimental Callback to stream live transcript
    def stream_callback(text: str):
        order_cart.add_messages_to_state(Message(role="user", content=text))
        stream_data = order_cart.get_view_data()
        display(stream_data)

    
    while True:
        if wake_detector.detect(WAKE_WORDS, WAKE_WAIT_DELAY):
            conversation_manager.run(
                on_stream=None,               # stream_callback,
                on_open=open_callback, 
                on_data=data_callback,
                end_utterance_threshold=None, # is not currently set.
                run_callback_in_thread=True   # Set this to true to run the assistant interaction in thread to prevent transcript socket data stream blocking
            )
            
 
 
#################################################
# Assistant thread with assembly-ai voice input #
#################################################
def main2():
    kfc_agent = get_kfc_agent()
    order_cart = get_order_cart()
    audio_manager = get_audio_manager()
    wake_detector = get_wakeword_detector()
    kfc_agent.update_audio_manager(audio_manager)
    order_cart.update_audio_manager(audio_manager)
    conversation_manager = get_conversation_manager()

    
    def open_callback():
        """Function called on open"""
        response = audio_manager.play_initial_response()
        audio_manager.wait_until_done()
        order_cart.add_messages_to_state(Message(role="assistant", content=response), is_started=True)
        stream_data = order_cart.get_view_data()
        display(stream_data)
        
        
    def data_callback(text: str) -> bool:
        """Function called when transcript is complete is order confirmed then return True to close the connection"""
        order_cart.add_messages_to_state(Message(role="user", content=text))
        stream_data = order_cart.get_view_data()
        display(stream_data)
        
        response, order_confirmed = kfc_agent.invoke(text)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        
        order_cart.add_messages_to_state(Message(role="assistant", content=response))
        stream_data = order_cart.get_view_data()
        display(stream_data)
        
        if order_confirmed:
            order_cart.reset_cart()
        
        # audio_manager.microphone_stream.resume()
        return order_confirmed
    
    # Experimental Callback to stream live transcript
    def stream_callback(text: str):
        order_cart.add_messages_to_state(Message(role="user", content=text))
        stream_data = order_cart.get_view_data()
        display(stream_data)

    
    while True:
        if wake_detector.detect(WAKE_WORDS, WAKE_WAIT_DELAY):
            conversation_manager.run(
                on_stream=None,               # stream_callback,
                on_open=open_callback, 
                on_data=data_callback,
                end_utterance_threshold=None,
                run_callback_in_thread=True   # Set this to true to run the assistant interaction in thread to prevent transcript socket data stream blocking
            )
            

    
#######################################
# Assistant thread with console input #
#######################################
def main3():
    kfc_agent = get_kfc_agent()
    order_cart = get_order_cart()
    audio_manager = get_audio_manager()
    
    kfc_agent.update_audio_manager(audio_manager)
    order_cart.update_audio_manager(audio_manager)
    
    response = audio_manager.play_initial_response()
    
    order_cart.add_messages_to_state(Message(role="assistant", content=response), is_started=True)
    stream_data = order_cart.get_view_data()
    display(stream_data)
    
    while True:
        user = input("User: ")
        order_cart.add_messages_to_state(Message(role="user", content=user))
        stream_data = order_cart.get_view_data()
        display(stream_data)
    
        response, order_confirmed = kfc_agent.invoke(user)
        print("Assistant:", response)
        audio_manager.speak(response)
        audio_manager.wait_until_done()
        
        order_cart.add_messages_to_state(Message(role="assistant", content=response))
        stream_data = order_cart.get_view_data()
        display(stream_data)

        if order_confirmed:
            order_cart.reset_cart()
            print("Loop Ended")
            break


if __name__ == '__main__':
    # Start the webview server
    start_webview_server()
    
    # main1() # Assistant thread with deep-gram voice input
    # main2() # Assistant thread with assembly-ai voice input
    main3() # Assistant thread with console input

