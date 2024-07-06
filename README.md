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
2. Setting up virtual environment
- Creating virtual environment
    ```bash 
    python -m venv venv
    ```

- Activating on windows:
    ```bash
    .\venv\Scripts\activate
    ```

- Activating on linux:
    ```bash
    source venv/bin/activate
    ```
    
- Installing dependencies:
    ```bash
    pip install -r requirements.txt
    ```

---
3. Set up API keys (one time):
    - Create a `.env` file in the project root folder.
    - Go to [Assembly ai's website](https://www.assemblyai.com/), login and get an API key paste it inside `.env` file as `ASSEMBLY_API_KEY=<your-api-key>`.
    - Go to [Deepgram's website](https://deepgram.com/), login and get an API key paste it inside `.env` file as `DEEPGRAM_API_KEY=<your-api-key>`.
    - Go to [Groq's website](https://groq.com/), login and get the API key then paste it inside `.env` as `GROQ_API_KEY=<your-api-key>`.

**Note:** To enable rotation of api keys for groq, set a variable `GROQ_API_KEYS=["<api-key1>", "<api-key2>", "<api-key3>"]` in `.env` and set `ROTATE_LLM_API_KEYS` variable to be `True` in `config.py`.

---
4. Run the application:
```bash
python app.py
```
