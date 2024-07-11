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
<div class="bg-gray-20 grid min-h-screen grid-cols-4">
    <div class="bg-kfc"></div>
    <div class="container max-w-5xl col-span-3 mx-auto">
        <!-- Banner ad -->
        <!-- img class="w-full object-cover object-top" src="https://static-prod.adweek.com/wp-content/uploads/2024/06/kfcooh1-1024x538.png" alt="" /-->
        <!-- Banner ad end -->
        <h2 class="px-3 pt-4 text-3xl mb-3 font-bold text-white">{{ category }}</h2>
        <div class="grid grid-cols-1 gap-2 p-2 md:grid-cols-2 lg:grid-cols-3">
            <!-- A menu item -->
            {% for item in menu_items %}
            <div class="rounded-md border border-white/10 backdrop-blur-lg p-0.5 shadow-md">
                <img class="h-[200px] w-full rounded-sm object-cover" src="{{ item.image_url_path }}" alt="{{ item.name }}"/>
                <div class="px-2 py-2">
                    <h2 class="text-xl text-white font-semibold">{{ item.name }}</h2>
                    <p class="text-xl text-white font-semibold">${{ item.price_per_unit | round(2) }}</h2>
                </div>
            </div>
            {% endfor %}
            <!-- Menu item end -->
        </div>
    </div>
    <div class="sticky top-0 col-span-1 flex h-screen flex-col justify-between bg-gradient-to-t from-black via-black to-red-900/80 backdrop-blur-md px-3 py-4">
        <div>
            <p class="text-2xl text-white">Your cart</p>
            <p class="mt-1 text-xl text-white">Total price ${{ total_price | round(2) }}</p>
        <div class="cart-items mt-3 grid grid-cols-1 gap-2">
        <!-- A cart item -->
        {% for order in cart_items %}
        <div class="flex items-center gap-3 rounded-md bg-white/20 p-1">
            <img class="h-12 w-12 rounded-md object-cover" src="{{ order.image_url_path }}" alt="{{ order.name }}" />
            <div>
                <p class="font-semibold text-white">{{ order.name }}</p>
                <p class="text-xs text-white/40">x{{ order.total_quantity }} · ${{ order.price_per_unit | round(2) }}</p>
            </div>
        </div>
        {% endfor %}
        <!-- Cart item end -->
      </div>
    </div>
    
    <!-- Bottom section of Cart panel showing gif and transcript -->
    <div>
        {% if show_gif %}
            <p class="mt-1 text-sm text-white/60">Listening...</p>
            <img class="mix-blend-lighten" src="https://cdn.dribbble.com/users/651656/screenshots/5297182/untitled-4.gif" alt="" />
        {% endif %}
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
    body {
        background-image: url('{{ background_image }}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        min-height: 100vh;
    }
    .backdrop {
        background-color: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
        min-height: 100vh;
    }
</style>
<div class="flex min-h-screen items-center justify-center bg-black/50 backdrop-blur-md">
    <div class="m-4 max-w-md rounded-xl bg-white/10 p-8 shadow-lg backdrop-blur-lg">
        <h2 class="mb-6 text-3xl font-bold text-white">Let's review your order</h2>
        <div class="space-y-4">
            <!-- A cart item -->
            {% for item in cart_items %}
            <div class="flex items-center justify-between rounded-lg bg-white/20 p-4">
                <div class="flex items-center space-x-4">
                    <img src="{{ item.image_url_path }}" alt="{{ item.name }}" class="h-16 w-16 rounded-md object-cover">
                    <div>
                        <p class="font-semibold text-white">{{ item.name }}</p>
                        <p class="text-sm text-white/60">${{ item.price_per_unit | round(2) }} each</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="font-semibold text-white">x{{ item.total_quantity }}</p>
                    <p class="text-sm text-white/60">${{ (item.price_per_unit * item.total_quantity | round(2)) | string }}</p>
                </div>
            </div>
            {% endfor %}
            <!-- Cart item end -->
        </div>
        <div class="mt-6 rounded-lg bg-red-600 p-4">
            <div class="flex items-center justify-between">
                <p class="text-lg font-semibold text-white">Total price</p>
                <p class="text-2xl font-bold text-white">${{ total_price }}</p>
            </div>
        </div>
    </div>
</div>
"""

CONFIRMATION_PAGE_TEMPLATE = """
<style>
    {{ css }}
</style>
<div class="h-screen bg-[#289b51] items-center flex flex-col justify-center">
  <img class="object-cover max-h-56" src="https://cdn.dribbble.com/users/208474/screenshots/4356546/save_800x600.gif">
  <h2 class="text-center text-white text-3xl font-bold">Thank you for your order!</h2>
  <p class="text-white/70 text-center max-w-md mx-auto mt-3">{{ message }}</p>
</div>
"""


