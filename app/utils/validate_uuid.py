import uuid
from fastapi import HTTPException, status

def validate_uuid(id_str: str) -> None:
    try:
        uuid.UUID(id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid meal ID '{id_str}'. A valid UUID is expected."
        )