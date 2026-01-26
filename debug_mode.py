class DebugMode:
    def handle(self, message, state):
        return {"response": f"Debugging info: {message}"}