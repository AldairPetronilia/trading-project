class UnknownDocumentTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown document type code: {code}")
        self.code = code
