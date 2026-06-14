import sys
import traceback
if __name__ == "__main__":
    try:
        from app.main import app
        print("Success!")
    except Exception as e:
        print("Error during import:")
        traceback.print_exc()
