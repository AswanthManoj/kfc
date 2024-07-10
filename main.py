from assistant.utils import Message
from config import WAKE_WORDS, WAKE_WAIT_DELAY
from startup import (
    get_conversation_manager, get_wakeword_detector,
    get_audio_manager, get_order_cart, get_kfc_agent
)
from web_builder.builder import start_webview_server, display


kfc_agent = get_kfc_agent()
order_cart = get_order_cart()
audio_manager = get_audio_manager()
wake_detector = get_wakeword_detector()
kfc_agent.update_audio_manager(audio_manager)
order_cart.update_audio_manager(audio_manager)
conversation_manager = get_conversation_manager()


def assistant_action(transcript: str) -> bool:
    order_cart.add_messages_to_state(Message(role="user", content=transcript))
    display(order_cart.get_view_data())
    
    response, order_confirmed = kfc_agent.invoke(transcript)
    audio_manager.speak(response)
    audio_manager.wait_until_done()
        
    order_cart.add_messages_to_state(Message(role="assistant", content=response))
    display(order_cart.get_view_data())
    
    if order_confirmed:
        order_cart.reset_cart()
        kfc_agent.save_interaction()

    return order_confirmed


if __name__ == '__main__':
    start_webview_server()
    while True:
        if wake_detector.detect(WAKE_WORDS, WAKE_WAIT_DELAY):
            print("Wake word detected...")
            response = audio_manager.play_initial_response()
            order_cart.add_messages_to_state(Message(role="assistant", content=response), is_started=True)
            display(order_cart.get_view_data())
            audio_manager.wait_until_done()
            
            # 1. Inside this first the it starts listening
            # 2. then in every full transcript it stops listening
            # 3. after the assistant_action method is executed it again starts listening
            # 4. If order placement is confirmed then it will never listen and there by ends the interaction
            conversation_manager.interact(assistant_action)
            print("Interaction loop ended")