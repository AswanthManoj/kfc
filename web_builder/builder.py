import os, base64
import yaml, random
from webview import Webview
from typing import List, Optional
from jinja2 import Template, Environment
from config import ENABLE_WEBVIEW_VERBOSITY
from .styles import HOME_PAGE_STYLE, MENU_PAGE_STYLE
from assistant.utils import StreamData, Message, Item, Order
from .templates import HOME_PAGE_TEMPLATE, MENU_PAGE_TEMPLATE, ORDER_REVIEW_PAGE_TEMPLATE


MENU_ITEM_HEIGHT = 300
CART_ITEM_HEIGHT = 100
LOGO_IMAGE_PATH = "images/logo1.png"
HOME_BACKGROUND_IMAGE = "images/poster1.jpg"
MENU_BACKGROUND_IMAGE = "images/background.jpg"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


if ENABLE_WEBVIEW_VERBOSITY:
    print(f"WEBVIEW: BASE_DIR: {BASE_DIR}")
    print(f"WEBVIEW: LOGO_IMAGE_PATH: {os.path.join(BASE_DIR, LOGO_IMAGE_PATH)}")
    print(f"WEBVIEW: HOME_BACKGROUND_IMAGE: {os.path.join(BASE_DIR, HOME_BACKGROUND_IMAGE)}")
    print(f"WEBVIEW: MENU_BACKGROUND_IMAGE: {os.path.join(BASE_DIR, MENU_BACKGROUND_IMAGE)}")


def start_webview_server():
    Webview.configure(
        port=8080,
        debug=False,
        host="127.0.0.1", 
        log_level="warning",
        title="KFC Voice Assistant", 
    )
    Webview.update_view(display_home_page())
    Webview.start_webview()
    return Webview

def get_base64_image(image_path: str) -> str:
    image_path = os.path.join(BASE_DIR, image_path)
    with open(image_path, "rb") as image_file:
        encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
        if ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW: Successfully encoded image: {image_path}, encoded data length: {len(encoded_data)}")
        return f"data:image/png;base64,{encoded_data}"

def display_home_page() -> str:
    css_template = Template(HOME_PAGE_STYLE)
    html_template = Template(HOME_PAGE_TEMPLATE)
    
    rendered_css = css_template.render({
        "background_image": get_base64_image(HOME_BACKGROUND_IMAGE)
    })
    rendered_html = html_template.render({
        "css": rendered_css,
        "catch_phrase": random.choice([
            "Hungry? Just say the word",
            "Voice-activated deliciousness",
            "Your order is just a hello away",
            "Speak up for finger-lickin' good!",
        ])
    })
    Webview.update_view(rendered_html)
    return rendered_html
    
                         
    def display(self, data: StreamData|str) -> bool:
        """
        Display the appropriate content based on the input data.

        This method handles different actions like showing menus, adding items to cart, etc.

        Args:
            data (StreamData|str): The data to be displayed, either as a StreamData object or a string.

        Returns:
            bool: True if the display was successful, False otherwise.
        """
        html_content = None
        if ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW DATA: {data}")
        print("From webview: ", data.action)
        try:
            if isinstance(data, StreamData):
                    
                html_content = self.generate_show_menu(data)
                self.webview.update_view(html_content)
                # if data.action in ["show_main_dishes", "show_side_dishes", "show_beverages"]:
                #     html_content = self.generate_show_menu(data)
                #     self.webview.update_view(html_content)
                    
                # elif data.action in ["add_item_to_cart", "remove_item_from_cart", "modify_item_quantity_in_cart"]:
                #     html_content = self.generate_cart_update(data)
                #     self.webview.update_view(html_content)
                
                # elif data.action in ["get_cart_contents"]:
                #     html_content = self.generate_order_review(data)
                #     self.webview.update_view(html_content)
                    
                # elif data.action in ["confirm_order"]:
                #     html_content = self.generate_confirmation(data)
                #     self.webview.update_view(html_content)
                    
            else:
                self.__wrap__(data)
            return True
        except Exception as e:
            if ENABLE_WEBVIEW_VERBOSITY:
                print(f"Error in display method: {str(e)}")
            return False
    
def display_dishes(data: StreamData) -> str:
    css_template = Template(MENU_PAGE_STYLE)
    html_template = Template(MENU_PAGE_TEMPLATE)
    menu_type_mapping = {
        "show_beverages": "beverages",
        "show_main_dishes": "main_dishes",
        "show_side_dishes": "side_dishes",
    }
    title_mapping = {
        "show_beverages": "KFC Beverages",
        "show_main_dishes": "KFC Main Dishes",
        "show_side_dishes": "KFC Side Dishes",
    }
    category_title = title_mapping.get(data.action, "Menu")
    current_menu_type = menu_type_mapping.get(data.action, "main_dishes")
        
    # Generate menu items HTML
    current_menu_items: List[Item] = []
    for m, menu in enumerate(data.menu):
        if menu.menu_type == current_menu_type:
            for item in menu.items:
                current_menu_items.append(Item(
                    name=item.name,
                    price_per_unit=item.price_per_unit,
                    image_url_path=get_base64_image(item.image_url_path),
                ))
            break
            
    # Generate cart items HTML
    cart_items = [
        Order(
            name=order.name,
            total_quantity=order.total_quantity,
            price_per_unit=order.price_per_unit,
            image_url_path=get_base64_image(order.image_url_path),
        ) for order in data.cart
    ]
        
    rendered_css = css_template.render({
        "menu_item_height": MENU_ITEM_HEIGHT,
        "cart_item_height": CART_ITEM_HEIGHT,
        "background_image": get_base64_image(MENU_BACKGROUND_IMAGE)
    })

    rendered_html = html_template.render({
        "css": rendered_css,
        "cart_items": cart_items,
        "category": category_title,
        "total_price": data.total_price,
        "menu_items": current_menu_items,
        "logo_image": get_base64_image(LOGO_IMAGE_PATH)
    })
    if ENABLE_WEBVIEW_VERBOSITY:
        print(f"WEBVIEW: `generate_show_menu` rendered successfully.")
    Webview.update_view(rendered_html)
    return rendered_html

def generate_cart_update(data: StreamData) -> str:
    # This should be called for any cart updates and return the rendered html
    return data.model_dump_json(indent=4)
    
def display_order_review(data: StreamData) -> str:
    css_template = Template(MENU_PAGE_STYLE)
    html_template = Template(ORDER_REVIEW_PAGE_TEMPLATE)

    # Generate cart items HTML
    cart_items = [
        Order(
            name=order.name,
            total_quantity=order.total_quantity,
            price_per_unit=order.price_per_unit,
            image_url_path=get_base64_image(order.image_url_path),
        ) for order in data.cart
    ]
        
    rendered_css = css_template.render({
        "menu_item_height": MENU_ITEM_HEIGHT,
        "cart_item_height": CART_ITEM_HEIGHT,
        "background_image": get_base64_image(MENU_BACKGROUND_IMAGE)
    })

    rendered_html = html_template.render({
        "css": rendered_css,
        "cart_items": cart_items,
        "total_price": data.total_price,
        "logo_image": get_base64_image(LOGO_IMAGE_PATH)
    })
    if ENABLE_WEBVIEW_VERBOSITY:
        print(f"WEBVIEW: `generate_show_menu` rendered successfully.")
    Webview.update_view(rendered_html)
    return rendered_html

def display_confirmation(data: StreamData) -> str:
    rendered_html = "<h1>Thank you for confirming the order...</h1>"
    Webview.update_view(rendered_html)
    return rendered_html
   
def view_data_dump(data: StreamData):
    Webview.update_view(data.model_dump_json()) 
