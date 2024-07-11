import os
from dotenv import load_dotenv

load_dotenv()
if not os.path.exists("downloads"):
    os.makedirs("downloads")


#################
# MODELS PARAMS #
#################
STT_MODEL = "nova-2"                       # Optional if stt backend is of deepgram
LLM_MODEL = "gpt-4o"                       # "gemma2-9b-it"# "llama3-8b-8192"
ROTATE_LLM_API_KEYS = True
TTS_MODEL = "aura-asteria-en"
STT_MODEL_SAMPLE_RATE = 48000
STT_END_OF_UTTERANCE_THRESHOLD = 1500
STT_MICROPHONE_BACKEND = "pyaudio"     # Set to `pyaudio` or `sounddevice` 
# STT_WORD_PROB_BOOSTS = [
#     "side dishes", "main dishes", "cart", "pepsi", "iced tea", "order", "hot dog",
#     "confirm", "mountain dew", "coleslaw", "french fries", "mac and cheese", "add", "remove",
#     "cream cheese", "mashed potatoes", "chizza", "burger", "saucy chicken", "drumstick", "show"
# ]
STT_WORD_PROB_BOOSTS = ["chizza", "coleslaw"]

#############################
# PRE-RECORDED SOUNDS PATHS #
#############################
DISFLUENCE = "responses/disfluencies"
INITIAL_RESPONSE = "responses/initial_responses"
INTERMEDIATE_RESPONSE = "responses/intermediate_responses"


####################
# WAKE WORD PARAMS #
####################
CHANNELS = 1
WAKE_WAIT_DELAY = 4
WAKE_SAMPLE_RATE = 16000
WAKE_WORD_MODEL = "openai/whisper-tiny.en"
WAKE_WORDS = [word.lower() for word in ["hi", "Hello", "hey there", "Hello K F C", "hi k f c"]]



#############
# DEBUGGING #
#############
ENABLE_LLM_VERBOSITY = True
ENABLE_STT_VERBOSITY = False
ENABLE_TTS_VERBOSITY = False
ENABLE_TOOL_VERBOSITY = True
ENABLE_WEBVIEW_VERBOSITY = True



################
# EXPERIMENTAL #
################
AUTO_LISTEN_WITHOUT_CLOSE = False
CONVERSATION_FOLDER = "saved_chats"



#############################
# ASSISTANT GUIDANCE PROMPT #
#############################
SYSTEM_PROMPT = """
You're a KFC drive-thru voice assistant. Use available functions to take orders efficiently. Follow these guidelines:

Casually greet customers and ask for their order. If they ask "What do you have?" or "What items are available?", ask which category they prefer: main dishes, side dishes, or beverages.

Use show_main_dishes(), show_side_dishes(), and show_beverages() to share menu options. After calling a function, tell the customer to check the screen for details, then briefly mention 2-3 popular items. If asked about all items, use show_main_dishes() first, then describe them.

Add items one at a time with add_item_to_cart(), always confirming quantity. Use remove_item_from_cart() or modify_item_quantity_in_cart() for order changes.

Review orders with get_cart_contents() if asked or before checkout for confirmation. Finalize confirmed orders with confirm_order().

Keep responses brief and focused on the order. Politely redirect off-topic questions to the menu or current order.

Speak naturally, occasionally using fillers like "um" or "uh" for a conversational tone. Avoid markdown lists, numbered lists, or overly formal language. Generate responses as paragraphs.

Be helpful but efficient to keep the line moving. Suggest popular items if customers seem unsure. Always ask if they'd like anything else before confirming the order.

The following menu contains our available items:

Menu:
{menu}
---

Use this information to assist customers with their orders and provide accurate item details.

**Note:** Always review the cart using `get_cart_contents()` before finalizing confirmation with `confirm_order()`  
"""