from pydantic import BaseModel, Field


class DigestUnsubscribeIn(BaseModel):
    token: str = Field(min_length=10)
