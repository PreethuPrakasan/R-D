from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from ai_tools import ai_tools_service
from models import (
    CheckVehicleStatusRequest, BookAppointmentRequest, CheckAppointmentsRequest,
    CancelAppointmentRequest, GetServiceInfoRequest, UpdateCustomerInfoRequest,
    ToolCallRequest, ToolCallResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up FastAPI backend...")
    # Test database connection
    try:
        test_conn = db.get_connection()
        test_conn.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    yield
    # Shutdown
    logger.info("Shutting down FastAPI backend...")

app = FastAPI(
    title="Automotive AI Backend",
    description="Backend API for automotive customer service AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Automotive AI Backend is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "automotive-ai-backend"}

# AI Tools endpoints
@app.post("/ai-tools/check-vehicle-status", response_model=ToolCallResponse)
async def check_vehicle_status(request: CheckVehicleStatusRequest):
    """Check vehicle status and service history"""
    try:
        result = await ai_tools_service.check_vehicle_status(request)
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except Exception as e:
        logger.error(f"Error in check_vehicle_status endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/ai-tools/book-appointment", response_model=ToolCallResponse)
async def book_appointment(request: BookAppointmentRequest):
    """Book a new appointment"""
    try:
        result = await ai_tools_service.book_appointment(request)
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except Exception as e:
        logger.error(f"Error in book_appointment endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/ai-tools/check-appointments", response_model=ToolCallResponse)
async def check_appointments(request: CheckAppointmentsRequest):
    """Check existing appointments"""
    try:
        result = await ai_tools_service.check_appointments(request)
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except Exception as e:
        logger.error(f"Error in check_appointments endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/ai-tools/cancel-appointment", response_model=ToolCallResponse)
async def cancel_appointment(request: CancelAppointmentRequest):
    """Cancel an appointment"""
    try:
        result = await ai_tools_service.cancel_appointment(request)
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except Exception as e:
        logger.error(f"Error in cancel_appointment endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/ai-tools/get-service-info", response_model=ToolCallResponse)
async def get_service_info(request: GetServiceInfoRequest):
    """Get service information and pricing"""
    try:
        result = await ai_tools_service.get_service_info(request)
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except Exception as e:
        logger.error(f"Error in get_service_info endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/ai-tools/update-customer-info", response_model=ToolCallResponse)
async def update_customer_info(request: UpdateCustomerInfoRequest):
    """Update customer information"""
    try:
        result = await ai_tools_service.update_customer_info(request)
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except Exception as e:
        logger.error(f"Error in update_customer_info endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Generic tool call endpoint for the Node.js server
@app.post("/ai-tools/execute", response_model=ToolCallResponse)
def execute_tool_call(request: ToolCallRequest):
    """Execute any AI tool call"""
    try:
        tool_name = request.tool_name
        params = request.parameters
        
        if tool_name == "check_vehicle_status":
            req = CheckVehicleStatusRequest(**params)
            result = ai_tools_service.check_vehicle_status(req)
        elif tool_name == "book_appointment":
            req = BookAppointmentRequest(**params)
            result = ai_tools_service.book_appointment(req)
        elif tool_name == "check_appointments":
            req = CheckAppointmentsRequest(**params)
            result = ai_tools_service.check_appointments(req)
        elif tool_name == "cancel_appointment":
            req = CancelAppointmentRequest(**params)
            result = ai_tools_service.cancel_appointment(req)
        elif tool_name == "get_service_info":
            req = GetServiceInfoRequest(**params)
            result = ai_tools_service.get_service_info(req)
        elif tool_name == "update_customer_info":
            req = UpdateCustomerInfoRequest(**params)
            result = ai_tools_service.update_customer_info(req)
        else:
            return ToolCallResponse(
                success=False,
                message=f"Unknown tool: {tool_name}"
            )
        
        return ToolCallResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
        
    except Exception as e:
        logger.error(f"Error in execute_tool_call endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
