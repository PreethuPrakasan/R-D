import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        # Mock data for testing
        self.customers = [
            {
                'id': 1,
                'phone': '+1234567890',
                'name': 'John Doe',
                'email': 'john.doe@email.com',
                'created_at': datetime.now()
            }
        ]
        
        self.vehicles = [
            {
                'id': 1,
                'customer_id': 1,
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2020,
                'vin': '1HGBH41JXMN109186',
                'status': 'active',
                'created_at': datetime.now()
            },
            {
                'id': 2,
                'customer_id': 1,
                'make': 'Honda',
                'model': 'Civic',
                'year': 2018,
                'vin': '2HGBH41JXMN109187',
                'status': 'active',
                'created_at': datetime.now()
            }
        ]
        
        self.services = [
            {
                'id': 1,
                'name': 'Oil Change',
                'description': 'Complete oil change service with filter replacement',
                'duration_minutes': 30,
                'price': 49.99,
                'is_active': True,
                'created_at': datetime.now()
            },
            {
                'id': 2,
                'name': 'Brake Inspection',
                'description': 'Comprehensive brake system inspection and adjustment',
                'duration_minutes': 45,
                'price': 79.99,
                'is_active': True,
                'created_at': datetime.now()
            },
            {
                'id': 3,
                'name': 'Tire Rotation',
                'description': 'Rotate tires and check tire pressure',
                'duration_minutes': 20,
                'price': 29.99,
                'is_active': True,
                'created_at': datetime.now()
            },
            {
                'id': 4,
                'name': 'Engine Diagnostic',
                'description': 'Complete engine diagnostic scan and analysis',
                'duration_minutes': 60,
                'price': 99.99,
                'is_active': True,
                'created_at': datetime.now()
            }
        ]
        
        self.appointments = [
            {
                'id': 1,
                'customer_id': 1,
                'vehicle_id': 1,
                'service_id': 1,
                'appointment_date': datetime.now().replace(hour=10, minute=0),
                'status': 'scheduled',
                'notes': 'Regular maintenance',
                'created_at': datetime.now()
            }
        ]
    
    def get_connection(self):
        """Mock connection for compatibility"""
        return self
    
    # Customer operations
    def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get customer by phone number"""
        for customer in self.customers:
            if customer['phone'] == phone:
                return customer
        return None
    
    def create_customer(self, phone: str, name: str, email: str = None) -> Dict[str, Any]:
        """Create a new customer"""
        new_customer = {
            'id': len(self.customers) + 1,
            'phone': phone,
            'name': name,
            'email': email,
            'created_at': datetime.now()
        }
        self.customers.append(new_customer)
        return new_customer
    
    def update_customer(self, customer_id: int, **updates) -> Dict[str, Any]:
        """Update customer information"""
        for i, customer in enumerate(self.customers):
            if customer['id'] == customer_id:
                for key, value in updates.items():
                    customer[key] = value
                return customer
        return None
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        for customer in self.customers:
            if customer['id'] == customer_id:
                return customer
        return None
    
    # Vehicle operations
    def get_vehicles_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all vehicles for a customer"""
        return [v for v in self.vehicles if v['customer_id'] == customer_id]
    
    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """Get vehicle by ID"""
        for vehicle in self.vehicles:
            if vehicle['id'] == vehicle_id:
                return vehicle
        return None
    
    def create_vehicle(self, customer_id: int, make: str, model: str, year: int, vin: str = None) -> Dict[str, Any]:
        """Create a new vehicle"""
        new_vehicle = {
            'id': len(self.vehicles) + 1,
            'customer_id': customer_id,
            'make': make,
            'model': model,
            'year': year,
            'vin': vin,
            'status': 'active',
            'created_at': datetime.now()
        }
        self.vehicles.append(new_vehicle)
        return new_vehicle
    
    def update_vehicle_status(self, vehicle_id: int, status: str) -> Dict[str, Any]:
        """Update vehicle status"""
        for i, vehicle in enumerate(self.vehicles):
            if vehicle['id'] == vehicle_id:
                vehicle['status'] = status
                return vehicle
        return None
    
    # Service operations
    def get_services(self) -> List[Dict[str, Any]]:
        """Get all active services"""
        return [s for s in self.services if s['is_active']]
    
    def get_service_by_id(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get service by ID"""
        for service in self.services:
            if service['id'] == service_id and service['is_active']:
                return service
        return None
    
    def get_service_by_name(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service by name (fuzzy matching)"""
        for service in self.services:
            if service['is_active'] and service_name.lower() in service['name'].lower():
                return service
        return None
    
    # Appointment operations
    def get_appointments_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all appointments for a customer with service and vehicle details"""
        appointments_with_details = []
        for appointment in self.appointments:
            if appointment['customer_id'] == customer_id:
                service = self.get_service_by_id(appointment['service_id'])
                vehicle = self.get_vehicle_by_id(appointment['vehicle_id'])
                
                appointment_detail = appointment.copy()
                appointment_detail['service_name'] = service['name']
                appointment_detail['service_duration'] = service['duration_minutes']
                appointment_detail['service_price'] = service['price']
                appointment_detail['vehicle_make'] = vehicle['make']
                appointment_detail['vehicle_model'] = vehicle['model']
                appointment_detail['vehicle_year'] = vehicle['year']
                
                appointments_with_details.append(appointment_detail)
        
        return sorted(appointments_with_details, key=lambda x: x['appointment_date'], reverse=True)
    
    def get_upcoming_appointments(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get upcoming appointments for a customer"""
        now = datetime.now()
        appointments_with_details = []
        
        for appointment in self.appointments:
            if (appointment['customer_id'] == customer_id and 
                appointment['appointment_date'] >= now and 
                appointment['status'] == 'scheduled'):
                
                service = self.get_service_by_id(appointment['service_id'])
                vehicle = self.get_vehicle_by_id(appointment['vehicle_id'])
                
                appointment_detail = appointment.copy()
                appointment_detail['service_name'] = service['name']
                appointment_detail['service_duration'] = service['duration_minutes']
                appointment_detail['service_price'] = service['price']
                appointment_detail['vehicle_make'] = vehicle['make']
                appointment_detail['vehicle_model'] = vehicle['model']
                appointment_detail['vehicle_year'] = vehicle['year']
                
                appointments_with_details.append(appointment_detail)
        
        return sorted(appointments_with_details, key=lambda x: x['appointment_date'])
    
    def create_appointment(self, customer_id: int, vehicle_id: int, service_id: int, 
                         appointment_date: datetime, notes: str = None) -> Dict[str, Any]:
        """Create a new appointment"""
        new_appointment = {
            'id': len(self.appointments) + 1,
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'service_id': service_id,
            'appointment_date': appointment_date,
            'status': 'scheduled',
            'notes': notes,
            'created_at': datetime.now()
        }
        self.appointments.append(new_appointment)
        return new_appointment
    
    def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Cancel an appointment"""
        for i, appointment in enumerate(self.appointments):
            if appointment['id'] == appointment_id:
                appointment['status'] = 'cancelled'
                return appointment
        return None
    
    def check_availability(self, service_id: int, appointment_date: date) -> bool:
        """Check if a service is available on a given date"""
        # Simple mock - allow up to 8 appointments per day
        count = 0
        for appointment in self.appointments:
            if (appointment['service_id'] == service_id and 
                appointment['appointment_date'].date() == appointment_date and 
                appointment['status'] in ['scheduled', 'in_progress']):
                count += 1
        
        return count < 8
    
    def find_or_create_vehicle(self, customer_id: int, make: str, model: str, year: int) -> Dict[str, Any]:
        """Find existing vehicle or create new one"""
        # First try to find existing vehicle
        for vehicle in self.vehicles:
            if (vehicle['customer_id'] == customer_id and 
                vehicle['make'].lower() == make.lower() and 
                vehicle['model'].lower() == model.lower() and 
                vehicle['year'] == year):
                return vehicle
        
        # Create new vehicle if not found
        return self.create_vehicle(customer_id, make, model, year)

# Global database instance
db = DatabaseService()
