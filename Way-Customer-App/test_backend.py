#!/usr/bin/env python3
"""
Simple test backend without complex dependencies
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockDatabase:
    def __init__(self):
        self.customers = [
            {
                'id': 1,
                'phone': '+1234567890',
                'name': 'John Doe',
                'email': 'john.doe@email.com'
            }
        ]
        
        self.vehicles = [
            {
                'id': 1,
                'customer_id': 1,
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2020,
                'status': 'active'
            }
        ]
        
        self.services = [
            {
                'id': 1,
                'name': 'Oil Change',
                'description': 'Complete oil change service',
                'duration_minutes': 30,
                'price': 49.99
            }
        ]
        
        self.appointments = []

    def get_customer_by_phone(self, phone):
        for customer in self.customers:
            if customer['phone'] == phone:
                return customer
        return None

    def get_vehicles_by_customer(self, customer_id):
        return [v for v in self.vehicles if v['customer_id'] == customer_id]

    def get_services(self):
        return self.services

    def create_appointment(self, customer_id, vehicle_id, service_id, appointment_date, notes=None):
        new_appointment = {
            'id': len(self.appointments) + 1,
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'service_id': service_id,
            'appointment_date': appointment_date,
            'status': 'scheduled',
            'notes': notes
        }
        self.appointments.append(new_appointment)
        return new_appointment

db = MockDatabase()

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy'}).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'Automotive AI Backend is running!'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/ai-tools/execute':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            tool_name = data.get('tool_name')
            parameters = data.get('parameters', {})
            
            result = self.execute_tool(tool_name, parameters)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def execute_tool(self, tool_name, parameters):
        try:
            if tool_name == 'check_vehicle_status':
                customer_phone = parameters.get('customer_phone')
                customer = db.get_customer_by_phone(customer_phone)
                
                if not customer:
                    return {
                        'success': False,
                        'message': 'Customer not found with that phone number.'
                    }
                
                vehicles = db.get_vehicles_by_customer(customer['id'])
                if not vehicles:
                    return {
                        'success': True,
                        'message': f"Hi {customer['name']}! No vehicles found. Would you like to add one?"
                    }
                
                message = f"Hi {customer['name']}! Here are your vehicles:\n\n"
                for vehicle in vehicles:
                    message += f"🚗 {vehicle['year']} {vehicle['make']} {vehicle['model']}\n"
                    message += f"Status: ✅ Ready for service\n\n"
                
                return {
                    'success': True,
                    'message': message
                }
            
            elif tool_name == 'get_service_info':
                services = db.get_services()
                message = "Here are our available services:\n\n"
                for service in services:
                    message += f"🔧 {service['name']}\n"
                    message += f"{service['description']}\n"
                    message += f"Duration: {service['duration_minutes']} minutes | Price: ${service['price']}\n\n"
                
                return {
                    'success': True,
                    'message': message
                }
            
            elif tool_name == 'book_appointment':
                customer_phone = parameters.get('customer_phone')
                service_name = parameters.get('service_name')
                vehicle_info = parameters.get('vehicle_info')
                
                customer = db.get_customer_by_phone(customer_phone)
                if not customer:
                    customer = {
                        'id': len(db.customers) + 1,
                        'phone': customer_phone,
                        'name': 'New Customer',
                        'email': None
                    }
                    db.customers.append(customer)
                
                # Find service
                service = None
                for s in db.services:
                    if service_name.lower() in s['name'].lower():
                        service = s
                        break
                
                if not service:
                    return {
                        'success': False,
                        'message': f"Service '{service_name}' not found. Available services: Oil Change, Brake Inspection, etc."
                    }
                
                # Create appointment
                appointment = db.create_appointment(
                    customer['id'], 
                    1,  # vehicle_id
                    service['id'], 
                    '2024-01-15 10:00:00',
                    f"Vehicle: {vehicle_info}"
                )
                
                return {
                    'success': True,
                    'message': f"Perfect! I've booked your {service['name']} appointment. Your appointment ID is {appointment['id']}."
                }
            
            else:
                return {
                    'success': False,
                    'message': f'Unknown tool: {tool_name}'
                }
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'message': 'Sorry, I encountered an error processing your request.'
            }

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8000), APIHandler)
    print("🚀 Starting Simple Automotive AI Backend...")
    print("📍 Backend URL: http://localhost:8000")
    print("🔧 Health Check: http://localhost:8000/health")
    print("")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()
