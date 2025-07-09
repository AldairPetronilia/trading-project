class UnknownContractMarketAgreementTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown contract market agreement type code: {code}")
        self.code = code
