class MemoryMode:
    def handle(self, message, state):
        return {"response": f"Memory mode managing memory for: {message}"}