# KFC Food Ordering Assistant

## Overview
The KFC Food Ordering Assistant is an low-latency interactive voice assistant designed to streamline the ordering process at KFC.

```mermaid
flowchart TD
    start(Voice Listening Starts) --> listen[Wait for User Input]
    listen -->|End of Utterance| transcribe[Transcribe Speech to Text]
    transcribe --> agent_call[Send Output to LLM Agent]

    agent_call -->|Tool Call Needed| play_intermediate[Play Intermediate Response]
    play_intermediate --> tool_call[Invoke Tool]
    tool_call --> play_response[Play intermediate response]
    tool_call --> tool_output[Get Tool Output]
    tool_output --> agent_call

    agent_call -->|No Tool Call Needed| final_response[Generate Final Response]
    final_response --> tts[Convert Final Response to Speech]
    tts --> check[Check if Order is Confirmed]

    check -->|Order Not Confirmed| listen[Wait for User Input Again]
    check -->|Order Confirmed| end_interaction[End Voice Interaction]

    class start,listen,transcribe,agent_call,play_intermediate,tool_call,tool_output,final_response,tts,check,end_interaction classStep;
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/sajithamma/kfc.git
cd kfc
```

---
2. Setting up virtual environment and installing dependencies:
- Creating virtual environment
    ```bash 
    pip install poetry
    poetry install
    ```


---
3. Set up API keys and environment variables:
    - Create a `.env` file in the project root folder.

    ```bash
    ASSEMBLY_API_KEY=<your-assemblyai-api-key>
    DEEPGRAM_API_KEY=<your-deepgram-api-key>
    GROQ_API_KEY=<your-groq-api-key>
    OPENAI_API_KEY=<your-openai-api-key>

    OPENAI_API_KEYS=["openai-api-key1", "openai-api-key2", ...]
    GROQ_API_KEYS=["groq-api-key1", "groq-api-key2", ...]
    ```

    - Click [here](https://www.assemblyai.com/), to get api key from assemblyai.
    - Click [here](https://deepgram.com/), to get api key from deepgram.
    - For llm either use groq or openai:
        - Click [here](https://groq.com/), to get api key from groq.

        - Click [here](https://openai.com/), to get api key from openai.


**Note:** To enable rotation of api keys for groq, set a variable `GROQ_API_KEYS=["<api-key1>", "<api-key2>", "<api-key3>"]` or `OPENAI_API_KEYS=["<api-key1>", "<api-key2>", "<api-key3>"]` in `.env` and set `ROTATE_LLM_API_KEYS` variable to be `True` in `config.py`.

---
4. Run the application:
```bash
poetry run python app.py
```

---

### Project Structuring:

#### Webview and related UI methods: 

    - web_builder/builder.py : For Webview class and related UI manipulation methods.
    - web_builder/templates.py : For html template definitions.

#### Assistant Utilities related Classes and Methods:

    - assistant/agent.py : Contains Speech to text, Text to speech, Langchain agent definitions and Wake-word detector.
    - assistant/menu.py : Contains the menu parent class and its subclass for cart with singleton definition with available items.
    - assistant/tools.py : Contains the langchain agent tools whose functionalities where defined within `assistant/menu.py/OrderCart` classes methods.
    - assistant/utils.py : Contains the pydantic model definitions and Microphone object class for the `assemblyai` to listen with (package's Microphone class didn't had a pause option)

#### startup.py:

    - Initializes all utility classes.

#### config.py:

    - Defines debugging, system prompt, global variables etc.

#### app.py:
Contains two main functions:
    - `main1` method uses voice features as user input to assistant.
    - `main2` method uses console input as user input to assistant.

#### Note: All intermediate voice plays and UI updates are done from the tool calls itself from `assistant/menu.py/OrderCart` and `assistant/menu.py/KFCMenu` class's methods


#### For debugging purposes you can enable or dissable `ENABLE_LLM_VERBOSITY`, `ENABLE_STT_VERBOSITY`, `ENABLE_TTS_VERBOSITY`, `ENABLE_TOOL_VERBOSITY`, `ENABLE_WEBVIEW_VERBOSITY` variables in `config.py` to controll individual modules verbosity.