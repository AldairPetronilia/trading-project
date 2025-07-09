class UnknownBusinessTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown business type code: {code}")
        self.code = code
