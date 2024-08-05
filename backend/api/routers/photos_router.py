import base64
import imghdr

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


@photos_router.patch("/get_profile_photo/", status_code=status.HTTP_200_OK)
def get_profile_image(id: int):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT image FROM users_images WHERE user_id = %s AND is_profile_image = TRUE", (id,))
                profile_image_data = cursor.fetchone()
                if profile_image_data is None:
                    raise HTTPException(status_code=404, detail="Фото профиля не найдено")

                profile_image_bytes = profile_image_data[
                    0]  # Преобразование двоичного кода изображения в b64 и передача url
                image_type = imghdr.what(BytesIO(profile_image_bytes))
                profile_image_base64 = base64.b64encode(profile_image_bytes).decode('utf-8')
                profile_image = f"data:image/{image_type};base64,{profile_image_base64}"

                return profile_image
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
