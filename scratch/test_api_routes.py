from app.main import app

print("All registered routes in FastAPI app:")
for route in app.routes:
    # Print route path and name
    print(f"Path: {route.path} | Name: {route.name} | Methods: {getattr(route, 'methods', None)}")
