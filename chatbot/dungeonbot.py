import getpass
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

import pathlib
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
        self.state = "initial"
        self.inventory = set()
        self.visited = set()
        self.chat_history = []
        self.death_message = "You have met an untimely demise. Game over."
        self.last_image_path = None

        self.llm = ChatOpenAI(
            model="meta-llama-3.1-8b-instruct",
            temperature=0.5,
            openai_api_key=API_KEY,
            openai_api_base="https://chat-ai.academiccloud.de/v1",
        )
        self.chain = self.create_dungeon_chain()

    def create_dungeon_chain(self):
        prompt = PromptTemplate.from_template("""
You are a Dungeon Master guiding a player through a multi-room fantasy dungeon.

Your Main rule:
- Do NOT reveal exact puzzle solutions or give away the correct choices, even if asked directly.
- Only give vague, atmospheric hints or describe what the player sees, not solutions.
- The player must solve puzzles by exploring and experimenting, not by asking for answers.
- If a player tries to "guess" or asks for spoilers, respond with "You will have to discover that yourself."
- Never list all items or possibilities in a room, unless the player explicitly investigates.
- Let the player interact with objects one by one and reward careful actions, not random guesses.
- Player ist not alowed to skip rooms or puzzel or go directly to the end without solving the puzzles.
- Do not invent new objects or creatures. You must strictly stay within the described room structure and elements.

Example of good hint:
- "The riddle in the book is hard to understand at first glance. It mentions something about moonlight on silver."
- "When knowledge meets destiny, the unseen path may reveal itself."

Example of what NOT to do:
- Don't say "The answer is the silver dragon."
- Don't say "Use the book in the library to open the passage."     

Rules:
- Never solve puzzles or open paths automatically. Wait for the player to describe an action.
- Only perform an action if the player clearly describes it ("I use the key on the door", "I insert the crystal into the lock", etc).
- Simply having an item is not enough to trigger the next event.
- If the player does not describe a clear action, just describe the environment and wait for more input.
- suggest the player if he can go trough a door, if its open, but never say what is behind it.
- Never give away puzzle solutions.    
 - If the player writes "go" it means tey want to go trough the door to the next room, if they solved the puzzle of the room.                                     

Room & Game Info (for you only! Do NOT reveal to player):
- initial: two statues mounted on opposite walls: two dragon heads crafted from metal. one silver, one gold.
    The room also has a key and a book on a table inside the room.
     The book contains a riddle that hints towards which dragon head is the correct one. It is not required that the player has read it to insert the key in the silver dragon keyhole. 
    Touching the correct one (silver) shows a hidden door in the stone of the wall that is locked and needs to be unlocked with the key found in the room.  
        The door leads to the corridor and is the only way to leave the room. 
    if the player **inserts the key into the golden dragon**, they immediately **die by fire**.
                                              
- The Corridor connects to the initial room. It has three doors for the first room (Room 1), the second room (Room 2) and the third room (Room 3). The player always enters it after leaving the initial room. 
    The doors to each new room look the same and the player cannot tell what is behind them without entering.

- Room 1: (Library) has a mute skeleton NPC that gestures for silence and wears a crystal on a necklace that gives off a faint glow. 
    If the player **makes noise, shouts, yell or speaks loudly**, the skeleton **kills them immediately**.
    Placing the book from initial into an empty shelf opens a river passage. 
            The player can escape the dungeon by taking a boat on the underground river, but only if they have opened the river passage first.
    Taking the crystal deactivates the skeleton but is not related to the secret passage.

- Room 2: contains a deadly snake and some gold. 
    The Player have to decide what to do.
    Slowly reaching for the gold will succeeed, fighting the snake or making sudden movements will **die from venom**.

- Room 3:  has 3 pictures representing numbers. 
    A book nearby gives the order to input those numbers into a combination lock. 
    In each painting there is a number hidden, the player has to find them by looking at the pictures.
    The book with the order is relatet to the motiv of the pictures.
    The correct **combination 4-9-2** must be entered into a **vitrine/safe** to unlock a crystal.
    Either this crystal or the one from the library can be inserted into the door to escape.

- The underground river has a boat. Reaching it allows the player to escape via an alternate ending. The player can only reach the river through the secret passage in the library.
- The game ends when the player escapes through the door in Room 3 or by boat, or dies in a room.

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
        if self.state == "Death":
            return self.death_message, {
                "user_message": user_message,
                "response": self.death_message,
                "callback_logs": {}
            }
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
   
    # Bild anzeigen
    def display_image(self, image_name):
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, "images", image_name)
        self.last_image_path = image_path  # in Streamlit nutzbar
        return image_path
            

#Bilder für Sidebar
    def get_current_room_image(self):
        image_map = {
            "initial": "initial_room.png",
            "Room 1": "room2_bib.png",
            "Room 2": "room2_snake.png",
            "Room 3": "room3.png",
            "Corridor": "corridor.png",
            "Underground River": "river.png",
            "Escape": "exit.png",
            "Escape_Alt": "boat.png",
            "Death": "fire.png",
        }
        image_name = image_map.get(self.state, "default.png")
        return os.path.join("images", image_name)

    def update_state(self, user_message):
        msg = user_message.lower()

        if self.state == "initial":
            self.display_image("initial_room.png")
            if "key" in msg:
                self.inventory.add("key")
            if "book" in msg:
                self.inventory.add("book")
            if "dragon" in msg:
                if "gold" in msg:
                    self.state = "Death"
                    self.death_message = "As you insert the key into the golden dragon’s mouth, flames erupt and consume you."
                    #self.display_image("fire.png")
                    return
                elif "silver" in msg:
                    if "key" in self.inventory:
                       if "insert" in msg:
                        self.state = "Corridor"
                        self.visited.add("initial")

        elif self.state == "Corridor":
            if "room 1" in msg or "library" in msg or "first room" in msg:
                if "key" in self.inventory:
                    self.state = "Room 1"
                    self.visited.add("Room 1")
            elif "room 2" in msg or "snake" in msg:
                if "key" in self.inventory:
                    self.state = "Room 2"
                    self.visited.add("Room 3")
            elif "room 3" in msg or "hall" in msg:
                if "key" in self.inventory:
                    self.state = "Room 3"
                    self.visited.add("Room 3")

        elif self.state == "Room 1":
            self.display_image("room2_bib.png")
            if any(word in msg for word in ["shout", "yell", "loud", "scream", "noise"]):
                self.state = "Death"
                self.death_message = "Your voice echoes through the library. The skeleton reacts instantly, silencing you forever."
                print("[DEBUG] Death by noise triggered in Room 1")
                #self.display_image("Death by Skeleton")
                return
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

        elif self.state == "Room 2":
            if "snake" in msg:
                if "fight" in msg or "attack" in msg or "combat" in msg:
                    self.state = "Death"
                    self.death_message = "You attempt to battle the serpent, but it’s far too powerful. Its venom ends your journey."
                    #self.display_image("Death by Snake")
                elif "charge" in msg or "gold" in msg:
                    self.inventory.add("gold")

        elif self.state == "Room 3":
            self.display_image("room3.png")
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
            elif dm.state == "Death":
                end_msg = dm.death_message
            print("DM:", end_msg)
            break
