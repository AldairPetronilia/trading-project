class UnknownAuctionCategoryError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown auction category: {code}")
        self.code = code
