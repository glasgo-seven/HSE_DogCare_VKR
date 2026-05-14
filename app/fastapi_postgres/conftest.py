import os

os.environ["DATABASE_URL"] = "sqlite:///./test_petcare.db"

import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
from api import app, get_session

# Изолированная тестовая БД
TEST_DATABASE_URL = "sqlite:///./test_petcare.db"

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

# --- Фикстуры данных (только обязательные поля + опциональные для полноты) ---
@pytest.fixture(name="owner_data")
def owner_data():
    return {"name": "Иван Петров", "age": 30, "email": "ivan@test.com", "phone": "+79001234567"}

@pytest.fixture(name="owner_min_data")
def owner_min_data():
    return {"name": "Минимальный Владелец"}

@pytest.fixture(name="breed_data")
def breed_data():
    return {"name": "Лабрадор"}

@pytest.fixture(name="role_data")
def role_data():
    return {"name": "Администратор"}

@pytest.fixture(name="employee_data")
def employee_data():
    return {"name": "Анна Сидорова", "role_id": 1, "age": 35}

@pytest.fixture(name="employee_min_data")
def employee_min_data():
    return {"name": "Только Обязательное", "role_id": 1}

@pytest.fixture(name="event_data")
def event_data():
    return {"name": "Выставка", "manager_id": 1, "visitor_amount": 10, "duration_min": 60}

@pytest.fixture(name="event_min_data")
def event_min_data():
    return {"name": "Мин. Событие", "manager_id": 1, "visitor_amount": 5}

@pytest.fixture(name="user_data")
def user_data():
    return {"login": "testuser", "password": "SecurePass123!", "user_type": False}