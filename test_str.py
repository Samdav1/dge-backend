from app.models.user import RefreshToken
import uuid
import datetime
rt = RefreshToken(id=uuid.uuid4(), user_id=uuid.uuid4(), token="eyJhbG...", created_at=datetime.datetime.now(), expires_at=datetime.datetime.now())
print(str(rt))
