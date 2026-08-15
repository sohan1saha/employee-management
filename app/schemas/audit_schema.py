from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: str
    action: str
    target_entity: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    client_ip: str
    timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
