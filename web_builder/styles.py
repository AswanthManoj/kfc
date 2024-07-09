
HOME_PAGE_STYLE = """
body, html { 
    margin: 0; 
    height: 100%; 
    font-family: Arial, sans-serif; 
}
.background { 
    background-image: url('{{ background_image }}'); 
    height: 100%; 
    background-position: center; 
    background-repeat: no-repeat; 
    background-size: cover; 
    display: flex; 
    align-items: center; 
    justify-content: center; 
}
.container { 
    background: rgba(255, 255, 255, 0.15); 
    backdrop-filter: blur(10px);padding: 30px; 
    border-radius: 20px; 
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    background: linear-gradient(
        135deg, 
        rgba(255, 255, 255, 0.1), 
        rgba(255, 255, 255, 0.05)
    ); 
}
.title { 
    color: white; 
    font-size: 3.5em; 
    margin-bottom: 15px; 
    font-weight: 900; 
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); 
}
.subtitle { 
    color: white; 
    font-size: 1.4em; 
    font-weight: 600; 
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3); 
}
"""




##############################
# DEPRECATED MENU PAGE STYLE #
##############################
MENU_PAGE_STYLE = """
body { 
    font-family: Arial, sans-serif; 
    margin: 0; 
    padding: 0; 
    background-color: #f8f8f8; 
}
.background { 
    position: fixed; 
    top: 0; 
    left: 0; 
    width: 100%; 
    height: 100%; 
    background-image: url('{{ background_image }}'); 
    background-size: cover; 
    background-position: center; 
    filter: blur(5px); 
    z-index: -1; 
}
.container { 
    display: flex; 
    height: 100vh; 
}
.menu { 
    flex: 3; 
    overflow-y: auto; 
    padding: 20px; 
}
.cart { 
    flex: 1; 
    background-color: #101010; 
    padding: 20px; 
    display: flex; 
    flex-direction: column; 
    color: white; 
}
.logo { 
    max-width: 100px; 
    margin-bottom: 20px; 
}
.category { 
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 20px;
    color: #ffffff; 
}
.menu-grid { 
    display: grid; 
    grid-template-columns: repeat(2, 1fr); 
    gap: 20px; 
}
        
.item { 
    border: 1px solid rgba(221, 221, 221, 0.7); 
    padding: 10px; 
    background-color: rgba(255, 255, 255, 0.1); 
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    backdrop-filter: blur(12px);
    border-radius: 10px;
    height: {{ menu_item_height }}px; 
    display: flex; 
    opacity: 0.95;
    transition: transform 0.2s ease-in-out;
    flex-direction: column; 
}
.item img { 
    width: 100%; 
    height: calc({{ menu_item_height }}px - 80px); 
    object-fit: cover; margin-bottom: 10px; 
}
.item-name { 
    font-size: 24px; 
    font-weight: bolder; 
    color: #ffffff; 
    margin-bottom: 5px; 
}
.item-price { 
    font-weight: bold; 
    color: white; 
    font-size: 30px; 
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3); 
}
        
.cart-item { 
    display: flex; 
    margin-bottom: 15px; 
    background-color: #303030; 
    padding: 10px; 
    border-radius: 5px; 
    height: {{ cart_item_height }}px; 
}
.cart-item img { 
    width: {{ cart_item_height }}px; 
    height: {{ cart_item_height }}px; 
    object-fit: cover; 
    margin-right: 15px; 
}
.cart-item-details { 
    flex-grow: 1; 
    display: flex; flex-direction: column; 
    justify-content: center; 
}
.cart-item-name { 
    font-size: 18px; 
    font-weight: bold; 
    margin-bottom: 5px; 
}
.cart-item-quantity, .cart-item-price { 
    font-size: 14px; 
}
.total { 
    font-size: 22px; 
    font-weight: bold; 
    margin-top: auto; 
    background-color: #e4002b; 
    color: white; 
    padding: 10px; 
    border-radius: 5px; 
    text-align: center; 
}
"""