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
<div class="bg-gray-20 grid min-h-screen grid-cols-4 bg-gradient-to-br from-red-700 to-red-700">
    <div class="container col-span-3 mx-auto">
        <!-- Banner ad -->
        <!-- img class="w-full object-cover object-top" src="https://static-prod.adweek.com/wp-content/uploads/2024/06/kfcooh1-1024x538.png" alt="" /-->
        <!-- Banner ad end -->
        <h2 class="px-3 pt-4 text-2xl font-bold text-white">{{ category }}</h2>
        <div class="grid grid-cols-1 gap-2 p-2 md:grid-cols-2 lg:grid-cols-3">
            <!-- A menu item -->
            {% for item in menu_items %}
            <div class="rounded-md border bg-white p-0.5 shadow-md">
                <img class="h-[200px] w-full rounded-sm object-cover" src="{{ item.image_url_path }}" alt="{{ item.name }}"/>
                <div class="px-2 py-2">
                    <h2 class="text-lg font-semibold">{{ item.name }}</h2>
                    <h2 class="text-lg text-gray-600">${{ item.price_per_unit }}</h2>
                </div>
            </div>
            {% endfor %}
            <!-- Menu item end -->
        </div>
    </div>
    <div class="sticky top-0 col-span-1 flex h-screen flex-col justify-between bg-gradient-to-t from-zinc-950 to-zinc-950/70 px-3 py-4">
        <div>
            <p class="text-2xl text-white">Your cart</p>
            <p class="mt-1 text-xl text-white/60">Total price ${{ total_price }}</p>
        <div class="cart-items mt-3 grid grid-cols-1 gap-2">
        <!-- A cart item -->
        {% for order in cart_items %}
        <div class="flex items-center gap-3 rounded-md bg-white/20 p-1">
            <img class="h-12 w-12 rounded-md object-cover" src="{{ order.image_url_path }}" alt="{{ order.name }}" />
            <div>
                <p class="font-semibold text-white">{{ order.name }}</p>
                <p class="text-xs text-white/40">x{{ order.total_quantity }} · ${{ order.price_per_unit}}</p>
            </div>
        </div>
        {% endfor %}
        <!-- Cart item end -->
      </div>
    </div>
    
    <!-- Bottom section of Cart panel showing gif and transcript -->
    <div>
        <img class="mix-blend-lighten" src="https://cdn.dribbble.com/users/651656/screenshots/5297182/untitled-4.gif" alt="" />
        <div class="p-2">
            <!-- Transcript start -->
            <div class="flex flex-col gap-2">
                <p class="inline-block bg-gradient-to-b from-white/30 to-white bg-clip-text text-base text-transparent">
                    {{ role1 }} {{ turn1 }}
                    <br />
                    <br />
                    {{ role2 }} {{ turn2 }}
                </p>
            </div>
            <!-- Transcript end -->
        </div>
    </div>
    <!-- Bottom section end -->
    </div>
</div>
"""

ORDER_REVIEW_PAGE_TEMPLATE = """
    <style>
        {{ css }}
    </style>
    <div class="background"></div>
    <div class="menu">
        <img src="{{ logo_image }}" alt="KFC Logo" class="logo">
        <div class="category">Your Cart</div>
        <div class="menu-grid">
            {% for item in cart_items %}
            <div class="item">
                <img src="{{ item.image_url_path }}" alt="{{ item.name }}">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-price">Quantity: {{ item.total_quantity }} | Total price of Item {{ item.price_per_unit * item.total_quantity }}</div>
            </div>
            {% endfor %}
        </div>
        <h1>Total Price: ${{ total_price }}</h1>
    </div>
"""

CONFIRMATION_PAGE_TEMPLATE = """
"""

















#################################
# DEPRECATED MENU PAGE TEMPLATE #
#################################
'''
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
'''