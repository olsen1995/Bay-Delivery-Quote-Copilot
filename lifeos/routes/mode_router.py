from lifeos.prompt_mode import PromptMode
from lifeos.memory_mode import MemoryMode
from lifeos.notes_mode import NotesMode
from lifeos.multi_mode import MultiMode
from lifeos.debug_mode import DebugMode
from lifeos.system_mode import SystemMode
from lifeos.api_key_mode import ApiKeyMode
from lifeos.feedback_mode import FeedbackMode

class ModeRouter:
    def __init__(self):
        self.modes = {
            "prompt": PromptMode(),
            "memory": MemoryMode(),
            "notes": NotesMode(),
            "multi": MultiMode(),
            "debug": DebugMode(),
            "system": SystemMode(),
            "apikey": ApiKeyMode(),
            "feedback": FeedbackMode(),
        }

    def route(self, user_message, state):
        """
        Decide the BEST matching mode from the following list, based on the input:
        - prompt: General questions or AI tasks
        - memory: Remembered facts, lookups, clearing memory
        - notes: Writing or managing notes
        - multi: Task juggling or productivity
        - debug: Debug info or dev tools
        - system: Internal status or system logs
        - apikey: Manage or view API keys
        - feedback: Collecting user feedback or bug reports
        """
        best_mode = "prompt"

        if "remember" in user_message or "recall" in user_message:
            best_mode = "memory"
        elif "note" in user_message:
            best_mode = "notes"
        elif "multiple" in user_message or "juggle" in user_message:
            best_mode = "multi"
        elif "debug" in user_message or "error" in user_message:
            best_mode = "debug"
        elif "system" in user_message or "status" in user_message:
            best_mode = "system"
        elif "api key" in user_message or "usage" in user_message:
            best_mode = "apikey"
        elif "feedback" in user_message or "report" in user_message:
            best_mode = "feedback"

        return self.modes[best_mode]