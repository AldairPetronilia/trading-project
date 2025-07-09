class UnknownAreaCodeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown area code: {code}")
        self.code = code
