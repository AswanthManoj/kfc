# import webview
import os, base64
import yaml, random
from webview import Webview
from typing import List, Optional
from jinja2 import Template, Environment
from config import ENABLE_WEBVIEW_VERBOSITY
from .styles import HOME_PAGE_STYLE, MENU_PAGE_STYLE
from assistant.utils import StreamData, StreamMessages, Item
from .templates import HOME_PAGE_TEMPLATE, MENU_PAGE_TEMPLATE


env = Environment()
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


class WebViewApp:
    def __init__(self, host: str="127.0.0.1", port: int=8080, debug: bool=False, title: str="KFC Voice Assistant", log_level: str="warning"):
        self.webview = Webview
        self.webview.configure(
            title=title, host=host, 
            port=port, debug=debug, log_level=log_level
        )
        is_started = self.webview.start_webview()
        self.webview.update_view(self.get_home())
        env.filters['base64_encode'] = self.__get_base64_image__
        
        if is_started and ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW: Started webview")
    
    def __wrap__(self, content:str):
        return f"<p>{content}</p>"

    def __get_base64_image__(self, image_path: str) -> str:
        try:
            image_path = os.path.join(BASE_DIR, image_path)
            with open(image_path, "rb") as image_file:
                encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
                if ENABLE_WEBVIEW_VERBOSITY:
                    print(f"WEBVIEW: Successfully encoded image: {image_path}, encoded data length: {len(encoded_data)}")
                return f"data:image/png;base64,{encoded_data}"
        except Exception as e:
            if ENABLE_WEBVIEW_VERBOSITY:
                print(f"WEBVIEW: Error encoding image {image_path}: {str(e)}")
            return ""

    def get_home(self) -> str:
        css_template = Template(HOME_PAGE_STYLE)
        html_template = Template(HOME_PAGE_TEMPLATE)
        
        rendered_css = css_template.render({
            "background_image": self.__get_base64_image__(HOME_BACKGROUND_IMAGE)
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
        if ENABLE_WEBVIEW_VERBOSITY:
            print("WEBVIEW: Home page HTML generated")
        return rendered_html
    
    def display(self, data: StreamData|str) -> bool:
        html_content = None
        if ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW DATA: {data}")
        try:
            if isinstance(data, StreamData):
                if data.action in ["show_main_dishes", "show_side_dishes", "show_beverages"]:
                    html_content = self.generate_show_menu(data)
                    self.webview.update_view(html_content)
                elif data.action in ["add_item_to_cart"]:
                    # Add the html renderer for add_item_to_cart
                    pass
                elif data.action in ["remove_item_from_cart"]:
                    # Add the html renderer for remove_item_from_cart
                    pass
                elif data.action in ["modify_item_quantity_in_cart"]:
                    # Add the html renderer for modify_item_quantity_in_cart
                    pass
                elif data.action in ["get_cart_contents"]:
                    # Add the html renderer for get_cart_contents
                    pass
                else:
                    # Add the html renderer for confirm_order
                    pass
            else:
                self.__wrap__(data)
            if ENABLE_WEBVIEW_VERBOSITY:
                print(f"WEBVIEW HTML: {html_content[:500]}...")
            return True
        except Exception as e:
            if ENABLE_WEBVIEW_VERBOSITY:
                print(f"Error in display method: {str(e)}")
            return False
    
    def generate_show_menu(self, data: StreamData) -> str:
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
        current_menu_type = menu_type_mapping.get(data.action, "main_dish")
        
        # Generate menu items HTML
        current_menu_items: List[Item] = []
        for m, menu in enumerate(data.menu):
            if menu.menu_type == current_menu_type:
                for i, item in enumerate(menu.items):
                    data.menu[m].items[i].image_url_path = self.__get_base64_image__(item.image_url_path)
                    current_menu_items.append(item)
                break
            
        # Generate cart items HTML
        for o, order in enumerate(data.cart):
            data.cart[o].image_url_path = self.__get_base64_image__(order.image_url_path)
        
        rendered_css = css_template.render({
            "menu_item_height": MENU_ITEM_HEIGHT,
            "cart_item_height": CART_ITEM_HEIGHT,
            "background_image": self.__get_base64_image__(MENU_BACKGROUND_IMAGE)
        })

        rendered_html = html_template.render({
            "css": rendered_css,
            "cart_items": data.cart,
            "category": category_title,
            "total_price": data.total_price,
            "menu_items": current_menu_items,
            "logo_image": self.__get_base64_image__(LOGO_IMAGE_PATH)
        })
        print(rendered_html[:500])
        return rendered_html



'''
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
                if ENABLE_WEBVIEW_VERBOSITY:
                    print("WEBVIEW Menu Item:", order)
                menu_items_html += f"""
                <div class="item">
                    <img src="data:image/jpg;base64,{image_data}" alt="{item.name}">
                    <div class="item-name">{item.name}</div>
                    <div class="item-price">${item.price_per_unit}</div>
                </div>
                """
    
    # Generate cart items HTML
    cart_items_html = ""
    for order in data.cart:
        image_path = os.path.join(BASE_DIR, order.image_url_path)
        image_data = get_base64_image(image_path)
        if ENABLE_WEBVIEW_VERBOSITY:
            print("WEBVIEW Order Item:", order)
        cart_items_html += f"""
        <div class="cart-item">
            <img src="data:image/jpg;base64,{image_data}" alt="{order.name}">
            <div class="cart-item-details">
                <div class="cart-item-name">{order.name}</div>
                <div class="cart-item-quantity">Quantity: {order.total_quantity}</div>
                <div class="cart-item-price">Price: ${order.price_per_unit * order.total_quantity}</div>
            </div>
        </div>
        """
    
    html_content: str = MENU_PAGE_TEMPLATE.replace("{category}", category_title)
    html_content = html_content.replace("{cart_items}", cart_items_html)
    html_content = html_content.replace("{menu_items}", menu_items_html)
    html_content = html_content.replace("{total_price}", str(data.total_price))
    html_content = html_content.replace("{menu_item_height}", str(MENU_ITEM_HEIGHT))
    html_content = html_content.replace("{cart_item_height}", str(CART_ITEM_HEIGHT))
    html_content = html_content.replace("{logo_image}", f"data:image/png;base64,{logo_image_data}")
    html_content = html_content.replace("{background_image}", f"data:image/jpg;base64,{menu_background_image_data}")
    
    if ENABLE_WEBVIEW_VERBOSITY:
        print("WEBVIEW: Menu page HTML generated")
    return html_content


def generate_order_updates(data: StreamData) -> str:
    pass
    


'''