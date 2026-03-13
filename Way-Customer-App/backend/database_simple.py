import psycopg2
import psycopg2.extras
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.connection_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'automotive_ai',
            'user': 'postgres',
            'password': 'root'
        }
    
    def get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(**self.connection_params)
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute a query and return results"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                if fetch_one:
                    result = cursor.fetchone()
                    return dict(result) if result else None
                elif fetch_all:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # Customer operations
    def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get customer by phone number"""
        return self.execute_query(
            "SELECT * FROM customers WHERE phone = %s", 
            (phone,), 
            fetch_one=True
        )
    
    def create_customer(self, phone: str, name: str, email: str = None) -> Dict[str, Any]:
        """Create a new customer"""
        return self.execute_query(
            "INSERT INTO customers (phone, name, email) VALUES (%s, %s, %s) RETURNING *",
            (phone, name, email),
            fetch_one=True
        )
    
    def update_customer(self, customer_id: int, **updates) -> Dict[str, Any]:
        """Update customer information"""
        if not updates:
            return self.get_customer_by_id(customer_id)
        
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        values = list(updates.values()) + [customer_id]
        
        return self.execute_query(
            f"UPDATE customers SET {set_clause} WHERE id = %s RETURNING *",
            tuple(values),
            fetch_one=True
        )
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        return self.execute_query(
            "SELECT * FROM customers WHERE id = %s", 
            (customer_id,), 
            fetch_one=True
        )
    
    # Vehicle operations
    def get_vehicles_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all vehicles for a customer"""
        return self.execute_query(
            "SELECT * FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC",
            (customer_id,),
            fetch_all=True
        )
    
    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """Get vehicle by ID"""
        return self.execute_query(
            "SELECT * FROM vehicles WHERE id = %s", 
            (vehicle_id,), 
            fetch_one=True
        )
    
    def create_vehicle(self, customer_id: int, make: str, model: str, year: int, vin: str = None) -> Dict[str, Any]:
        """Create a new vehicle"""
        return self.execute_query(
            "INSERT INTO vehicles (customer_id, make, model, year, vin) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (customer_id, make, model, year, vin),
            fetch_one=True
        )
    
    def update_vehicle_status(self, vehicle_id: int, status: str) -> Dict[str, Any]:
        """Update vehicle status"""
        return self.execute_query(
            "UPDATE vehicles SET status = %s WHERE id = %s RETURNING *",
            (status, vehicle_id),
            fetch_one=True
        )
    
    # Service operations
    def get_services(self) -> List[Dict[str, Any]]:
        """Get all active services"""
        return self.execute_query(
            "SELECT * FROM services WHERE is_active = true ORDER BY name",
            fetch_all=True
        )
    
    def get_service_by_id(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get service by ID"""
        return self.execute_query(
            "SELECT * FROM services WHERE id = %s AND is_active = true", 
            (service_id,), 
            fetch_one=True
        )
    
    def get_service_by_name(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service by name (fuzzy matching)"""
        results = self.execute_query(
            "SELECT * FROM services WHERE is_active = true AND LOWER(name) LIKE LOWER(%s)",
            (f"%{service_name}%",),
            fetch_all=True
        )
        return results[0] if results else None
    
    # Appointment operations
    def get_appointments_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all appointments for a customer with service and vehicle details"""
        return self.execute_query("""
            SELECT a.*, s.name as service_name, s.duration_minutes, s.price,
                   v.make, v.model, v.year
            FROM appointments a 
            JOIN services s ON a.service_id = s.id 
            JOIN vehicles v ON a.vehicle_id = v.id 
            WHERE a.customer_id = %s 
            ORDER BY a.appointment_date DESC
        """, (customer_id,), fetch_all=True)
    
    def get_upcoming_appointments(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get upcoming appointments for a customer"""
        return self.execute_query("""
            SELECT a.*, s.name as service_name, s.duration_minutes, s.price,
                   v.make, v.model, v.year
            FROM appointments a 
            JOIN services s ON a.service_id = s.id 
            JOIN vehicles v ON a.vehicle_id = v.id 
            WHERE a.customer_id = %s 
            AND a.appointment_date >= NOW() 
            AND a.status = 'scheduled'
            ORDER BY a.appointment_date ASC
        """, (customer_id,), fetch_all=True)
    
    def create_appointment(self, customer_id: int, vehicle_id: int, service_id: int, 
                         appointment_date: datetime, notes: str = None) -> Dict[str, Any]:
        """Create a new appointment"""
        return self.execute_query("""
            INSERT INTO appointments (customer_id, vehicle_id, service_id, appointment_date, notes) 
            VALUES (%s, %s, %s, %s, %s) RETURNING *
        """, (customer_id, vehicle_id, service_id, appointment_date, notes), fetch_one=True)
    
    def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Cancel an appointment"""
        return self.execute_query(
            "UPDATE appointments SET status = 'cancelled' WHERE id = %s RETURNING *",
            (appointment_id,),
            fetch_one=True
        )
    
    def check_availability(self, service_id: int, appointment_date: date) -> bool:
        """Check if a service is available on a given date"""
        result = self.execute_query("""
            SELECT COUNT(*) as count 
            FROM appointments 
            WHERE service_id = %s 
            AND DATE(appointment_date) = %s 
            AND status IN ('scheduled', 'in_progress')
        """, (service_id, appointment_date), fetch_one=True)
        
        existing_count = result['count']
        # Assuming max 8 appointments per day per service
        return existing_count < 8
    
    def find_or_create_vehicle(self, customer_id: int, make: str, model: str, year: int) -> Dict[str, Any]:
        """Find existing vehicle or create new one"""
        # First try to find existing vehicle
        vehicles = self.get_vehicles_by_customer(customer_id)
        for vehicle in vehicles:
            if (vehicle['make'].lower() == make.lower() and 
                vehicle['model'].lower() == model.lower() and 
                vehicle['year'] == year):
                return vehicle
        
        # Create new vehicle if not found
        return self.create_vehicle(customer_id, make, model, year)

# Global database instance
db = DatabaseService()
