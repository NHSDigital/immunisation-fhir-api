def load_string(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
