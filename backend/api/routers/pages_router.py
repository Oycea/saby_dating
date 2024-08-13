import base64
import imghdr
import io
import json
from routers.session import open_conn
from fastapi import HTTPException, APIRouter, Depends
from routers.authorization_router import User, get_current_user

pages_router = APIRouter(
    prefix="",
    tags=["Pages"]
)


def get_user_info_by_id(id: int):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM users WHERE id = %s AND is_deleted = false", (id,))
                name = cursor.fetchone()[0]
                if name is None:
                    raise HTTPException(status_code=404, detail="Имя пользователя не найдено")

                profile_image = get_profile_image(id)

                return {"name": name, "profile_image": profile_image}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


def get_profile_image(id: int):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT image FROM users_images WHERE user_id = %s AND is_profile_image = TRUE AND is_deleted = false", (id,))
                profile_image_data = cursor.fetchone()
                if profile_image_data is None:
                    raise HTTPException(status_code=404, detail="Фото профиля не найдено")

                profile_image_bytes = profile_image_data[
                    0]  # Преобразование двоичного кода изображения в b64 и передача url
                image_type = imghdr.what(io.BytesIO(profile_image_bytes))
                profile_image_base64 = base64.b64encode(profile_image_bytes).decode('utf-8')
                profile_image = f"data:image/{image_type};base64,{profile_image_base64}"

                return profile_image
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@pages_router.get("/chat", name='chat')  # Страница чата
def get_chat_page(dialogue_id: int, offset: int = 0, limit: int = 30, current_user: User = Depends(get_current_user)):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                self_user = json.loads(current_user.json())  # Преобразование строки в объект
                cursor.execute(
                    "SELECT user_id, message, TO_CHAR(date, 'HH24:MI') as date, id FROM messages WHERE dialogue_id = %s AND is_deleted = false ORDER BY id DESC LIMIT %s OFFSET %s",
                    (dialogue_id, limit, offset))
                limited_result = cursor.fetchall()  # Возвращает кортеж user_id, message, date и id сообщения
                if limited_result is None:
                    raise HTTPException(status_code=404, detail="Сообщения не найдены.")

                cursor.execute("SELECT message FROM messages WHERE is_deleted = false AND dialogue_id = %s", (dialogue_id,))
                full_result = cursor.fetchall()
                if full_result is None:
                    raise HTTPException(status_code=404, detail="Сообщения не найдены.")
                full_result_len = len(full_result)  # Возвращает кол-во всех сообщений в диалоге

                profile_image = get_profile_image(self_user['id'])

                cursor.execute("""
                                    SELECT 
                                        CASE 
                                            WHEN user1_id = %s THEN user2_id
                                            WHEN user2_id = %s THEN user1_id
                                        END
                                    FROM 
                                        dialogues
                                    WHERE 
                                        id = %s AND is_deleted = false
                                """,
                               (self_user['id'], self_user['id'], dialogue_id))  # Возвращает id другого пользователя
                other_user_id = cursor.fetchone()[0]
                if other_user_id is None:
                    raise HTTPException(status_code=404, detail="ID пользователя не найден.")
                other_user = get_user_info_by_id(other_user_id)  # Возвращает имя и фото другого пользователя

                return {"limited_result": limited_result, "full_result_len": full_result_len, 'self_user': self_user,
                                                                                     'profile_image': profile_image,
                                                                                     'other_user': other_user,
                                                                                     'dialogue_id': dialogue_id}
    except Exception as ex:
        print(f"Error occurred: {ex}")
        raise HTTPException(status_code=500, detail=str(ex))


@pages_router.get("/dialogues", name="dialogues")  # Страница диалогов
def get_dialogues_page(current_user: User = Depends(get_current_user)):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                self_user = json.loads(current_user.json())  # Преобразование строки в объект

                cursor.execute("""
                                    SELECT 
                                        id AS dialogue_id,
                                        CASE 
                                            WHEN user1_id = %s THEN user2_id
                                            WHEN user2_id = %s THEN user1_id
                                        END
                                    FROM 
                                        dialogues
                                    WHERE 
                                        (user1_id = %s OR user2_id = %s) AND is_deleted = false
                                """,
                               (self_user['id'], self_user['id'], self_user['id'], self_user['id']))
                dialogues = cursor.fetchall()  # Возвращает id диалога и id всех собеседников пользователя
                if dialogues is None:
                    raise HTTPException(status_code=404, detail="Диалог или ID пользователя не найдены")

                other_user = []
                for dialogue in dialogues:
                    user_info = get_user_info_by_id(dialogue[1])  # Получаем имя и фото всех собеседников
                    other_user += [user_info]

                return {"dialogues": dialogues, "other_user": other_user}
    except Exception as ex:
        print(f"Error occurred: {ex}")
        raise HTTPException(status_code=500, detail=str(ex))


@pages_router.put("/delete_dialogue/{dialogueId}", name="delete_dialogue")
def delete_dialogue(dialogueId: int):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE dialogues SET is_deleted = true WHERE id = %s", (dialogueId,))
                return {"detail": "Диалог успешно удалён"}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


#Функция поиска диалога
@pages_router.get('/search_dialog/{name_second_user}', name="search dialog by name")  # Добавить в pages
def search_dialog(name_second_user: str, current_user: User = Depends(get_current_user)) -> dict[str, list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                main_user_id = current_user.id
                cursor.execute("SELECT dialogues.id "
                               "FROM dialogues JOIN users ON dialogues.user2_id = users.id "
                               "WHERE (dialogues.user1_id = %s AND users.name = %s  AND dialogues.is_deleted = false ) ",
                               (main_user_id, name_second_user,))
                find_dialog = cursor.fetchall()
                cursor.execute("SELECT dialogues.id "
                               "FROM dialogues JOIN users ON dialogues.user1_id = users.id "
                               "WHERE (dialogues.user2_id = %s AND users.name = %s  AND dialogues.is_deleted = false ) ",
                               (main_user_id, name_second_user,))
                find_dialog = find_dialog + cursor.fetchall()
                find_dialog = [dialog[0] for dialog in find_dialog]
                if not find_dialog:
                    raise HTTPException(status_code=404, detail="Dialog is not found")
                return {f"the dialog was successfully found with users by name{name_second_user}": find_dialog}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

