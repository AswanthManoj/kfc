import os
import random
import threading
import numpy as np
import pygame, httpx
from io import BytesIO
from dotenv import load_dotenv
import asyncio, requests, os, time
from llama_index.llms.groq import Groq
from llama_index.core.llms import ChatMessage
from typing import Tuple, List, BinaryIO, Dict
from deepgram import ( 
    DeepgramClient, DeepgramClientOptions, 
    LiveTranscriptionEvents, LiveOptions, Microphone 
)


SYSTEM_PROMPT = """Role: You are a KFC driveway food delivery voice assistant.
Instructions:
- Respond briefly in a clear and concise manner. 
- You do not give any long explanations or descriptions. 
"""


class TranscriptCollector:
    def __init__(self):
        self.reset()

    def reset(self):
        self.transcript_parts = []

    def add_part(self, part):
        self.transcript_parts.append(part)

    def get_full_transcript(self):
        return ' '.join(self.transcript_parts)

class SpeechToText:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.base_url = "https://api.deepgram.com/v1/listen/"
        
        self.params={"model": self.model_name, "smart_format": "false"}
        self.headers={"Content-Type": "audio/*", "Authorization": f"Token {self.api_key}"}
        
    async def transcribe(self, audio: BinaryIO):
        try:
            async with httpx.AsyncClient() as client:

                response = await client.post(
                    self.base_url,
                    params=self.params,
                    headers=self.headers,
                    content=audio.read(),
                )
                response.raise_for_status()
                transcript = response.json()
                return transcript['results']['channels'][0]['alternatives'][0]['transcript']

        except httpx.HTTPError as e:
            print(f"HTTP Error in transcribe_audio: {e}")
            return ""
        except Exception as e:
            print(f"Exception in transcribe_audio: {e}")
            return ""

    async def listen(self, callback):
        transcript_collector = TranscriptCollector()
        transcription_complete = asyncio.Event()
        
        try:
            deepgram: DeepgramClient = DeepgramClient(
                api_key=self.api_key, 
                config=DeepgramClientOptions(
                    api_key=self.api_key,
                    options={"keepalive": "true"}
                )
            )
            dg_connection = deepgram.listen.asynclive.v("1")
            print ("Listening...")
            
            async def on_message(cls, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                
                if not result.speech_final:
                    transcript_collector.add_part(sentence)
                else:
                                                                # This is the final part of the current sentence
                    transcript_collector.add_part(sentence)
                    full_sentence = transcript_collector.get_full_transcript()   
                    if len(full_sentence.strip()) > 0:          # Check if the full_sentence is not empty before printing
                        full_sentence = full_sentence.strip()
                        print(f"Human: {full_sentence}")
                        
                        callback(full_sentence)                 # Call the callback with the full_sentence
                        transcript_collector.reset()
                        transcription_complete.set()
            
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            await dg_connection.start(LiveOptions(
                channels=1,
                punctuate=True,
                endpointing=300,
                language="en-US",
                sample_rate=16000,
                smart_format=False,
                encoding="linear16",
                model=self.model_name,
            ))
            microphone = Microphone(dg_connection.send)         # Open a microphone stream on the default input device
            microphone.start()
            await transcription_complete.wait()
            microphone.finish()
            await dg_connection.finish()

        except Exception as e:
            print(f"Could not open socket: {e}")
            return

class TextToSpeech:
    def __init__(self, model_name: str, disfluencies_folder: str="disfluencies", initial_response_folder: str="responses/initial_responses") -> None:
        pygame.mixer.init()
        self.model_name = model_name
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.base_url = "https://api.deepgram.com/v1/speak"
        
        self.params={"model": model_name, "encoding": "mp3"}
        self.headers={"Content-Type": "application/json", "Authorization": f"Token {self.api_key}"}
        self.disfluencies = {
            # "uh": "uh.mp3",
            # "ahh": "ahh.mp3", 
            # "fine": "fine.mp3",
            # "got it...": "got_it.mp3", 
            "uh-huh...": "uh_huh.mp3", 
            "umm okay...": "um_ok.mp3",
            "uh ha um": "uh_ha_um.mp3", 
            "sure um...": "sure_um.mp3", 
            "... uh huh hm...": "uh_huh_hm.mp3",
        }
        self.initial_responses = {
            "Uh... Welcome to KFC and what can I get for you today?": "init_1.mp3", 
            "Hey there... um, welcome to KFC and how can I help you?": "init_2.mp3", 
            "Good day, welcome to KFC and what would you like to order?": "init_3.mp3", 
            "Hi... You've reached KFC, ready to place your order?": "init_4.mp3", 
            "Hello there! you have arrived at KFC, what are you craving?": "init_5.mp3", 
            "Uhm.. Hi... welcome to Kentucky Fried Chicken and are you ready to order something, or anything you prefer to have?": "init_6.mp3"
        }
        
        self.__load_intro__(initial_response_folder)
        self.__load_disfluencies__(disfluencies_folder)
    
    def __load_disfluencies__(self, folder: str):
        self.disfluency_sounds = {}
        for filler, filename in self.disfluencies.items():
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                self.disfluency_sounds[filler] = pygame.mixer.Sound(path)
            else:
                print(f"File {path} not found. Skipping {filler}.")

    def __load_intro__(self, folder: str):
        self.intro_sounds = {}
        for text, filename in self.initial_responses.items():
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                self.intro_sounds[text] = pygame.mixer.Sound(path)
            else:
                print(f"File {path} not found.")
        
    def play_disfluent_filler(self):
        if random.choice([True, True]):
            filler = random.choice(list(self.disfluency_sounds.keys()))
            sound = self.disfluency_sounds[filler]
            delay_seconds = 0.05
            def delayed_play_sound():
                time.sleep(delay_seconds)
                sound.play()
            thread = threading.Thread(target=delayed_play_sound)
            thread.start()
    
    def play_initial_response(self) -> str:
        choice = random.choice(list(self.intro_sounds.keys()))
        sound = self.intro_sounds[choice]
        sound.play()
        return choice
    
    async def generate(self, text: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={"text": text,},
                    params=self.params,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.content

        except httpx.HTTPError as e:
            print(f"HTTP Error in generate_speech_from_text: {e}")
            return None
        except Exception as e:
            print(f"Exception in generate_speech_from_text: {e}")
            return None
    
    def speak(self, text: str, return_response_time:bool=False) -> float|None:
        first_byte_time = None
        start_time = time.time()
        
        try:
            with requests.post(self.base_url, stream=True, json={"text": text,}, params=self.params, headers=self.headers) as r:
                chunks = []
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                            chunks.append(chunk)
                            if first_byte_time is None:
                                first_byte_time = time.time()
                                ttfb = int((first_byte_time - start_time) * 1000)
                                print(f"TTS Time to First Byte (TTFB): {ttfb}ms")
                
                audio_data = b''.join(chunks)
                audio_file = BytesIO(audio_data)
                sound = pygame.mixer.Sound(audio_file)
                channel = sound.play()
                audio_duration_ms = sound.get_length()
                time.sleep(audio_duration_ms / 1000)
            
            return ttfb if return_response_time else None

        except Exception as e:
            print(f"Exception in speak: {e}")
            return None
      
              
class LanguageModel:
    def __init__(self, model_name: str) -> None:
        self.model = Groq(
            max_tokens=1024,
            temperature=0.0,
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.messages = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
        
    def add_user_message(self, text:str) -> str:
        self.messages.append(ChatMessage(role="user", content=text))
    
    def add_assistant_message(self, text:str) -> str:
        self.messages.append(ChatMessage(role="assistant", content=text))
    
    async def generate(self, text:str, return_response_time:bool=False) -> str|Tuple[str, float]:
        self.add_user_message(text)
        
        start_time = time.time()
        response = await self.model.achat(self.messages)
        response = response.message.content
        end_time = time.time()
        
        self.add_assistant_message(response)
        elapsed_time = int((end_time - start_time) * 1000)
        print(f"LLM ({elapsed_time}ms): {response}")
        return response if not return_response_time else (response, elapsed_time)
    
class ConversationManager:
    def __init__(self, stt_model_id: str, llm_model_id: str, tts_model_id: str):
        self.transcription_response = ""
        self.tts = TextToSpeech(tts_model_id)
        self.stt = SpeechToText(stt_model_id)
        self.llm = LanguageModel(llm_model_id)
    
    def handle_full_sentence(self, full_sentence):
        self.transcription_response = full_sentence
    
    def reset(self):
        self.transcription_response = ""
    
    async def main(self):
        while True:
            if len(self.llm.messages)==1:
                self.llm.add_assistant_message(self.tts.play_initial_response())
            await self.stt.listen(self.handle_full_sentence)
            if "goodbye" in self.transcription_response.lower():
                break
            llm_response = await self.llm.generate(self.transcription_response)
            self.tts.speak(llm_response)
            self.reset()
    
    async def main2(self):
        while True:
            if len(self.llm.messages)==1:
                self.llm.add_assistant_message(self.tts.play_initial_response())
            query = input("Enter your query: ")
            if query:
                self.tts.play_disfluent_filler()
                response, llm_elapsed_time = await self.llm.generate(query, True)
                tts_elapsed_time = self.tts.speak(response, True)
                if tts_elapsed_time is not None and llm_elapsed_time is not None:
                    print("Total response time:", llm_elapsed_time+tts_elapsed_time, "ms\n")
        
    