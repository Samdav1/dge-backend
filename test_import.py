import sys
import traceback
try:
    from app.main import app
    print("Success!")
except Exception as e:
    print("Error during import:")
    traceback.print_exc()
