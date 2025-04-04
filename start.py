import os
import sys
import time
import subprocess
import sqlite3
import datetime
import base64

# Create a simple Deriv icon if it doesn't exist
def create_deriv_icon():
    """Create a simple Deriv icon if it doesn't exist."""
    icon_path = os.path.join("static", "assets", "deriv-icon.png")
    
    if not os.path.exists(icon_path):
        # Base64 encoded simple deriv logo (orange D)
        deriv_icon_base64 = """
        iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAFyGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNS42LWMxNDUgNzkuMTYzNDk5LCAyMDE4LzA4LzEzLTE2OjQwOjIyICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxOSAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDIzLTA0LTAzVDE2OjAxOjU5KzAzOjAwIiB4bXA6TW9kaWZ5RGF0ZT0iMjAyMy0wNC0wM1QxNjowMzozNSswMzowMCIgeG1wOk1ldGFkYXRhRGF0ZT0iMjAyMy0wNC0wM1QxNjowMzozNSswMzowMCIgZGM6Zm9ybWF0PSJpbWFnZS9wbmciIHBob3Rvc2hvcDpDb2xvck1vZGU9IjMiIHBob3Rvc2hvcDpJQ0NQcm9maWxlPSJzUkdCIElFQzYxOTY2LTIuMSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpmOWNiYjJiMS03OWZh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
        """
        
        # Write the icon to a file
        try:
            # Remove header part from base64 string
            deriv_icon_base64 = deriv_icon_base64.strip().replace('\n', '')
            # Decode the base64 data
            icon_data = base64.b64decode(deriv_icon_base64)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(icon_path), exist_ok=True)
            
            # Write the icon file
            with open(icon_path, 'wb') as f:
                f.write(icon_data)
            
            print(f"✅ Created Deriv icon at {icon_path}")
        except Exception as e:
            print(f"❌ Failed to create Deriv icon: {e}")

def init_database():
    """Initialize the database."""
    try:
        # Check if update_database.py exists and run it
        if os.path.exists('update_database.py'):
            print("📊 Running database update script...")
            subprocess.run([sys.executable, 'update_database.py'], check=True)
        
        # Check if database.py exists and run it
        if os.path.exists('database.py'):
            print("📊 Initializing database...")
            subprocess.run([sys.executable, 'database.py'], check=True)
            
        print("✅ Database initialization complete")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def start_application():
    """Start the main application."""
    try:
        print("🚀 Starting the application...")
        subprocess.run([sys.executable, 'main.py'], check=True)
        return True
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return False

def main():
    """Main function to initialize and start the application."""
    print("🔍 Starting initialization process...")
    print("="*50)
    
    # Create the Deriv icon
    create_deriv_icon()
    print("="*50)
    
    # Initialize the database
    database_success = init_database()
    if not database_success:
        print("❌ Failed to initialize database. Exiting.")
        sys.exit(1)
    
    print("="*50)
    
    # Start the application
    start_success = start_application()
    if not start_success:
        print("❌ Failed to start application. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main() 