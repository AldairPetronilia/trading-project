class UnknownProcessTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown process type code: {code}")
        self.code = code
