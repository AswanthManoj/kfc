from config import LLM_MODEL
from startup import get_audio_manager
from tools import get_available_tools
from agent import ConversationManager, Agent


def main():
    # TODO: Add websocket client for streaming UI and transcriptions.
    agent = Agent(
        model_name=LLM_MODEL, 
        tools=get_available_tools()
    )
    manager = ConversationManager(
        agent=agent,
        audio_manager=get_audio_manager(),
    )
    manager.run()

if __name__=="__main__":
    main()
    
    
# audio_manager = get_audio_manager()
# audio_manager.speak("Hi..., hello there I am a assistant")
# audio_manager.speak("Who is here to talk.")
# audio_manager.speak("About a KFC drive-way voice assistant.")
# audio_manager.speak("And as you guessed, its me.")
# audio_manager.wait_until_done()