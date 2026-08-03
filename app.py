import os
import pickle
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from loguru import logger

from database import postgres_connection
from schema import PostGet


# === Вспомогательные функции ===
def load_sql(
    query: str,
    dtypes: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Выполняет SQL-запрос и возвращает DataFrame.
    """
    conn = postgres_connection()

    try:
        df = pd.read_sql(query, conn, dtype=dtypes)
    except Exception as e:
        raise RuntimeError(
            f"❌ Ошибка при выполнении SQL-запроса: {e}\nЗапрос: {query}"
        ) from e
    finally:
        conn.close()

    return df


def load_model(model_path: str = "model.pkl"):
    """
    Загружает ML-модель из pickle-файла.
    """
    if os.environ.get("IS_LMS", "0") == "1":
        model_path = os.environ["MODEL_PATH"]

    logger.info(f"Загрузка модели из файла {model_path}...")

    try:
        with open(model_path, "rb") as file:
            model = pickle.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Файл модели не найден: {model_path}")
    except Exception as e:
        raise RuntimeError(f"❌ Ошибка при загрузке модели: {e}") from e

    logger.success("Модель успешно загружена")

    return model


# === Загрузка основных ресурсов ===
logger.info("Инициализация сервиса...")

app = FastAPI()


# При локальном запуске используем путь к нашей модели.
# В LMS путь будет автоматически заменён через MODEL_PATH.
model = load_model("models/catboost_recommender.pkl")

MODEL_FEATURES = list(model.feature_names_)

logger.info(f"Признаки модели: {MODEL_FEATURES}")


# === Пользовательские признаки ===
logger.info("Загружаем признаки пользователей...")

user_features = load_sql(
    """
    SELECT
        user_id,
        age,
        gender,
        country,
        city,
        exp_group,
        os,
        source
    FROM vvtom_user_features
    """
)

# user_id станет индексом — так поиск пользователя работает быстрее.
user_features = user_features.set_index("user_id")

USER_CATEGORICAL_COLUMNS = [
    "gender",
    "country",
    "city",
    "exp_group",
    "os",
    "source",
]

# При обучении эти признаки были преобразованы в строки.
for column in USER_CATEGORICAL_COLUMNS:
    user_features[column] = user_features[column].astype(str)

logger.info(f"Загружено пользователей: {len(user_features)}")


# === Признаки постов ===
logger.info("Загружаем признаки постов...")

post_features = load_sql(
    """
    SELECT
        features.*,
        posts.text
    FROM vvtom_post_features AS features
    INNER JOIN public.post_text_df AS posts
        ON features.post_id = posts.post_id
    ORDER BY features.post_id
    """
)

# topic при обучении был строковым категориальным признаком.
post_features["topic"] = post_features["topic"].astype(str)

# Эти столбцы нужны только для формирования ответа API,
# но не должны передаваться модели.
post_response_data = post_features[["post_id", "text", "topic"]].copy()

# Базовые признаки всех постов.
post_model_features = post_features.drop(columns=["post_id", "text"])

logger.info(f"Загружено постов: {len(post_features)}")

logger.success("Сервис успешно инициализирован")


@app.get(
    "/post/recommendations/",
    response_model=List[PostGet],
)
def recommended_posts(
    user_id: int,
    dt: datetime,
    limit: int = 10,
) -> List[PostGet]:
    """
    Возвращает top-N постов с наибольшей
    предсказанной вероятностью лайка.
    """

    # 1. Проверяем наличие пользователя.
    if user_id not in user_features.index:
        raise HTTPException(
            status_code=404,
            detail=f"Пользователь {user_id} не найден",
        )

    if limit <= 0:
        return []

    # 2. Получаем признаки одного пользователя.
    user_row = user_features.loc[user_id]

    # 3. Создаём кандидатов:
    # один пользователь комбинируется со всеми постами.
    candidates = post_model_features.copy()

    candidates["gender"] = user_row["gender"]
    candidates["age"] = user_row["age"]
    candidates["country"] = user_row["country"]
    candidates["city"] = user_row["city"]
    candidates["exp_group"] = user_row["exp_group"]
    candidates["os"] = user_row["os"]
    candidates["source"] = user_row["source"]

    # 4. Добавляем временные признаки.
    candidates["hour"] = dt.hour

    # Monday=0 ... Sunday=6 — так же, как pandas dayofweek.
    candidates["dow"] = dt.weekday()

    # 5. Восстанавливаем точный порядок признаков,
    # использованный при обучении.
    candidates = candidates[MODEL_FEATURES]

    # 6. Получаем вероятность класса 1 — вероятность лайка.
    probabilities = model.predict_proba(candidates)[:, 1]

    effective_limit = min(limit, len(probabilities))

    # 7. Быстро выбираем top-N без полной сортировки
    # всех нескольких тысяч постов.
    top_positions = np.argpartition(
        -probabilities,
        effective_limit - 1,
    )[:effective_limit]

    # Сортируем только выбранные top-N постов.
    top_positions = top_positions[np.argsort(probabilities[top_positions])[::-1]]

    top_posts = post_response_data.iloc[top_positions]

    # 8. Формируем ответ FastAPI.
    recs = [
        PostGet(
            id=int(row.post_id),
            text=row.text,
            topic=row.topic,
        )
        for row in top_posts.itertuples(index=False)
    ]

    return recs
