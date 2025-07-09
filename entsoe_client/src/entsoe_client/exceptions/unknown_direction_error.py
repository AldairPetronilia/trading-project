class UnknownDirectionError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown direction code: {code}")
        self.code = code
