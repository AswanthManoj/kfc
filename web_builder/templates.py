HOME_PAGE_TEMPLATE = """
    <style>
        {{ css }}
    </style>
    <div class="background">
        <div class="container">
            <h1 class="title">KFC Voice Assistant</h1>
            <p class="subtitle">{{ catch_phrase }}</p>
        </div>
    </div>
"""

MENU_PAGE_TEMPLATE = """
    <style>
        {{ css }}
    </style>
    <div class="background"></div>
    <div class="container">
        <div class="menu">
            <img src="{{ logo_image }}" alt="KFC Logo" class="logo">
            <div class="category">{{ category }}</div>
            <div class="menu-grid">
                {% for item in menu_items %}
                <div class="item">
                    <img src="{{ item.image_url_path }}" alt="{{ item.name }}">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-price">${{ item.price_per_unit }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="cart">
            <h2>Your Order</h2>
            {% for order in cart_items %}
            <div class="cart-item">
                <img src="{{ order.image_url_path }}" alt="{{ order.name }}">
                <div class="cart-item-details">
                    <div class="cart-item-name">{{ order.name }}</div>
                    <div class="cart-item-quantity">Quantity: {{ order.total_quantity }}</div>
                    <div class="cart-item-price">Price: ${{ order.price_per_unit * order.total_quantity }}</div>
                </div>
            </div>
            {% endfor %}
            <div class="total">Total: ${{ total_price }}</div>
        </div>
    </div>
"""

