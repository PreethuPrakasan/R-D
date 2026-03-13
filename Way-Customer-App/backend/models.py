from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time

class CustomerBase(BaseModel):
    phone: str
    name: str
    email: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

class Customer(CustomerBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VehicleBase(BaseModel):
    make: str
    model: str
    year: int
    vin: Optional[str] = None

class VehicleCreate(VehicleBase):
    customer_id: int

class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    status: Optional[str] = None

class Vehicle(VehicleBase):
    id: int
    customer_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: float

class ServiceCreate(ServiceBase):
    pass

class Service(ServiceBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class AppointmentBase(BaseModel):
    customer_id: int
    vehicle_id: int
    service_id: int
    appointment_date: datetime
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class Appointment(AppointmentBase):
    id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AppointmentWithDetails(Appointment):
    service_name: str
    service_duration: int
    service_price: float
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int

# AI Tool Request/Response Models
class ToolCallRequest(BaseModel):
    tool_name: str
    parameters: dict

class ToolCallResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Specific tool request models
class CheckVehicleStatusRequest(BaseModel):
    customer_phone: str

class BookAppointmentRequest(BaseModel):
    customer_phone: str
    service_name: str
    preferred_date: str  # YYYY-MM-DD format
    preferred_time: Optional[str] = None  # HH:MM format
    vehicle_info: str  # "Make Model Year"
    notes: Optional[str] = None

class CheckAppointmentsRequest(BaseModel):
    customer_phone: str

class CancelAppointmentRequest(BaseModel):
    customer_phone: str
    appointment_id: str

class GetServiceInfoRequest(BaseModel):
    service_name: Optional[str] = None

class UpdateCustomerInfoRequest(BaseModel):
    customer_phone: str
    name: Optional[str] = None
    email: Optional[str] = None
