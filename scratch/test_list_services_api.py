from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead
from app.schemas.user import UserStatus
import uuid

# Mock get_current_user to return a dummy user
async def mock_get_current_user():
    return UserRead(
        id=uuid.UUID("d6833504-808f-4bdd-a13b-7dfc17985de1"),
        email="test@example.com",
        username="testuser",
        status=UserStatus.active,
        referral_code=None,
        is_admin=False
    )

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

# Hit the API endpoint
headers = {
    "X-API-KEY": "vo59nkWcjkAtpPosuyqkaF3PDO1llaTT0QQA4JH0ECw3gLDDm9/awTin+wyPvgXLR7iLhTRuXvzs0KcuTe12xw=="
}
response = client.get("/services/services/", headers=headers)

print("Status code:", response.status_code)
if response.status_code == 200:
    data = response.json()
    print("Number of items:", len(data))
    if len(data) > 0:
        print("Keys of first item:", data[0].keys())
        import json
        print("Sample item json:", json.dumps(data[0], indent=2))
else:
    print("Response text:", response.text)
