class UnknownObjectAggregationError(ValueError):
    def __init__(self, code: str):
        super().__init__(f"Unknown object aggregation: {code}")
        self.code = code
