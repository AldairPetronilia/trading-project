class UnknownMarketRoleTypeError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Unknown market role type code: {code}")
        self.code = code
