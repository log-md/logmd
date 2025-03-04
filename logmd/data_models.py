from pydantic import BaseModel, Field


class LogMDToken(BaseModel):
    token: str = Field(min_length=20, description="The token for the user")
    email: str = Field(
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="The email of the user",
    )
