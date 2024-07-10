import yaml
from typing import List, Optional
from web_builder.builder import display
from assistant.agent import AudioManager
from config import ENABLE_TOOL_VERBOSITY, ENABLE_TTS_VERBOSITY
from assistant.utils import Item, Order, Menu, StreamData, Message



###############################
# ASSISTANT DATA TOOL CLASSES #
###############################
class KFCMenu:
    def __init__(self, audio_manager: AudioManager, beverages: Optional[List[Item]] = None, main_dishes: Optional[List[Item]] = None, side_dishes: Optional[List[Item]] = None) -> None:
        self.beverages=beverages
        self.main_dishes=main_dishes
        self.side_dishes=side_dishes
        self.audio_manager = audio_manager
        self.menu=[
            Menu(menu_type="beverages", items=self.beverages),
            Menu(menu_type="main_dishes", items=self.main_dishes),
            Menu(menu_type="side_dishes", items=self.side_dishes),
        ]
        self.action = None
        self.is_started = False
        self.stream_messages = []
        self.orders: List[Order] = []
    
    def update_audio_manager(self, audio_manager):
        self.audio_manager = audio_manager
        
    def get_view_data(self) -> StreamData:
        view_data = StreamData(
            menu=self.menu,
            cart=self.orders,
            action=self.action,
            is_started=self.is_started,
            stream_messages=self.stream_messages
        )
        view_data.update()
        return view_data
    
    def add_messages_to_state(self, message: Message, is_started: bool=False) -> StreamData:
        self.is_started=is_started
        self.stream_messages.append(message)
        return self.get_view_data()
        
    def show_main_dishes(self) -> bool:
        self.action = "show_main_dishes"
        
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}' Invoked")
        return True

    def show_side_dishes(self) -> bool:
        self.action = "show_side_dishes"
        
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}' Invoked")
        return True

    def show_beverages(self) -> bool:
        self.action = "show_beverages"
        
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}' Invoked")
        return True
    
    def get_item_by_name(self, name: str) -> Optional[Item]:
        for category in [self.main_dishes, self.side_dishes, self.beverages]:
            for item in category:
                if name == item.name:
                    print("get item by name: ", item)
                    return item
        return None
    

class OrderCart(KFCMenu):
    
    def __init__(self, audio_manager: AudioManager=None, beverages: Optional[List[Item]] = None, main_dishes: Optional[List[Item]] = None, side_dishes: Optional[List[Item]] = None) -> None:
        super().__init__(audio_manager, beverages, main_dishes, side_dishes)
    
    def add_item_to_cart(self, item_name: str, quantity: int = 1) -> str:
        is_new = True
        item = self.get_item_by_name(item_name)
        if item is None:
            return yaml.dump({"error": "Item not found from the menu. Please try with a valid name from the available menu items."})
        result = dict(name=item.name, total_quantity=quantity, price_per_unit=f"${item.price_per_unit}")

        for i, order in enumerate(self.orders):
            if order.name == item_name:
                self.orders[i].total_quantity += quantity
                # self.orders[i].image_url_path = item.image_url_path
                result['total_quantity'] = self.orders[i].total_quantity
                result['price_per_unit'] = f"${order.price_per_unit}"
                is_new = False
                break
       
        if is_new:
            self.orders.append(Order(
                name=item_name, 
                total_quantity=quantity,
                price_per_unit=item.price_per_unit, 
                image_url_path=item.image_url_path
            ))
        
        self.action = "add_item_to_cart"
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}': {yaml.dump(result)}")
            
        return yaml.dump(result)

    def remove_item_from_cart(self, item_name: str, quantity: int = 1, remove_all: bool = False) -> str:
        result = dict(name=item_name, action="not_found")
        for i, order in enumerate(self.orders):
            if order.name == item_name:
                if (order.total_quantity <= quantity) or remove_all:
                    self.orders.pop(i)
                    result['action'] = "fully_removed"
                else:
                    self.orders[i].total_quantity -= quantity
                    result['action'] = "partially_removed"
                    result['remaining_quantity'] = self.orders[i].total_quantity
                break
            
        self.action = "remove_item_from_cart"
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}': {yaml.dump(result)}")
            
        return yaml.dump(result)

    def modify_item_quantity_in_cart(self, item_name: str, new_quantity: int) -> str:
        result = dict(name=item_name, action="not_found")
        for order in self.orders:
            if order.name == item_name:
                if new_quantity <= 0:
                    self.orders.remove(order)
                    result['action'] = "removed"
                else:
                    order.total_quantity = new_quantity
                    result['action'] = "updated"
                    result['new_quantity'] = new_quantity
                break
            
        self.action = "modify_item_quantity_in_cart"
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}': {yaml.dump(result)}")
        
        return yaml.dump(result)

    def confirm_order(self) -> str:
        confirmation = {
            "status": "confirmed",
            "message": "Your order has been confirmed.",
            "items": [{"name": order.name, "quantity": order.total_quantity} for order in self.orders]
        }
        
        self.action = "confirm_order"
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
       
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}': {yaml.dump(confirmation)}")
        
        # self.reset_cart()
        return yaml.dump(confirmation)

    def get_cart_contents(self) -> str:
        contents = []
        total_price = 0
        for order in self.orders:
            total = order.total_quantity * order.price_per_unit
            total_price += total
            contents.append({"name": order.name, "quantity": order.total_quantity, "price": total})
            
        self.action = "get_cart_contents"
        if self.audio_manager:
            self.audio_manager.play_intermediate_response(self.action)
        view_data = self.get_view_data()
        display(view_data)
        
        if ENABLE_TOOL_VERBOSITY:
            print(f"TOOL '{self.action}': {yaml.dump(contents)}\n\nTotal Price of items: ${total_price}")  
            
        if contents:
            return f"{yaml.dump(contents)}\n\nTotal Price of items: ${total_price}"
        return "The cart is currently empty."

    def reset_cart(self) -> None:
        self.action = None
        self.is_started = False
        self.stream_messages = []
        self.orders: List[Order] = []
        view_data = self.get_view_data()
        display(view_data)

        
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
    
class SingletonOrderCart(OrderCart, metaclass=SingletonMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def update_webview_manager(self, webview_manager):
        self.webview_manager = webview_manager
    
    def update_audio_manager(self, audio_manager):
        self.audio_manager = audio_manager
    
    def get_menu_items(self):
        return self.menu
            
        
def get_order_cart():
    if not hasattr(get_order_cart, "instance"):
        get_order_cart.instance = SingletonOrderCart(
            beverages=[
                Item(name="Pepsi", price_per_unit=1.41, image_url_path="images/pepsi.jpg"),
                Item(name="Iced Tea", price_per_unit=1.13, image_url_path="images/iced_tea.jpg"),
                Item(name="Mountain Dew", price_per_unit=1.53, image_url_path="images/mountain_dew.jpg")
            ],
            side_dishes=[
                Item(name="Coleslaw", price_per_unit=1.99, image_url_path="images/coleslaw.jpg"),
                Item(name="French Fries", price_per_unit=2.49, image_url_path="images/fries.jpg"),
                Item(name="Mac and Cheese Bowl", price_per_unit=2.99, image_url_path="images/mac_and_cheese.jpg"),
                Item(name="Cream Cheese Mashed Potatoes", price_per_unit=2.29, image_url_path="images/cream_cheese_mashed_potatoes.jpg"),
            ],
            main_dishes=[
                Item(name="KFC Special Chizza", price_per_unit=3.7, image_url_path="images/chizza.jpg"),
                Item(name="Zinger Burger", price_per_unit=3.49, image_url_path="images/zinger_burger.jpg"),
                Item(name="Hot and Saucy Chicken", price_per_unit=4.1, image_url_path="images/hot_and_saucy_chicken.jpg"),
                Item(name="Chicken Crispy Tender Hot Dog", price_per_unit=4.7, image_url_path="images/crispy_tender_hot_dog.jpg"),
                Item(name="KFC Chicken Drumstick Bucket 12pc", price_per_unit=6.1, image_url_path="images/chicken_drumstick_bucket.jpg"),
            ]
        )
    return get_order_cart.instance

def get_menu_items() -> List[Menu]:
    order_cart = get_order_cart()
    return order_cart.get_menu_items()
