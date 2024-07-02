import os
import pygame
import random
import threading


fillers = {
    "Ah...": "ah.mp3",
    "Oh...": "oh.mp3",
    "Hmm...": "hmm.mp3",
    "Okay...": "ok.mp3",
    "Sure...": "sure.mp3",
    "Got it...": "got_it.mp3",
    "Uh-huh...": "uh_huh.mp3",
}

pygame.mixer.init()

def load_fillers(folder: str) -> dict:
    sounds = {}
    for filler, filename in fillers.items():
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            sounds[filler] = pygame.mixer.Sound(path)
        else:
            print(f"File {filename} not found. Skipping {filler}.")
    return sounds

def play_filler(sounds: dict):
    if random.choice([True, False]):
        filler = random.choice(list(sounds.keys()))
        sound = sounds[filler]
        thread = threading.Thread(target=sound.play)
        thread.start()

sounds = load_fillers("fillers")

while True:
    q = input("Enter:")
    print("start")
    play_filler(sounds)
    print("end")