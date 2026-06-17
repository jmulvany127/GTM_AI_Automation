from datetime import datetime
from pydantic import BaseModel


class CrmSyncLogRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    crm_system: str
    sync_status: str
    external_contact_id: str | None
    error_message: str | None
    created_at: datetime
