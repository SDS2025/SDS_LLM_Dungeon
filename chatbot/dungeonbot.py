import getpass
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

# Silence warnings
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
        self.llm = ChatOpenAI(
            model="meta-llama-3.1-8b-instruct",
            temperature=0.7,
            openai_api_key=API_KEY,
            openai_api_base="https://chat-ai.academiccloud.de/v1",
        )
        self.chain = self.create_dungeon_chain()

    def create_dungeon_chain(self):
        prompt = PromptTemplate.from_template("""
You are a Dungeon Master narrating a dark fantasy escape room experience to the player. The player has just woken up in a cell. Describe the scene vividly, but do not reveal all secrets. Let the player interact.

Room description:
The adventurer awakens in a cold, damp stone cell. There's a small wooden table. On the table: a dusty leather-bound book and an old iron key. Mounted on opposite stone walls are two dragon head statues—one gold, one silver. Unknown to the player, the exit is hidden in the stone and only reveals itself when the correct dragon head is activated.

The book contains a riddle or clue hinting at which dragon is correct. Touching the correct head opens the hidden door. Touching the wrong one results in instant death.

Respond in immersive narration, then allow the player to act. Respond to player input like a D&D dungeon master would, updating the world accordingly.

Conversation so far:
{chat_history}

Player: {user_message}
DM:""")
        return prompt | self.llm | StrOutputParser()

    def get_response(self, user_message, chat_history):
        callback = CustomCallback()
        response = self.chain.invoke(
            {"user_message": user_message, "chat_history": "\n".join(chat_history)},
            {"callbacks": [callback], "stop_sequences": ["\n"]},
        )
        log = {
            "user_message": user_message,
            "response": response,
            "callback_logs": callback.messages
        }
        return response, log

if __name__ == "__main__":
    dm = DungeonMaster()
    chat_history = []
    print("Welcome to the Dungeon. Type 'quit' to exit.")

    while True:
        user_message = input("You: ")
        if user_message.strip().lower() in ["quit", "exit", "bye"]:
            print("DM: May your journey continue in other realms...")
            break

        response, log = dm.get_response(user_message, chat_history)
        print("DM:", response)
        chat_history.append(f"Player: {user_message}")
        chat_history.append(f"DM: {response}")
