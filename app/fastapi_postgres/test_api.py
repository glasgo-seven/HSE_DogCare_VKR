import pytest
from fastapi import status
from sqlmodel import select
from models import Owner, Dog, Breed, Role, Employee, Event, User

# ==================== AUTH ====================
class TestAuth:
    def test_register_success(self, client, user_data):
        res = client.post("/register", json=user_data)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["login"] == user_data["login"]

    def test_register_duplicate(self, client, user_data):
        client.post("/register", json=user_data)
        res = client.post("/register", json=user_data)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_required(self, client):
        res = client.post("/register", json={"password": "123"})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_success(self, client, user_data):
        client.post("/register", json=user_data)
        res = client.post("/token", data={"username": user_data["login"], "password": user_data["password"]})
        assert res.status_code == status.HTTP_200_OK
        assert "access_token" in res.json()

    def test_login_wrong_password(self, client, user_data):
        client.post("/register", json=user_data)
        res = client.post("/token", data={"username": user_data["login"], "password": "WrongPass"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

# ==================== OWNERS ====================
class TestOwners:
    def test_create_owner_full(self, client, owner_data):
        res = client.post("/owners/", json=owner_data)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["name"] == owner_data["name"]

    def test_create_owner_min_required(self, client, owner_min_data):
        res = client.post("/owners/", json=owner_min_data)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["age"] is None

    def test_create_owner_missing_name(self, client):
        res = client.post("/owners/", json={"age": 25})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_read_owners(self, client, owner_data):
        client.post("/owners/", json=owner_data)
        res = client.get("/owners/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.json()) >= 1

    def test_lookup_owner_by_phone(self, client, owner_data):
        client.post("/owners/", json=owner_data)
        res = client.get("/owners/lookup", params={"phone": "+79001234567"})
        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["owner"]["phone"] == "+79001234567"
        assert body["dogs"] == []
        assert body["participations"] == []
        assert "visit_records" in body
        assert "dog_embeddings" in body
        assert body["dog_embeddings"] == []

    def test_lookup_owner_phone_digits_only(self, client, owner_data):
        client.post("/owners/", json=owner_data)
        res = client.get("/owners/lookup", params={"phone": "79001234567"})
        assert res.status_code == status.HTTP_200_OK

    def test_lookup_owner_not_found(self, client):
        res = client.get("/owners/lookup", params={"phone": "+79999999999"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_lookup_owner_missing_phone(self, client):
        res = client.get("/owners/lookup", params={"phone": ""})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_read_owner_404(self, client):
        res = client.get("/owners/999")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_update_owner(self, client, owner_data):
        created = client.post("/owners/", json=owner_data).json()
        res = client.patch(f"/owners/{created['id']}", json={"name": "Обновлено"})
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["name"] == "Обновлено"

    def test_delete_owner(self, client, owner_data):
        created = client.post("/owners/", json=owner_data).json()
        res = client.delete(f"/owners/{created['id']}")
        assert res.status_code == status.HTTP_204_NO_CONTENT

# ==================== DOGS ====================
class TestDogs:
    def _create_deps(self, client):
        owner = client.post("/owners/", json={"name": "Owner"}).json()
        breed = client.post("/breeds/", json={"name": "Breed"}).json()
        return owner, breed

    def test_create_dog_success(self, client):
        owner, breed = self._create_deps(client)
        dog_data = {"name": "Бобик", "breed_id": breed["id"], "owner_id": owner["id"]}
        res = client.post("/dogs/", json=dog_data)
        assert res.status_code == status.HTTP_201_CREATED

    def test_create_dog_min_required(self, client):
        owner, breed = self._create_deps(client)
        dog_data = {"name": "Рекс", "breed_id": breed["id"], "owner_id": owner["id"]}
        res = client.post("/dogs/", json=dog_data)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["age"] is None

    def test_dog_embedding_upsert_and_read(self, client):
        import math

        owner, breed = self._create_deps(client)
        dog = client.post("/dogs/", json={"name": "CamDog", "breed_id": breed["id"], "owner_id": owner["id"]}).json()
        dim = 2048
        vec = [1.0 / math.sqrt(dim)] * dim
        res = client.put(
            f"/dogs/{dog['id']}/embedding",
            json={"mean_vector": vec},
        )
        assert res.status_code == 200
        j = res.json()
        assert j["dog_id"] == dog["id"]
        assert j["embedding_dim"] == dim
        r2 = client.get(f"/dogs/{dog['id']}/embedding")
        assert r2.status_code == 200

    def test_dog_embedding_catalog(self, client):
        import math

        owner, breed = self._create_deps(client)
        dog = client.post("/dogs/", json={"name": "Catalog Dog", "breed_id": breed["id"], "owner_id": owner["id"]}).json()
        dim = 8
        vec = [1.0 / math.sqrt(dim)] * dim
        client.put(
            f"/dogs/{dog['id']}/embedding",
            json={"mean_vector": vec},
        )
        res = client.get("/dog-embeddings/")
        assert res.status_code == status.HTTP_200_OK
        rows = res.json()
        assert any(item["dog_id"] == dog["id"] and item["dog_name"] == "Catalog Dog" for item in rows)

    def test_lookup_includes_dog_embeddings(self, client):
        import math

        owner = client.post("/owners/", json={"name": "CamOwner", "phone": "+79001112233"}).json()
        breed = client.post("/breeds/", json={"name": "CamBreed"}).json()
        dog = client.post(
            "/dogs/", json={"name": "X", "breed_id": breed["id"], "owner_id": owner["id"]}
        ).json()
        dim = 2048
        vec = [1.0 / math.sqrt(dim)] * dim
        client.put(
            f"/dogs/{dog['id']}/embedding",
            json={"mean_vector": vec},
        )
        res = client.get("/owners/lookup", params={"phone": "+79001112233"})
        assert res.status_code == 200
        idents = res.json()["dog_embeddings"]
        assert len(idents) == 1
        assert idents[0]["dog_id"] == dog["id"]
        assert idents[0]["embedding"]["embedding_dim"] == dim

    def test_create_dog_missing_required(self, client):
        res = client.post("/dogs/", json={"name": "Бобик"})  # нет breed_id, owner_id
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_dog_invalid_owner(self, client):
        _, breed = self._create_deps(client)
        res = client.post("/dogs/", json={"name": "X", "breed_id": breed["id"], "owner_id": 999})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_read_dogs(self, client):
        self._create_deps(client)
        owners = client.get("/owners/").json()
        breeds = client.get("/breeds/").json()
        client.post(
            "/dogs/",
            json={"name": "T", "breed_id": breeds[0]["id"], "owner_id": owners[0]["id"]},
        )
        res = client.get("/dogs/")
        assert res.status_code == status.HTTP_200_OK

# ==================== EMPLOYEES ====================
class TestEmployees:
    def test_create_employee_success(self, client, role_data, employee_data):
        client.post("/roles/", json=role_data)
        res = client.post("/employees/", json=employee_data)
        assert res.status_code == status.HTTP_201_CREATED

    def test_create_employee_min_required(self, client, role_data, employee_min_data):
        client.post("/roles/", json=role_data)
        res = client.post("/employees/", json=employee_min_data)
        assert res.status_code == status.HTTP_201_CREATED

    def test_create_employee_missing_role(self, client, employee_min_data):
        del employee_min_data["role_id"]
        res = client.post("/employees/", json=employee_min_data)
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_employee_invalid_role(self, client, employee_data):
        res = client.post("/employees/", json={**employee_data, "role_id": 999})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

# ==================== EVENTS ====================
class TestEvents:
    def _setup_manager(self, client):
        client.post("/roles/", json={"name": "R"})
        emp = client.post("/employees/", json={"name": "M", "role_id": 1}).json()
        return emp["id"]

    def test_create_event_success(self, client, event_data):
        manager_id = self._setup_manager(client)
        event_data["manager_id"] = manager_id
        res = client.post("/events/", json=event_data)
        assert res.status_code == status.HTTP_201_CREATED

    def test_create_event_min_required(self, client, event_min_data):
        manager_id = self._setup_manager(client)
        event_min_data["manager_id"] = manager_id
        res = client.post("/events/", json=event_min_data)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["duration_min"] is None

    def test_create_event_missing_required(self, client):
        res = client.post("/events/", json={"name": "Test"})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_invalid_manager(self, client, event_data):
        event_data["manager_id"] = 999
        res = client.post("/events/", json=event_data)
        assert res.status_code == status.HTTP_400_BAD_REQUEST


class TestParticipationAndVisits:
    def test_update_participation(self, client):
        owner1 = client.post("/owners/", json={"name": "Owner 1"}).json()
        owner2 = client.post("/owners/", json={"name": "Owner 2"}).json()
        client.post("/roles/", json={"name": "Manager"})
        emp = client.post("/employees/", json={"name": "Emp", "role_id": 1}).json()
        event = client.post("/events/", json={"name": "Event", "manager_id": emp["id"], "visitor_amount": 1}).json()
        sched = client.post("/schedules/", json={"event_id": event["id"], "time_start": "2026-01-01T10:00:00"}).json()
        part = client.post(
            "/participations/",
            json={"scheduled_event_id": sched["id"], "visitor_id": owner1["id"]},
        ).json()

        res = client.patch(f"/participations/{part['id']}", json={"visitor_id": owner2["id"]})
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["visitor_id"] == owner2["id"]

    def test_update_visit_record(self, client):
        owner = client.post("/owners/", json={"name": "Visit Owner"}).json()
        breed = client.post("/breeds/", json={"name": "Visit Breed"}).json()
        dog = client.post("/dogs/", json={"name": "Visit Dog", "breed_id": breed["id"], "owner_id": owner["id"]}).json()
        svc1 = client.post("/services/", json={"name": "Svc 1"}).json()
        svc2 = client.post("/services/", json={"name": "Svc 2"}).json()
        visit = client.post(
            "/visit-records/",
            json={
                "dog_id": dog["id"],
                "service_id": svc1["id"],
                "visited_at": "2026-01-02T11:00:00",
                "amount_rub": 1000,
            },
        ).json()

        res = client.patch(
            f"/visit-records/{visit['id']}",
            json={"service_id": svc2["id"], "amount_rub": 1500},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["service_id"] == svc2["id"]
        assert res.json()["amount_rub"] == 1500


class TestDogActivityPeriods:
    def test_create_update_and_filter_activity_period(self, client):
        owner = client.post("/owners/", json={"name": "Activity Owner"}).json()
        breed = client.post("/breeds/", json={"name": "Activity Breed"}).json()
        dog = client.post(
            "/dogs/",
            json={"name": "Activity Dog", "breed_id": breed["id"], "owner_id": owner["id"]},
        ).json()

        created = client.post(
            "/dog-activity-periods/",
            json={
                "dog_id": dog["id"],
                "activity_level": "active",
                "started_at": "2026-01-03T10:00:00",
                "avg_speed": 1.25,
                "peak_speed": 2.4,
                "sample_count": 15,
                "camera_index": 0,
            },
        )
        assert created.status_code == status.HTTP_201_CREATED
        period = created.json()
        assert period["activity_level"] == "active"
        assert period["ended_at"] is None

        open_rows = client.get("/dog-activity-periods/", params={"dog_id": dog["id"], "open_only": "true"})
        assert open_rows.status_code == status.HTTP_200_OK
        assert len(open_rows.json()) == 1

        updated = client.patch(
            f"/dog-activity-periods/{period['id']}",
            json={
                "activity_level": "moderate",
                "ended_at": "2026-01-03T10:05:00",
                "sample_count": 22,
            },
        )
        assert updated.status_code == status.HTTP_200_OK
        body = updated.json()
        assert body["activity_level"] == "moderate"
        assert body["sample_count"] == 22
        assert body["ended_at"] == "2026-01-03T10:05:00"

        closed_rows = client.get("/dog-activity-periods/", params={"dog_id": dog["id"], "activity_level": "moderate"})
        assert closed_rows.status_code == status.HTTP_200_OK
        assert len(closed_rows.json()) == 1
