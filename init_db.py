#!/usr/bin/env python3
"""
Database initialization script for the Career Guidance app.
Run this script to create the database tables.
"""

from app import app, db

def init_database():
    """Initialize the database with all tables."""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Database initialized successfully!")
            print("Database location: instance/app.db")
            
            # Test the connection
            from models import User
            user_count = User.query.count()
            print(f"Current users in database: {user_count}")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Initializing Career Guidance Database...")
    init_database()
