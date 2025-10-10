import uuid
from datetime import date
from typing import Type, TypeVar, Any, Dict, Callable
from fastapi import HTTPException, Request, Depends
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


async def profile_form_parser(
        request: Request,
        model_cls: Type[T]
) -> T:
    """
    Parses multipart/form-data and constructs a Pydantic model instance.
    Handles type conversion (string UUIDs/Dates) which Pydantic usually handles for JSON.
    """
    try:
        form_data = await request.form()
        data: Dict[str, Any] = {}

        for key, value in form_data.items():
            if not value:
                continue

            if hasattr(value, 'filename'):
                continue

            if key == "date_of_birth":
                try:
                    data[key] = date.fromisoformat(str(value))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid date format for {key}. Use YYYY-MM-DD.")
            elif key in ("team_id", "user_id"):
                try:
                    data[key] = uuid.UUID(str(value))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid UUID format for {key}.")
            else:
                data[key] = value

        user_id = getattr(request.state, "user_id", None)
        if user_id and 'user_id' not in data:
            try:
                data["user_id"] = uuid.UUID(user_id)
            except ValueError:
                pass

        return model_cls(**data)

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e.errors()}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal form parsing error: {e}")


def DependsForm(model_cls: Type[T]) -> Callable[[Request], T]:
    """
    Factory to create a dependency for a specific Pydantic model from form data.
    """

    async def dependency(request: Request) -> T:
        return await profile_form_parser(request, model_cls)

    return Depends(dependency)