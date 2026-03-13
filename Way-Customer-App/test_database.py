#!/usr/bin/env python3
"""
Test database connection and setup
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from database_postgres import db
    print("✅ Database module imported successfully")
    
    # Test connection
    try:
        conn = db.get_connection()
        print("✅ Database connection successful")
        conn.close()
        
        # Test a simple query
        services = db.get_services()
        print(f"✅ Database query successful - found {len(services)} services")
        
        # Test customer operations
        customer = db.get_customer_by_phone('+1234567890')
        if customer:
            print(f"✅ Customer found: {customer['name']}")
        else:
            print("ℹ️  No customer found with phone +1234567890 (this is normal)")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure PostgreSQL is running and the database 'automotive_ai' exists")
        
except ImportError as e:
    print(f"❌ Failed to import database module: {e}")
    print("Make sure psycopg2-binary is installed")
