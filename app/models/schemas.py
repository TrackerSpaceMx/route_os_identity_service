from pydantic import BaseModel,Field,model_validator
from typing import Optional,Literal
from enum import Enum
from datetime import datetime
from uuid import UUID

class Users(BaseModel):
    name: str = Field(max_length=100)
    username : str = Field(max_length=50)
    email : str = Field(max_length=255)
    phone : str  = Field(max_length=20)
    password_hash : str = Field(max_length=255)
    recovery_email : str = Field(max_length=255)
    role: str   = Field(max_length=20)
    send_invitation : Optional[bool] = False
    clients_information : list[dict]


class UserAuthentication(BaseModel):
    username: str =  Field(max_length=50)
    password: str

class UpdateUser(BaseModel):
    name : Optional[str] = None
    username : Optional[str] = None
    email : Optional[str] = None
    phone : Optional[str] = None
    password_hash : Optional[str] = None
    recovery_email : Optional[str] = None
    status : Optional[int] = None
    clients_information: Optional[list[dict]] = None


class RecoveryPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    token: str
    new_password: str


class Account(BaseModel):
    slug:str
    name: str
    api_key:str
    secret_key: str
    rfc: str
    address: str
    company_name:str


class PointsOfInterest(BaseModel):
    point_name :str
    category : str
    latidude : str
    longitude : str
    radius_meter : int

class RoutesCreation(BaseModel):
    route_name : str
    points : list[dict]
    client_id : int
    client_name : str
    starting_location: str



class Drivers(BaseModel):
    name:str
    employee_number: str
    phone:str
    phone_secondary:str
    license_number: str
    license_expiry: datetime
    photo_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=500)

class UpdateDriver(BaseModel):
    name: Optional[str] = None
    employee_number: Optional[str] = None
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[str] = None
    notes: Optional[str] = None
    photo_id: Optional[UUID] = None
    remove_photo: bool = False

class TripStop(BaseModel):
    waypoint_id: str
    sequence_order: int
    dwell_time: Optional[int] = None
    expected_arrival: Optional[datetime] = None

class CreateTrip(BaseModel):
    route_id: str
    driver_id : str
    vehicle_name : str
    vehicle_plate : str
    protocol_profile_id : str
    driver_phone : str
    folio : str
    stops : list[TripStop]
    scheduled_departure : datetime


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ThresholdUnit(str, Enum):
    seconds = "seconds"
    minutes = "minutes"
    km = "km"
    hour = "hour"
    count = "count"


class RuleType(str, Enum):
    panic = "panic"
    battery_disconnected = "battery_disconnected"
    jammer_detected = "jammer_detected"
    risk_zone = "risk_zone"
    signal_loss = "signal_loss"
    route_deviation = "route_deviation"
    restricted_stop = "restricted_stop"
    authorized_stop = "authorized_stop"
    restricted_hours = "restricted_hours"
    unload_dwell = "unload_dwell"
    rest_dwell = "rest_dwell"
    suspicious_call = "suspicious_call"


class ActionType(str, Enum):
    call_operator = "call_operator"
    send_email = "send_email"
    engine_stop = "engine_stop"


class RuleAction(BaseModel):
    action_type: ActionType
    delay_minutes: int = Field(0, ge=0)
    escalate: bool = False
    config: Optional[dict] = None


class ProtocolRule(BaseModel):
    rule_type: RuleType
    is_enabled: bool = True
    severity: Severity
    risk_impact: int = Field(..., ge=0, le=100)
    threshold_value: Optional[int] = Field(None, ge=0)
    threshold_unit: Optional[ThresholdUnit] = None
    params: Optional[dict] = None
    actions: list[RuleAction] = []


class ProtocolProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = False
    rules: list[ProtocolRule] = []

    @model_validator(mode="after")
    def no_duplicate_rule_types(self):
        types = [r.rule_type for r in self.rules]
        if len(types) != len(set(types)):
            raise ValueError("rule_type repeated in rules")
        return self

class StartTrip(BaseModel):
    trip_status : Literal["in_progress", "completed", "cancelled"]