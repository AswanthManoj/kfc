import os, base64
import webview, queue, yaml
from typing import List, Optional
from config import ENABLE_WEBVIEW_VERBOSITY
from assistant.utils import StreamData, StreamMessages
from web_builder.templates import MENU_PAGE_TEMPLATE, HOME_PAGE_TEMPLATE


MENU_ITEM_HEIGHT = 300
CART_ITEM_HEIGHT = 100
LOGO_IMAGE_PATH = "images/logo1.png"
HOME_BACKGROUND_IMAGE = "images/poster1.jpg"
MENU_BACKGROUND_IMAGE = "images/background.jpg"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


logo_image_data = get_base64_image(os.path.join(BASE_DIR, LOGO_IMAGE_PATH))
menu_background_image_data = get_base64_image(os.path.join(BASE_DIR, MENU_BACKGROUND_IMAGE))
home_background_image_data = get_base64_image(os.path.join(BASE_DIR, HOME_BACKGROUND_IMAGE))

    
class WebViewApp:
    def __init__(self):
        self.window = None
        self.html_queue = queue.Queue()

    def run_webview(self):
        self.window = webview.create_window(
            'KFC Assistant', 
            width=850,
            height=850,
            html=get_home()
        )
        webview.start(self.update_content, debug=False)

    def update_content(self):
        while True:
            try:
                new_html = self.html_queue.get(timeout=1)
                if new_html:
                    self.window.load_html(new_html)
            except queue.Empty:
                pass

    def display(self, data: StreamData|StreamMessages|str) -> bool:
        html_content = None
        if ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW DATA: {data}")
        
        if isinstance(data, StreamData) and data.action:
            html_content = generate_menu(data)
            self.html_queue.put(html_content)
        elif isinstance(data, StreamMessages):
            html_content = self.wrap(yaml.dump(data.model_dump()))
            self.html_queue.put(html_content)
        else:
            html_content = self.wrap(data)
            self.html_queue.put(html_content)
        
        if ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW HTML: {html_content}")
        return True
    
    def wrap(self, content:str):
        return f"<html><p>{content}</p></html>"
    
    
def get_home() -> str:
    catch_phrases = [
        "Hungry? Just say the word",
        "Speak up for finger-lickin' good!",
        "Your order is just a hello away",
        "Voice-activated deliciousness",
    ]
    html_content = HOME_PAGE_TEMPLATE.replace("{background_image}", f"data:image/jpg;base64,{home_background_image_data}")
    html_content = html_content.replace("{catch_phrase}", catch_phrases[-1])
    return html_content
    

def generate_menu(data: StreamData) -> str:
    func_mapping = {
        "get_sides": "side_dishes",
        "get_beverages": "beverages",
        "get_main_dishes": "main_dishes",
    }
    title_mapping = {
        "get_sides": "KFC Side Dishes",
        "get_beverages": "KFC Beverages",
        "get_main_dishes": "KFC Main Dishes",
    }

    category_title = "Menu"
    # Generate menu items HTML
    menu_items_html = ""
    for menu in data.menu:
        if menu.menu_type == func_mapping.get(data.action):
            category_title = title_mapping.get(data.action)
            for item in menu.items:
                image_path = os.path.join(BASE_DIR, item.image_url_path)
                image_data = get_base64_image(image_path)
                menu_items_html += f'''
                <div class="item">
                    <img src="data:image/jpg;base64,{image_data}" alt="{item.name}">
                    <div class="item-name">{item.name}</div>
                    <div class="item-price">${item.price_per_unit}</div>
                </div>
                '''
    
    # Generate cart items HTML
    cart_items_html = ""
    for order in data.cart:
        image_path = os.path.join(BASE_DIR, order.image_url_path)
        image_data = get_base64_image(image_path)
        cart_items_html += f'''
        <div class="cart-item">
            <img src="data:image/jpg;base64,{image_data}" alt="{order.name}">
            <div class="cart-item-details">
                <div class="cart-item-name">{order.name}</div>
                <div class="cart-item-quantity">Quantity: {order.total_quantity}</div>
                <div class="cart-item-price">Price: ${order.price_per_unit * order.total_quantity}</div>
            </div>
        </div>
        '''
    
    html_content: str = MENU_PAGE_TEMPLATE.replace("{category}", category_title)
    html_content = html_content.replace("{cart_items}", cart_items_html)
    html_content = html_content.replace("{menu_items}", menu_items_html)
    html_content = html_content.replace("{total_price}", str(data.total_price))
    html_content = html_content.replace("{menu_item_height}", str(MENU_ITEM_HEIGHT))
    html_content = html_content.replace("{cart_item_height}", str(CART_ITEM_HEIGHT))
    html_content = html_content.replace("{logo_image}", f"data:image/png;base64,{logo_image_data}")
    html_content = html_content.replace("{background_image}", f"data:image/jpg;base64,{menu_background_image_data}")
    return html_content


def generate_order_updates(data: StreamData) -> str:
    pass
    


