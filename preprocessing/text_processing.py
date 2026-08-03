import os
import re
import pandas as pd
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer


def pre_clean(text: str) -> str:
    """Первичная очистка текста от ссылок и спецсимволов."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)  # Удаляем ссылки
    text = re.sub(r"[^a-z\s]", "", text)  # Оставляем только латиницу и пробелы
    return text


def clean_and_vectorize_text(
    text_series: pd.Series, max_features: int = 50, prefix: str = "tfidf_"
) -> pd.DataFrame:
    """
    Принимает pd.Series с текстами, выполняет лемматизацию через spaCy
    и возвращает pd.DataFrame с TF-IDF признаками в формате float32.
    """
    # 1. Загрузка модели spaCy
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Модель en_core_web_sm не найдена. Начинаю скачивание...")
        os.system("python -m spacy download en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

    # 2. Первичная очистка текста
    pre_cleaned = text_series.apply(pre_clean).astype(str)

    # 3. Лемматизация через nlp.pipe в один поток
    cleaned_texts = []
    docs = nlp.pipe(pre_cleaned, disable=["ner", "parser"])

    for doc in docs:
        # Убираем английские стоп-слова, пунктуацию и пробелы
        lemmas = [
            token.lemma_
            for token in doc
            if not token.is_stop and not token.is_punct and not token.is_space
        ]
        cleaned_texts.append(" ".join(lemmas))

    # 4. Векторизация TF-IDF
    tfidf = TfidfVectorizer(max_features=max_features)
    tfidf_matrix = tfidf.fit_transform(cleaned_texts)
    feature_names = tfidf.get_feature_names_out()

    # 5. Сборка итогового DataFrame с оптимизацией памяти (float32)
    tfidf_df = pd.DataFrame(
        tfidf_matrix.toarray(),
        columns=feature_names,
        dtype="float32",  # Сразу создаем в float32, чтобы не тратить память
    ).add_prefix(prefix)

    return tfidf_df


# ТЕСТ

# # Исходный датафрейм с постами
# posts_df = pd.DataFrame(
#     {
#         "post_id": [1, 2],
#         "text": [
#             "Bitcoin price is skyrocketing today!",
#             "Delicious apple pie recipe for dinner.",
#         ],
#         "topic": ["finance", "food"],
#     }
# )

# # Создаем TF-IDF матрицу для текстов в датафрейме

# tfidf_features = clean_and_vectorize_text(
#     posts_df["text"], max_features=10, prefix="Z_"
# )

# final_posts_features = pd.concat([posts_df[["post_id"]], tfidf_features], axis=1)

# print(final_posts_features)
