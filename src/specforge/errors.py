class SpecForgeError(Exception):
    def __init__(self, code: str, artifact: str, path: str, message: str):
        self.code = code
        self.artifact = artifact
        self.path = path
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.code} {self.artifact}:{self.path}: {super().__str__()}"

