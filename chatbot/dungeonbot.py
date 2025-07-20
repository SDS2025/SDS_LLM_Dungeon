import getpass
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

import sys
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
API_KEY = os.getenv("CHAT_AI_ACCESS_KEY")
if not API_KEY:
    API_KEY = getpass.getpass("Enter your CHAT_AI_ACCESS_KEY: ")

class CustomCallback(BaseCallbackHandler):
    def __init__(self):
        self.messages = {}

    def on_llm_start(self, serialized, prompts, **kwargs):
        self.messages["on_llm_start_prompts"] = prompts
        self.messages["on_llm_start_kwargs"] = kwargs

    def on_llm_end(self, response: LLMResult, **kwargs):
        self.messages["on_llm_end_response"] = response
        self.messages["on_llm_end_kwargs"] = kwargs

class DungeonMaster:
    def __init__(self):
        self.state = "Room 1"
        self.inventory = set()
        self.visited = set()
        self.chat_history = []
        self.llm = ChatOpenAI(
            model="meta-llama-3.1-8b-instruct",
            temperature=0.7,
            openai_api_key=API_KEY,
            openai_api_base="https://chat-ai.academiccloud.de/v1",
        )
        self.chain = self.create_dungeon_chain()

    def create_dungeon_chain(self):
        prompt = PromptTemplate.from_template("""
You are a Dungeon Master guiding a player through a multi-room fantasy dungeon.
Use vivid, immersive narration. Use the current room, inventory, and player choices to advance the story.
Do NOT let the player skip any puzzle or challenges along the way. Do not let the player cheat.
Do NOT reveal too much information immediately. The player is supposed to find the information by exploring the rooms and solving puzzles, not by the narration alone.

Room Highlights:
- Room 1 has two metal dragon heads (statues) mounted on opposite walls: one silver, one gold. The room also has a key and a book. The book contains a riddle that hints towards which dragon head is the correct one. 
    Touching the correct one (silver) opens the hidden path which is a hidden door in the stone of the wall that needs to be unlocked with the key found in the room. The door leads to the corridor and is the only way to leave the room.
- The Corridor connects to Room 2 (Library), Room 3 (Snake), and Room 4 (Hall). The player enters it after leaving the first room. The doors to each room look the same and the player cannot tell what is behind them without entering. 
    DO not reveal any information about what is inside the rooms before the player enters them.
- Room 2 (Library) has a mute skeleton NPC that gestures for silence and wears a crystal on a necklace that gives off a faint glow. Making noise results in death by the skeleton. Placing the book from Room 1 into an empty shelf opens a river passage that the player can enter. 
    Taking the crystal deactivates the skeleton but is not related to the secret passage.
- Room 3 contains a deadly snake and some gold. Slowly reaching for the gold will succeeed, fighting the snake or making sudden movements will result in death.
- Room 4 (Hall) has 4 pictures representing numbers. A book nearby gives the order to input those numbers into a combination lock. Solving it yields a crystal. Either this crystal or the one from the library can be inserted into the door to escape.
- The underground river has a hidden boat. Reaching it allows the player to escape via an alternate ending.

State:
- Current Room: {state}
- Inventory: {inventory}
- Visited Rooms: {visited}

Conversation so far:
{chat_history}

Player: {user_message}
DM:""")
        return prompt | self.llm | StrOutputParser()

    def get_response(self, user_message, chat_history):
        self.update_state(user_message)
        callback = CustomCallback()
        response = self.chain.invoke(
            {
                "state": self.state,
                "inventory": ", ".join(sorted(self.inventory)),
                "visited": ", ".join(sorted(self.visited)),
                "user_message": user_message,
                "chat_history": "\n".join(chat_history),
            },
            {"callbacks": [callback], "stop_sequences": ["\n"]},
        )
        log = {
            "user_message": user_message,
            "response": response,
            "callback_logs": callback.messages
        }
        return response, log

    def update_state(self, user_message):
        msg = user_message.lower()

        if self.state == "Room 1":
            if "key" in msg:
                self.inventory.add("key")
            if "book" in msg:
                self.inventory.add("book")
            if "dragon" in msg:
                if "silver" in msg:
                    if "key" in self.inventory:
                        self.state = "Corridor"
                        self.visited.add("Room 1")
                elif "gold" in msg:
                    self.state = "Death"

        elif self.state == "Corridor":
            if "room 2" in msg or "library" in msg:
                if "key" in self.inventory:
                    self.state = "Room 2"
                    self.visited.add("Room 2")
            elif "room 3" in msg or "snake" in msg:
                if "key" in self.inventory:
                    self.state = "Room 3"
                    self.visited.add("Room 3")
            elif "room 4" in msg or "hall" in msg:
                if "key" in self.inventory:
                    self.state = "Room 4"
                    self.visited.add("Room 4")

        elif self.state == "Room 2":
            if "loud" in msg or "shout" in msg or "yell" in msg:
                self.state = "Death"
            if "shelf" in msg and "book" in self.inventory:
                self.inventory.add("river passage open")
            if "crystal" in msg:
                self.inventory.add("library crystal")
                self.inventory.add("skeleton deactivated")
            if "river" in msg and "river passage open" in self.inventory:
                self.state = "Underground River"
                self.visited.add("Underground River")

        elif self.state == "Underground River":
            if "boat" in msg or "escape" in msg or "freedom" in msg:
                self.state = "Escape_Alt"

        elif self.state == "Room 3":
            if "snake" in msg:
                if "charge" in msg or "life" in msg:
                    self.inventory.add("life orb")
                else:
                    self.state = "Death"

        elif self.state == "Room 4":
            if "pictures" in msg or "wall" in msg:
                self.inventory.add("saw pictures")
            if "book" in msg and ("order" in msg or "hint" in msg):
                self.inventory.add("saw order hint")
            if (
                "safe" in msg or "lock" in msg or "combination" in msg
            ) and "saw pictures" in self.inventory and "saw order hint" in self.inventory:
                self.inventory.add("hall crystal")
            if "crystal" in msg and ("hall crystal" in self.inventory or "library crystal" in self.inventory):
                self.state = "Escape"

    def is_game_over(self):
        return self.state in ["Death", "Escape", "Escape_Alt"]

if __name__ == "__main__":
    dm = DungeonMaster()
    print("Welcome to the Dungeon. Type 'quit' to exit.")

    while True:
        user_message = input("You: ")
        if user_message.strip().lower() in ["quit", "exit", "bye"]:
            print("DM: May your journey continue in other realms...")
            break

        response, log = dm.get_response(user_message, dm.chat_history)
        print("DM:", response)
        dm.chat_history.append(f"Player: {user_message}")
        dm.chat_history.append(f"DM: {response}")

        if dm.is_game_over():
            if dm.state == "Escape":
                end_msg = "You have escaped through the magic door. Victory!"
            elif dm.state == "Escape_Alt":
                end_msg = "You quietly drift away on the boat, free at last. An alternate ending!"
            else:
                end_msg = "You died in the dungeon..."
            print("DM:", end_msg)
            break
