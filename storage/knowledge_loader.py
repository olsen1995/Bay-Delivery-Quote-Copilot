import json
from pathlib import Path
import pandas as pd

class KnowledgeLoader:
    def __init__(self, plugins_dir="plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.data = {}

    def load_all(self):
        for file in self.plugins_dir.glob("*.*"):
            if file.suffix.lower() == ".json":
                with open(file, "r", encoding="utf-8") as f:
                    self.data[file.stem] = json.load(f)
            elif file.suffix.lower() == ".csv":
                self.data[file.stem] = pd.read_csv(file)
            else:
                self.data[file.stem] = str(file.resolve())  # path to image or other files
        return self.data
