import asyncio
from dotenv import load_dotenv
from test_utils import ConversationManager

load_dotenv()


stt_model = "nova-2"
llm_model = "llama3-8b-8192"
tts_model = "aura-asteria-en"
 
if __name__ == "__main__":
    manager = ConversationManager(
        stt_model_id=stt_model,
        llm_model_id=llm_model,
        tts_model_id=tts_model
    )
    # asyncio.run(manager.main()) # For automatic listening and response
    asyncio.run(manager.main2())
