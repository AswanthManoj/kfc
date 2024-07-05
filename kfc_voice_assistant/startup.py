from config import (
    TTS_MODEL, SOCKET_HOST, SOCKET_PORT, SOCKET_ENTRY,
    DISFLUENCE, INITIAL_RESPONSE, INTERMEDIATE_RESPONSE
)
from agent import AudioManager, OrderCart, Item, SocketManager


agent = None
order_cart = None
audio_manager = None
socket_manager = None

def get_audio_manager():
    global audio_manager
    if audio_manager is None:
        audio_manager = AudioManager(
            model_name=TTS_MODEL,
            disfluence_folder=DISFLUENCE,
            initial_response_folder=INITIAL_RESPONSE,
            intermediate_response_folder=INTERMEDIATE_RESPONSE
        )
    return audio_manager

def get_socket_manager():
    global socket_manager
    if socket_manager is None:
        socket_manager = SocketManager(
            port=SOCKET_PORT, 
            host=SOCKET_HOST, 
            entry=SOCKET_ENTRY
        )
    return socket_manager

def get_order_cart():
    global order_cart
    if order_cart is None:
        order_cart = OrderCart(
            audio_manager=get_audio_manager(),
            socket_manager=get_socket_manager(),
            beverages=[
                Item(name="Pepsi", price_per_unit=1.99, image_url_path="/images/pepsi.jpg"),
                Item(name="Iced Tea", price_per_unit=1.79, image_url_path="/images/iced_tea.jpg"),
                Item(name="Mountain Dew", price_per_unit=1.99, image_url_path="/images/mountain_dew.jpg")
            ],
            main_dishes=[
                Item(name="Zinger Burger", price_per_unit=4.99, image_url_path="/images/zinger_burger.jpg"),
                Item(name="Chicken Twister", price_per_unit=5.49, image_url_path="/images/chicken_twister.jpg"),
                Item(name="Original Recipe Chicken - 2 pc", price_per_unit=5.99, image_url_path="/images/original_chicken.jpg")
            ],
            side_dishes=[
                Item(name="Coleslaw", price_per_unit=1.99, image_url_path="/images/coleslaw.jpg"),
                Item(name="French Fries", price_per_unit=2.49, image_url_path="/images/fries.jpg"),
                Item(name="Mashed Potatoes", price_per_unit=2.29, image_url_path="/images/mashed_potatoes.jpg")
            ]
        )
    return order_cart


