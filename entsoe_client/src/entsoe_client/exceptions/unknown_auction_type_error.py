class UnknownAuctionTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown auction type: {code}")
        self.code = code
