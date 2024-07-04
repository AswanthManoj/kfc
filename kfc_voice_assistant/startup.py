from config import LLM_MODEL, TTS_MODEL
from agent import AudioManager, OrderCart, Item


agent = None
order_cart = None
audio_manager = None

def get_audio_manager():
    global audio_manager
    if audio_manager is None:
        audio_manager = AudioManager(
            model_name=TTS_MODEL,
            disfluence_folder="disfluencies",
            initial_response_folder="responses/initial_responses",
            intermediate_response_folder="responses/intermediate_responses"
        )
    return audio_manager

def get_order_cart():
    global order_cart
    if order_cart is None:
        order_cart = OrderCart(
            audio_manager=get_audio_manager(),
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


