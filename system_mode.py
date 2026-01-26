class SystemMode:
    def handle(self, message, state):
        return {"response": f"System mode status for: {message}"}