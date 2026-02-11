from pydantic import BaseModel, ConfigDict


class PlexGuid(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str


class PlexAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str


class PlexMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    librarySectionType: str
    type: str
    title: str
    grandparentTitle: str | None = None
    parentIndex: int | None = None
    index: int | None = None
    Guid: list[PlexGuid] | None = None


class PlexWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event: str
    Account: PlexAccount
    Metadata: PlexMetadata
