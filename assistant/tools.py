from langchain_core.tools import tool
from assistant.menu import get_order_cart

  
################
# MENU METHODS #
################
@tool
def get_main_dishes() -> str:
    """
    Retrieve available main dishes and their prices.
        
    Returns:
    str: A menu list with main dishes and their prices.
    """
    order_cart = get_order_cart()
    return order_cart.get_main_dishes()
    
@tool
def get_sides() -> str:
    """
    Retrieve available side dishes and their prices.

    Returns:
    str: A menu list with side dishes and their prices.
    """
    order_cart = get_order_cart()
    return order_cart.get_sides()
   
@tool 
def get_beverages() -> str:
    """
    Retrieve available beverages and their prices.

    Returns:
    str: A menu list with beverages and their prices.
    """
    order_cart = get_order_cart()
    return order_cart.get_beverages()
 

################
# CART METHODS #
################
@tool
def add_item_to_cart(item_name: str, quantity: int = 1) -> str:
    """
    Add an item to the cart. Use this function when a customer wants to add an item to their order. 
        
    **Note:** If quantity is not specified by the user, you should ask the user for quantity before adding the item.
        
    Args:
    item_name (str): The name of the item to add.
    quantity (int): The quantity of the item to add. Defaults to 1.
        
    Returns:
    str: Information about the name, price per unit, and total quantity of the added item in cart.
    """
    order_cart = get_order_cart()
    return order_cart.add_item(item_name, quantity)
       
@tool
def remove_item_from_cart(item_name: str, quantity: int = 1, remove_all: bool=False) -> str:
    """
    Remove an item from the cart. Use this function when a customer wants to remove an item from their order.

    Args:
    item_name (str): The name of the item to remove.
    quantity (int): The quantity of the item to remove. Defaults to 1.
    remove_all (bool): If True then removes all of the quantities of `item_name` from the cart. Default to False

    Returns:
    str: Information about the item name and its remaining quantity in cart, or if it was fully removed.
    """
    order_cart = get_order_cart()
    return order_cart.remove_item(item_name, quantity, remove_all)

@tool
def modify_item_quantity_in_cart(item_name: str, new_quantity: int) -> str:
    """
    Modify the quantity of an item in the cart. Use this function when a customer wants to change the quantity of an item in their order.

    Args:
    item_name (str): The name of the item to modify.
    new_quantity (int): The new quantity for the item.

    Returns:
    str: Information about the item name and its updated quantity in cart.
    """
    order_cart = get_order_cart()
    return order_cart.modify_quantity(item_name, new_quantity)

@tool
def get_cart_contents() -> str:
    """
    Get the current contents of the cart along with total price of the items in the cart. Use this function when a customer wants to review their current order.

    Returns:
    str: Information about the current contents of the cart along with their total price.
    """
    order_cart = get_order_cart()
    return order_cart.get_cart_contents()

@tool
def confirm_order() -> str:
    """
    Confirm and finalize the order. Use this function when a customer is ready to place their order.

    Returns:
    str: Information with a confirmation message and order details. Gracefully greet the customer and end the conversation.
    """
    order_cart = get_order_cart()
    return order_cart.confirm_order()

def get_available_tools() -> dict:
    return { 
        "get_sides": get_sides, 
        "confirm_order": confirm_order, 
        "get_beverages": get_beverages,
        "get_main_dishes": get_main_dishes,
        "add_item_to_cart": add_item_to_cart,
        "get_cart_contents": get_cart_contents,
        "remove_item_from_cart": remove_item_from_cart,
        "modify_item_quantity_in_cart": modify_item_quantity_in_cart,
    }