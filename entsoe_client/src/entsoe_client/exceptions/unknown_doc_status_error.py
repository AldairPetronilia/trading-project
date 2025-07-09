class UnknownDocStatusError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown doc status code: {code}")
        self.code = code
