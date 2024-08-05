from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
from io import BytesIO
from routers.session import open_conn
from routers.authorization_router import get_current_user, User


photos_router = APIRouter(prefix='/photos', tags=['Photos'])


@photos_router.post("/upload_photo/", status_code=status.HTTP_201_CREATED)
async def upload_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    try:
        file_data = await file.read()

        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users_images (user_id, image, is_profile_image, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (current_user.id, file_data, False, datetime.utcnow())
                )
        return {"detail": "Фотография загружена"}

    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@photos_router.patch("/set_profile_photo/", status_code=status.HTTP_200_OK)
def set_profile_photo(photo_id: int, current_user: User = Depends(get_current_user)):
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users_images SET is_profile_image = FALSE WHERE user_id = %s
                    """,
                    (current_user.id,)
                )
                cursor.execute(
                    """
                    UPDATE users_images SET is_profile_image = TRUE WHERE id = %s AND user_id = %s
                    """,
                    (photo_id, current_user.id)
                )
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Фотография не найдена или не принадлежит пользователю"
                    )
        return {"detail": "Фото профиля обновлено"}

    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@photos_router.get("/profile_photo/", status_code=status.HTTP_200_OK)
def get_profile_photo(current_user: User = Depends(get_current_user)):
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT image FROM users_images WHERE user_id = %s AND is_profile_image = TRUE
                    """,
                    (current_user.id,)
                )
                profile_image_data = cursor.fetchone()
                if profile_image_data is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Фото профиля не установлено"
                    )
                return StreamingResponse(BytesIO(profile_image_data[0]), media_type="image/jpeg")

    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )
