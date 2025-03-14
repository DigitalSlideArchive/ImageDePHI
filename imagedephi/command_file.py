from pydantic import BaseModel


# The only two required fields are command and input_paths
class CommandFile(BaseModel):
    command: str
    input_paths: list[str]
