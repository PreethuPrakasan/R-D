-- Database schema for automotive AI customer service
-- Run this in your PostgreSQL database

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    vin VARCHAR(17),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'in_service', 'completed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create services table
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create appointments table
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
    appointment_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_vehicles_customer_id ON vehicles(customer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_customer_id ON appointments(customer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

-- Insert sample services
INSERT INTO services (name, description, duration_minutes, price) VALUES
('Oil Change', 'Complete oil change service with filter replacement', 30, 49.99),
('Brake Inspection', 'Comprehensive brake system inspection and adjustment', 45, 79.99),
('Tire Rotation', 'Rotate tires and check tire pressure', 20, 29.99),
('Engine Diagnostic', 'Complete engine diagnostic scan and analysis', 60, 99.99),
('Transmission Service', 'Transmission fluid change and inspection', 90, 149.99),
('Battery Check', 'Battery testing and terminal cleaning', 15, 19.99),
('AC Service', 'Air conditioning system check and recharge', 45, 89.99),
('Wheel Alignment', 'Four-wheel alignment service', 60, 79.99)
ON CONFLICT DO NOTHING;

-- Insert sample customer and vehicle for testing
INSERT INTO customers (phone, name, email) VALUES
('+1234567890', 'John Doe', 'john.doe@email.com')
ON CONFLICT (phone) DO NOTHING;

INSERT INTO vehicles (customer_id, make, model, year, vin, status) VALUES
(1, 'Toyota', 'Camry', 2020, '1HGBH41JXMN109186', 'active'),
(1, 'Honda', 'Civic', 2018, '2HGBH41JXMN109187', 'active')
ON CONFLICT DO NOTHING;
