from typing import List, Optional
from pydantic import BaseModel, model_validator



###################
# PYDANTIC MODELS #
###################
class Item(BaseModel):
    name:           str
    price_per_unit: float
    image_url_path: str = ""

class Order(Item):
    total_quantity: int = 0
    
class Menu(BaseModel):
    items:     List[Item] = []
    menu_type: str = "main_dish"
    
class Message(BaseModel):
    role:         Optional[str] = None  # can be None, "assistant" or "user"
    content:      Optional[str] = None
    
    
class StreamData(BaseModel):
    menu:              List[Menu] = []
    cart:              List[Order] = []
    action:            Optional[str] = None
    is_started:        bool = False
    total_price:       float = 0
    stream_messages:   List[Message] = []
    
    @model_validator(mode="before")
    def calculate_total_price(cls, values):
        cart: List[Order] = values.get('cart') or []
        if cart:
            total_price = sum(order.price_per_unit * order.total_quantity for order in cart)
        else:
            total_price = 0
        values['total_price'] = total_price
        return values

    def update(self):
        if self.cart:
            self.total_price = sum(order.price_per_unit * order.total_quantity for order in self.cart)
        else:
            self.total_price = 0