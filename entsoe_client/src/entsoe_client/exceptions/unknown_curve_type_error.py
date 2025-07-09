class UnknownCurveTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown curve type code: {code}")
        self.code = code
