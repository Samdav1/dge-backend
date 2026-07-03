from app.main import app

print("Filtered routes containing 'services':")
for route in app.routes:
    if "services" in route.path:
        print(f"Path: {route.path} | Name: {route.name} | Methods: {getattr(route, 'methods', None)}")
