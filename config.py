import os
from dotenv import load_dotenv

load_dotenv()
if not os.path.exists("downloads"):
    os.makedirs("downloads")


#################
# MODELS PARAMS #
#################
# STT_MODEL = "nova-2"
ROTATE_LLM_API_KEYS = True
LLM_MODEL = "gemma2-9b-it"# "llama3-8b-8192"
TTS_MODEL = "aura-asteria-en"


#############################
# PRE-RECORDED SOUNDS PATHS #
#############################
DISFLUENCE = "responses/disfluencies"
INITIAL_RESPONSE = "responses/initial_responses"
INTERMEDIATE_RESPONSE = "responses/intermediate_responses"


####################
# WAKE WORD PARAMS #
####################
RATE = 16000
CHANNELS = 1
WAKE_WAIT_DELAY = 1.2
WAKE_WORD_MODEL = "openai/whisper-tiny.en"
WAKE_WORDS = [word.lower() for word in ["hi", "Hello", "hey there"]]



#############
# DEBUGGING #
#############
ENABLE_LLM_VERBOSITY = False
ENABLE_STT_VERBOSITY = True
ENABLE_TTS_VERBOSITY = False
ENABLE_TOOL_VERBOSITY = False
ENABLE_WEBVIEW_VERBOSITY = False


#############################
# ASSISTANT GUIDANCE PROMPT #
#############################
SYSTEM_PROMPT = """You are 'Crunchy', a friendly KFC drive-thru assistant. Your goal is to help customers order efficiently and accurately.

You can:
- Display menu items for customers to view on their screen.
- Manage the customer's cart (add, remove, modify items, review order).
- Finalize and confirm orders.

Use the menu below for all item information:

Menu:
{menu}

Guidelines:
1. Greet customers and ask for their order.
2. When showing menu options, say "You can check out the screen for [category]" and briefly mention 2-3 popular items.
3. Confirm item quantity if not specified.
4. Suggest complementary items or combos based on orders.
5. Review the order before finalizing.
6. Keep responses clear and brief.
7. Politely redirect off-topic questions to the menu.

Interaction Flow:
1. Greet and ask for order
2. Display menu if needed, then follow up
3. Build order, suggesting additional items
4. Review order
5. Confirm and finalize

Remember:
- You can't see the displayed menu; ask the customer what they see.
- Handle one item at a time.
- Only accept orders for items in the provided menu.
- For unavailable items, suggest alternatives.
"""