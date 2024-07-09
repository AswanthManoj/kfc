import os, base64
import yaml, random
from webview import Webview
from typing import List, Optional
from jinja2 import Template, Environment
from config import ENABLE_WEBVIEW_VERBOSITY
from .styles import HOME_PAGE_STYLE, MENU_PAGE_STYLE
from assistant.utils import StreamData, Message, Item
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
    """
    A class to manage the web view interface for the KFC Voice Assistant application.

    This class handles the creation and updating of web pages, including the home page
    and menu pages. It uses Jinja2 templates to render HTML content and manages the
    display of menu items, cart contents, and other UI elements.

    Attributes:
        webview (Webview): The webview instance for rendering the UI.
    """
    def __init__(self, host: str="127.0.0.1", port: int=8080, debug: bool=False, title: str="KFC Voice Assistant", log_level: str="warning"):
        """
        Initialize the WebViewApp with specified configuration.

        Args:
            host (str): The host address for the webview. Defaults to "127.0.0.1".
            port (int): The port number for the webview. Defaults to 8080.
            debug (bool): Whether to run in debug mode. Defaults to False.
            title (str): The title of the webview window. Defaults to "KFC Voice Assistant".
            log_level (str): The logging level for the webview. Defaults to "warning".
        """
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
        """
        Wrap content in a paragraph tag.

        Args:
            content (str): The content to wrap.

        Returns:
            str: The wrapped content.
        """
        return f"<div>{content}</div>"

    def __get_base64_image__(self, image_path: str) -> str:
        """
        Convert an image file to a base64-encoded string.

        Args:
            image_path (str): The path to the image file.

        Returns:
            str: The base64-encoded image data URI.
        """
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
        """
        Generate the HTML content for the home page.

        Returns:
            str: The rendered HTML content for the home page.
        """
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
            print(f"WEBVIEW DATA BEFORE STATE UPDATE: {data}")
        try:
            if isinstance(data, StreamData):

                if ENABLE_WEBVIEW_VERBOSITY:
                    print("WEBVIEW DATA AFTER STATE UPDATE:", data)
                    
                if data.action in ["show_main_dishes", "show_side_dishes", "show_beverages"]:
                    html_content = self.generate_show_menu(data)
                    self.webview.update_view(html_content)
                    
                elif data.action in ["add_item_to_cart", "remove_item_from_cart", "modify_item_quantity_in_cart"]:
                    html_content = self.generate_cart_update(data)
                    self.webview.update_view(html_content)
                
                elif data.action in ["get_cart_contents"]:
                    html_content = self.generate_order_review(data)
                    self.webview.update_view(html_content)
                    
                elif data.action in ["confirm_order"]:
                    html_content = self.generate_confirmation(data)
                    self.webview.update_view(html_content)
                    
            else:
                self.__wrap__(data)
            return True
        except Exception as e:
            if ENABLE_WEBVIEW_VERBOSITY:
                print(f"Error in display method: {str(e)}")
            return False
    
    def generate_show_menu(self, data: StreamData) -> str:
        """
        Generate the HTML content for displaying a menu page.

        Args:
            data (StreamData): The data containing menu items and cart information.

        Returns:
            str: The rendered HTML content for the menu page.
        """
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
        if ENABLE_WEBVIEW_VERBOSITY:
            print(f"WEBVIEW: `generate_show_menu` rendered successfully.")
        return rendered_html

    def generate_cart_update(self, data: StreamData) -> str:
        # This should be called for any cart updates and return the rendered html
        return data.model_dump_json(indent=4)
    
    def generate_order_review(self, data: StreamData) -> str:
        # This should be called to generate the order/cart review html page
        return data.model_dump_json(indent=4)
    
    def generate_confirmation(self, data: StreamData) -> str:
        # This should be called to generate the html page for order confirmation
        return data.model_dump_json(indent=4)
    
    


