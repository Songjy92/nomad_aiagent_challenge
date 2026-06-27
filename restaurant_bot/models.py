from pydantic import BaseModel


class UserAccountContext(BaseModel):
    customer_id: int
    name: str
    tier: str = "basic"


class InputGuardRailOutput(BaseModel):
    is_off_topic: bool
    reason: str

class RestaurantOutputGuardRailOutput(BaseModel):
    contains_off_topic: bool
    contains_sensitive_data: bool
    contains_system_info: bool
    reason: str

class HandoffData(BaseModel):
    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str
