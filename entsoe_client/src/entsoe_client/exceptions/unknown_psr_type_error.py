class UnknownPsrTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown PsrType code: {code}")
        self.code = code
