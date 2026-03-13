from typing import Dict, Any, Optional
from datetime import datetime, date, time
import logging
from database_adapter import db
from models import (
    CheckVehicleStatusRequest, BookAppointmentRequest, CheckAppointmentsRequest,
    CancelAppointmentRequest, GetServiceInfoRequest, UpdateCustomerInfoRequest
)

logger = logging.getLogger(__name__)

class AIToolsService:
    def __init__(self):
        pass
    
    def check_vehicle_status(self, request: CheckVehicleStatusRequest) -> Dict[str, Any]:
        """Check vehicle status and service history for a customer"""
        try:
            customer = db.get_customer_by_phone(request.customer_phone)
            if not customer:
                return {
                    "success": False,
                    "message": "I couldn't find a customer with that phone number. Please check the number and try again."
                }
            
            vehicles = db.get_vehicles_by_customer(customer['id'])
            if not vehicles:
                return {
                    "success": True,
                    "message": f"Hi {customer.get('first_name', 'Customer')}! I don't see any vehicles registered under your account. Would you like to add a vehicle or book a service?"
                }
            
            message = f"Hi {customer.get('first_name', 'Customer')}! Here's the status of your vehicles:\n\n"
            
            for vehicle in vehicles:
                message += f"🚗 {vehicle['year']} {vehicle['make']} {vehicle['model']}\n"
                message += f"Status: ✅ Ready for service\n"
                if vehicle.get('vin'):
                    message += f"VIN: {vehicle['vin']}\n"
                if vehicle.get('mileage'):
                    message += f"Mileage: {vehicle['mileage']:,} miles\n"
                message += "\n"
            
            return {
                "success": True,
                "message": message,
                "data": {"customer": customer, "vehicles": vehicles}
            }
            
        except Exception as e:
            logger.error(f"Error in check_vehicle_status: {e}")
            return {
                "success": False,
                "message": "Sorry, I encountered an error checking your vehicle status. Please try again."
            }
    
    def book_appointment(self, request: BookAppointmentRequest) -> Dict[str, Any]:
        """Book a new appointment for vehicle service"""
        try:
            # Get or create customer
            customer = db.get_customer_by_phone(request.customer_phone)
            if not customer:
                # Extract name from vehicle_info or use a default
                name = request.vehicle_info.split(' ')[0] if request.vehicle_info else 'Customer'
                customer = db.create_customer(request.customer_phone, name)
            
            # Find matching service
            service = db.get_service_by_name(request.service_name)
            if not service:
                services = db.get_services()
                available_services = [s['name'] for s in services]
                return {
                    "success": False,
                    "message": f"I couldn't find a service called '{request.service_name}'. Available services are: {', '.join(available_services)}. Please specify which service you'd like."
                }
            
            # Parse appointment date and time
            try:
                appointment_date = datetime.strptime(request.preferred_date, "%Y-%m-%d")
                if request.preferred_time:
                    time_obj = datetime.strptime(request.preferred_time, "%H:%M").time()
                    appointment_date = appointment_date.replace(hour=time_obj.hour, minute=time_obj.minute)
                else:
                    appointment_date = appointment_date.replace(hour=9, minute=0)  # Default to 9 AM
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time."
                }
            
            # Check availability
            is_available = db.check_availability(service['name'], appointment_date.date())
            if not is_available:
                return {
                    "success": False,
                    "message": f"I'm sorry, but {request.preferred_date} is fully booked for {service['name']}. Would you like to try a different date? I can check availability for you."
                }
            
            # Parse vehicle info and find or create vehicle
            vehicle_parts = request.vehicle_info.split()
            if len(vehicle_parts) < 3:
                return {
                    "success": False,
                    "message": "I need the make, model, and year of your vehicle. For example: 'Toyota Camry 2020'"
                }
            
            make = vehicle_parts[0]
            model = vehicle_parts[1]
            try:
                year = int(vehicle_parts[2])
            except ValueError:
                return {
                    "success": False,
                    "message": "Please provide a valid year for your vehicle."
                }
            
            vehicle = db.find_or_create_vehicle(customer['id'], make, model, year)
            
            # Create the appointment
            appointment = db.create_appointment(
                customer['id'],
                vehicle['id'],
                service['name'],
                appointment_date,
                request.notes
            )
            
            formatted_date = appointment_date.strftime("%B %d, %Y")
            formatted_time = appointment_date.strftime("%I:%M %p")
            
            return {
                "success": True,
                "message": f"Perfect! I've booked your {service['name']} appointment for {formatted_date} at {formatted_time}. Your appointment ID is {appointment['id']}. Is there anything else I can help you with?",
                "data": {
                    "appointment": appointment,
                    "service": service,
                    "vehicle": vehicle
                }
            }
            
        except Exception as e:
            logger.error(f"Error in book_appointment: {e}")
            return {
                "success": False,
                "message": "Sorry, I encountered an error booking your appointment. Please try again."
            }
    
    def check_appointments(self, request: CheckAppointmentsRequest) -> Dict[str, Any]:
        """Check existing appointments for a customer"""
        try:
            customer = db.get_customer_by_phone(request.customer_phone)
            if not customer:
                return {
                    "success": False,
                    "message": "I couldn't find a customer with that phone number. Please check the number and try again."
                }
            
            appointments = db.get_upcoming_appointments(customer['id'])
            
            if not appointments:
                return {
                    "success": True,
                    "message": f"Hi {customer.get('first_name', 'Customer')}! You don't have any upcoming appointments scheduled. Would you like to book a service?"
                }
            
            message = f"Hi {customer.get('first_name', 'Customer')}! Here are your upcoming appointments:\n\n"
            
            for appointment in appointments:
                appointment_date = appointment['appointment_date']
                formatted_date = appointment_date.strftime("%B %d, %Y")
                formatted_time = appointment_date.strftime("%I:%M %p")
                
                message += f"📅 {appointment['service_name']}\n"
                message += f"Date: {formatted_date}\n"
                message += f"Time: {formatted_time}\n"
                message += f"Vehicle: {appointment['vehicle_year']} {appointment['vehicle_make']} {appointment['vehicle_model']}\n"
                message += f"Status: {appointment['status']}\n"
                if appointment['notes']:
                    message += f"Notes: {appointment['notes']}\n"
                message += "\n"
            
            return {
                "success": True,
                "message": message,
                "data": {"customer": customer, "appointments": appointments}
            }
            
        except Exception as e:
            logger.error(f"Error in check_appointments: {e}")
            return {
                "success": False,
                "message": "Sorry, I encountered an error checking your appointments. Please try again."
            }
    
    def cancel_appointment(self, request: CancelAppointmentRequest) -> Dict[str, Any]:
        """Cancel an existing appointment"""
        try:
            customer = db.get_customer_by_phone(request.customer_phone)
            if not customer:
                return {
                    "success": False,
                    "message": "I couldn't find a customer with that phone number. Please check the number and try again."
                }
            
            try:
                appointment_id = int(request.appointment_id)
                appointment = db.cancel_appointment(appointment_id)
                
                return {
                    "success": True,
                    "message": f"I've successfully cancelled your appointment (ID: {appointment_id}). Is there anything else I can help you with?",
                    "data": {"appointment": appointment}
                }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid appointment ID. Please provide a valid appointment number."
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": "I couldn't find that appointment to cancel. Please check the appointment ID and try again."
                }
                
        except Exception as e:
            logger.error(f"Error in cancel_appointment: {e}")
            return {
                "success": False,
                "message": "Sorry, I encountered an error cancelling your appointment. Please try again."
            }
    
    def get_service_info(self, request: GetServiceInfoRequest) -> Dict[str, Any]:
        """Get information about available services and pricing"""
        try:
            if request.service_name:
                service = db.get_service_by_name(request.service_name)
                if not service:
                    return {
                        "success": False,
                        "message": f"I couldn't find information about '{request.service_name}'. Please ask about our available services."
                    }
                
                message = f"Here's information about {service['name']}:\n\n"
                message += f"{service['description']}\n\n"
                duration = service.get('estimated_duration', service.get('duration_minutes', service.get('duration', 'N/A')))
                price = service.get('base_price', service.get('price', 'Contact for pricing'))
                message += f"Duration: {duration} minutes\n"
                message += f"Price: ${price}\n\n"
                message += "Would you like to book this service?"
                
                return {
                    "success": True,
                    "message": message,
                    "data": {"service": service}
                }
            else:
                services = db.get_services()
                message = "Here are our available services:\n\n"
                
                for service in services:
                    message += f"🔧 {service['name']}\n"
                    message += f"{service['description']}\n"
                    duration = service.get('estimated_duration', service.get('duration_minutes', service.get('duration', 'N/A')))
                    price = service.get('base_price', service.get('price', 'Contact for pricing'))
                    message += f"Duration: {duration} minutes | Price: ${price}\n\n"
                
                return {
                    "success": True,
                    "message": message,
                    "data": {"services": services}
                }
                
        except Exception as e:
            logger.error(f"Error in get_service_info: {e}")
            return {
                "success": False,
                "message": "Sorry, I encountered an error getting service information. Please try again."
            }
    
    def update_customer_info(self, request: UpdateCustomerInfoRequest) -> Dict[str, Any]:
        """Update customer contact information"""
        try:
            customer = db.get_customer_by_phone(request.customer_phone)
            if not customer:
                return {
                    "success": False,
                    "message": "I couldn't find a customer with that phone number. Please check the number and try again."
                }
            
            updates = {}
            if request.name:
                updates['name'] = request.name
            if request.email:
                updates['email'] = request.email
            
            if not updates:
                return {
                    "success": False,
                    "message": "Please provide the information you'd like to update (name or email)."
                }
            
            updated_customer = db.update_customer(customer['id'], **updates)
            
            return {
                "success": True,
                "message": "I've updated your information successfully. Is there anything else I can help you with?",
                "data": {"customer": updated_customer}
            }
            
        except Exception as e:
            logger.error(f"Error in update_customer_info: {e}")
            return {
                "success": False,
                "message": "Sorry, I encountered an error updating your information. Please try again."
            }

# Global AI tools service instance
ai_tools_service = AIToolsService()
