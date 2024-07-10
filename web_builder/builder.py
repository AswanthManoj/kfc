import random
import os, base64
from typing import List
from jinja2 import Template
from webview import Webview
from .styles import HOME_PAGE_STYLE
from config import ENABLE_WEBVIEW_VERBOSITY
from assistant.utils import StreamData, Item, Order
from .tailwind_menu_page_style import MENU_PAGE_STYLE
from .tailwind_review_page_style import ORDER_REVIEW_PAGE_STYLE
from .tailwind_confirmation_page_style import CONFIRMATION_PAGE_STYLE
from .templates import HOME_PAGE_TEMPLATE, MENU_PAGE_TEMPLATE, ORDER_REVIEW_PAGE_TEMPLATE, CONFIRMATION_PAGE_TEMPLATE


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

def display(data: StreamData):
    rendered_html = ""
    if data.action is None:
        rendered_html = display_home_page()
    elif data.action in ["show_beverages", "show_main_dishes", "show_side_dishes", \
        "add_item_to_cart", "remove_item_from_cart", "modify_item_quantity_in_cart"]:
        rendered_html = display_dishes(data)
    elif data.action == "get_cart_contents":
        rendered_html = display_order_review(data)
    elif data.action == "confirm_order":
        rendered_html = display_confirmation()
    else:
        rendered_html = display_data_dump(data)
    try:    
        Webview.update_view(rendered_html)
    except Exception as e:
        print("Unable to update the webview, likely due to disconnection of the client browser", str(e))
        return False
    return True

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
    if ENABLE_WEBVIEW_VERBOSITY:
        print(f"WEBVIEW: `display_home_page` rendered successfully.")
    return rendered_html

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
    
    turn1, turn2, role1, role2 = "", "", "", ""
    if len(data.stream_messages)>1:
        role1 = data.stream_messages[-2].role
        turn1 = data.stream_messages[-2].content
        role2 = data.stream_messages[-1].role
        turn2 = data.stream_messages[-1].content
        role1 = "AI:" if role1=='assistant' else "You:" 
        role2 = "AI:" if role2=='assistant' else "You:" 
    elif data.stream_messages:
        role1 = data.stream_messages[-1].role
        turn1 = data.stream_messages[-1].content
        role1 = "AI:" if role1=='assistant' else "You:"
    
    show_gif = True if role2=="AI:" else False
        
    rendered_css = css_template.render({
        "background_image": get_base64_image(MENU_BACKGROUND_IMAGE)
    })

    rendered_html = html_template.render({
        "role1": role1,
        "role2": role2,
        "turn1": turn1,
        "turn2": turn2,
        "css": rendered_css,
        "show_gif": show_gif,
        "cart_items": cart_items,
        "category": category_title,
        "menu_items": current_menu_items,
        "total_price": round(data.total_price, 2),
        "logo_image": get_base64_image(LOGO_IMAGE_PATH),
    })
    if ENABLE_WEBVIEW_VERBOSITY:
        print(f"WEBVIEW: `display_dishes` rendered successfully.")
    return rendered_html

def display_order_review(data: StreamData) -> str:
    css_template = Template(ORDER_REVIEW_PAGE_STYLE)
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
        "background_image": get_base64_image(MENU_BACKGROUND_IMAGE)
    })

    rendered_html = html_template.render({
        "css": rendered_css,
        "cart_items": cart_items,
        "total_price": round(data.total_price, 2),
        "logo_image": get_base64_image(LOGO_IMAGE_PATH),
        "background_image": get_base64_image(MENU_BACKGROUND_IMAGE)
    })
    if ENABLE_WEBVIEW_VERBOSITY:
        print(f"WEBVIEW: `display_order_review` rendered successfully.")
    return rendered_html

def display_confirmation() -> str:
    css_template = Template(CONFIRMATION_PAGE_STYLE)
    html_template = Template(CONFIRMATION_PAGE_TEMPLATE)
    rendered_css = css_template.render({})
    rendered_html = html_template.render({"css": rendered_css})
    if ENABLE_WEBVIEW_VERBOSITY:
        print(f"WEBVIEW: `display_confirmation` rendered successfully.")
    return rendered_html
   
def display_data_dump(data: StreamData) -> str:
    return data.model_dump_json()
