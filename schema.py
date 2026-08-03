from datetime import datetime
from pydantic import BaseModel


class UserGet(BaseModel):
    """
    Модель данных пользователя для API-ответов.

    Атрибуты:
    - id: уникальный идентификатор пользователя.
    - gender: пол пользователя, представлен числом
    - age: возраст пользователя.
    - country: страна проживания.
    - city: город проживания.
    - exp_group: группа эксперимента, к которой относится пользователь.
    - os: операционная система устройства пользователя
    - source: источник регистрации или привлечения пользователя.
    """

    # TODO: Определить все поля с нужными типами данных
    id: int
    gender: int
    age: int
    country: str
    city: str
    exp_group: int
    os: str
    source: str

    class Config:
        orm_mode = True

class PostGet(BaseModel):
    """
    Модель данных поста для API-ответов.

    Атрибуты:
    - id: уникальный идентификатор поста.
    - text: текстовое содержимое поста.
    - topic: тема или категория поста.
    """

    # TODO: Определить все поля с нужными типами данных
    id: int
    text: str
    topic: str

    class Config:
        orm_mode = True


class FeedGet(BaseModel):
    """
    Модель данных действия пользователя с постом для API-ответов.

    Атрибуты:
    - user_id: идентификатор пользователя, который совершил действие.
    - post_id: идентификатор поста, над которым совершено действие.
    - user: вложенный объект UserGet с данными пользователя.
    - post: вложенный объект PostGet с данными поста.
    - action: тип действия
    - time: дата и время совершения действия в формате datetime.
    """

    # TODO: Определить все поля с нужными типами данных
    user_id: int
    post_id: int
    user: UserGet # TODO: Связать с классом UserGet
    post: PostGet  # TODO: Связать с классом PostGet
    action: str
    time: datetime
    
    class Config:
        orm_mode = True


if __name__ == "__main__":
    from models import User

    # Создаем обычный объект (например, загружаем из БД)
    user_obj = User(1, 0, 25, "USA", "New York", 2, "iOS", "ad_campaign")

    # Конвертируем обычный объект в Pydantic-модель UserGet для валидации и удобной работы
    user_pydantic = UserGet.model_validate(user_obj, from_attributes=True)

    # Теперь из Pydantic-модели можно легко получить JSON, словарь или использовать саму модель напрямую
    print(user_pydantic.model_dump_json())  # JSON-строка
    print(user_pydantic.model_dump())  # словарь Python
    print(user_pydantic)  # сам объект модели с удобным доступом к полям

### Output:
# {"id":1,"gender":0,"age":25,"country":"USA","city":"New York","exp_group":2,"os":"iOS","source":"ad_campaign"}
# {'id': 1, 'gender': 0, 'age': 25, 'country': 'USA', 'city': 'New York', 'exp_group': 2, 'os': 'iOS', 'source': 'ad_campaign'}
# id=1 gender=0 age=25 country='USA' city='New York' exp_group=2 os='iOS' source='ad_campaign'