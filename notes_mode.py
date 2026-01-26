class NotesMode:
    def handle(self, message, state):
        return {"response": f"Notes mode writing note: {message}"}