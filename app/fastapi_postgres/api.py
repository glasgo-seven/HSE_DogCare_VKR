from contextlib import asynccontextmanager
import json
import os

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import text

from typing import List, Optional, Any

# from api import get_session, router_dogs
from models import (
	Owner,
	OwnerCreate,
	OwnerUpdate,
	DogCreate,
	Dog,
	DogRead,
	DogUpdate,
	DogEmbedding,
	DogEmbeddingUpsert,
	DogEmbeddingRead,
	DogEmbeddingCatalogItem,
	DogActivityPeriod,
	DogActivityPeriodCreate,
	DogActivityPeriodUpdate,
	Breed,
	BreedCreate,
	BreedUpdate,
	Role,
	RoleCreate,
	RoleUpdate,
	Employee,
	EmployeeCreate,
	EmployeeRead,
	EmployeeUpdate,
	Event,
	EventCreate,
	EventReadFull,
	EventUpdate,
	Schedule,
	ScheduleCreate,
	ScheduleUpdate,
	Participation,
	ParticipationCreate,
	ParticipationUpdate,
	Service,
	ServiceCreate,
	ServiceUpdate,
	VisitRecord,
	VisitRecordCreate,
	VisitRecordUpdate,
	Token,
	User,
	UserRegister,
)

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm



# --- 1. CONFIG & DB SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL == '' or not DATABASE_URL:
	DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/animal_care_db'

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
	SQLModel.metadata.create_all(engine)


def migrate_schema():
	"""Добавление колонок к существующей БД (create_all их не обновляет)."""
	with engine.begin() as conn:
		try:
			conn.execute(text("ALTER TABLE dog ADD COLUMN photo_url VARCHAR(512)"))
		except Exception:
			pass
		try:
			conn.execute(text("DROP TABLE IF EXISTS dog_camera_profile"))
		except Exception:
			pass

# Зависимость для получения сессии БД
def get_session():
	with Session(engine) as session:
		yield session


def dog_to_read(session: Session, d: Dog) -> DogRead:
	b = session.get(Breed, d.breed_id)
	o = session.get(Owner, d.owner_id)
	return DogRead(
		id=d.id,
		name=d.name,
		age=d.age,
		gender=d.gender,
		breed_id=d.breed_id,
		breed=b.name if b else "?",
		owner_id=d.owner_id,
		owner=o.name if o else "?",
		photo_url=d.photo_url,
		created_at=d.created_at,
	)


def _dog_embedding_to_read(p: DogEmbedding) -> DogEmbeddingRead:
	arr = json.loads(p.mean_vector)
	return DogEmbeddingRead(
		dog_id=p.dog_id,
		embedding_dim=len(arr),
		created_at=p.created_at,
	)


def _dog_embedding_to_catalog_item(session: Session, p: DogEmbedding) -> DogEmbeddingCatalogItem:
	dog = session.get(Dog, p.dog_id)
	return DogEmbeddingCatalogItem(
		dog_id=p.dog_id,
		dog_name=dog.name if dog else f"dog_{p.dog_id}",
		mean_vector=json.loads(p.mean_vector),
		created_at=p.created_at,
	)


def employee_to_read(session: Session, e: Employee) -> EmployeeRead:
	r = session.get(Role, e.role_id)
	return EmployeeRead(
		id=e.id,
		name=e.name,
		role_id=e.role_id,
		role=r.name if r else "?",
		age=e.age,
		gender=e.gender,
		email=e.email,
		phone=e.phone,
		created_at=e.created_at,
	)


def event_to_read_full(session: Session, ev: Event) -> EventReadFull:
	manager = session.get(Employee, ev.manager_id)
	scheds = session.exec(select(Schedule).where(Schedule.event_id == ev.id)).all()
	time_start = min((s.time_start for s in scheds), default=None)
	names: list[str] = []
	seen: set[int] = set()
	for s in scheds:
		parts = session.exec(select(Participation).where(Participation.scheduled_event_id == s.id)).all()
		for p in parts:
			if p.visitor_id in seen:
				continue
			owner = session.get(Owner, p.visitor_id)
			if owner:
				names.append(owner.name)
				seen.add(p.visitor_id)
	return EventReadFull(
		id=ev.id,
		name=ev.name,
		manager_id=ev.manager_id,
		manager_name=manager.name if manager else "?",
		duration_min=ev.duration_min,
		visitor_amount=ev.visitor_amount,
		created_at=ev.created_at,
		time_start=time_start,
		participants=", ".join(names) if names else None,
	)


# --- 4. ROUTERS (Endpoints) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
	create_db_and_tables()
	migrate_schema()
	yield

app = FastAPI(title="PetCare API", version="1.0", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.post("/owners/", response_model=Owner, status_code=201)
def create_owner(owner: OwnerCreate, session: Session = Depends(get_session)):
	if owner.email:
		existing = session.exec(select(Owner).where(Owner.email == owner.email)).first()
		if existing:
			raise HTTPException(status_code=400, detail="Email already registered")
	
	db_owner = Owner.model_validate(owner)
	session.add(db_owner)
	session.commit()
	session.refresh(db_owner)
	return db_owner

@app.get("/owners/", response_model=List[Owner])
def read_owners(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
	owners = session.exec(select(Owner).offset(skip).limit(limit)).all()
	return owners


def _normalize_phone(raw: Optional[str]) -> str:
	if not raw:
		return ""
	return "".join(ch for ch in raw if ch.isdigit())


def _phones_match(stored: Optional[str], query: str) -> bool:
	na = _normalize_phone(stored)
	nb = _normalize_phone(query)
	if not na or not nb:
		return False
	if na == nb:
		return True
	if len(na) >= 10 and len(nb) >= 10 and na[-10:] == nb[-10:]:
		return True
	return False


@app.get("/owners/lookup")
def lookup_owner_by_phone(phone: str, session: Session = Depends(get_session)):
	"""Полная карточка: владелец, собаки, участия в событиях (по номеру телефона)."""
	q = phone.strip() if phone else ""
	if not q:
		raise HTTPException(status_code=400, detail="Укажите phone")
	owners = session.exec(select(Owner)).all()
	owner = next((o for o in owners if _phones_match(o.phone, q)), None)
	if not owner:
		raise HTTPException(status_code=404, detail="Владелец с таким номером не найден")
	dogs = session.exec(select(Dog).where(Dog.owner_id == owner.id)).all()
	dog_reads = [dog_to_read(session, d) for d in dogs]
	visit_rows: list[dict[str, Any]] = []
	for d in dogs:
		if d.id is None:
			continue
		for v in session.exec(select(VisitRecord).where(VisitRecord.dog_id == d.id)).all():
			svc = session.get(Service, v.service_id)
			visit_rows.append(
				{
					"id": v.id,
					"dog_id": v.dog_id,
					"dog_name": d.name,
					"service_name": svc.name if svc else None,
					"visited_at": v.visited_at.isoformat() if v.visited_at else None,
					"amount_rub": v.amount_rub,
				}
			)
	parts = session.exec(select(Participation).where(Participation.visitor_id == owner.id)).all()
	participations_out: list[dict[str, Any]] = []
	for p in parts:
		sched = session.get(Schedule, p.scheduled_event_id)
		ev = session.get(Event, sched.event_id) if sched else None
		participations_out.append(
			{
				"id": p.id,
				"scheduled_event_id": p.scheduled_event_id,
				"visitor_id": p.visitor_id,
				"created_at": p.created_at.isoformat() if p.created_at else None,
				"event_name": ev.name if ev else None,
				"time_start": sched.time_start.isoformat() if sched and sched.time_start else None,
			}
		)
	dog_embeddings: list[dict[str, Any]] = []
	for d in dogs:
		if d.id is None:
			continue
		row = session.exec(select(DogEmbedding).where(DogEmbedding.dog_id == d.id)).first()
		if row:
			dim = len(json.loads(row.mean_vector))
			dog_embeddings.append(
				{
					"dog_id": d.id,
					"embedding": {
						"embedding_dim": dim,
						"created_at": row.created_at.isoformat() if row.created_at else None,
					},
				}
			)
		else:
			dog_embeddings.append({"dog_id": d.id, "embedding": None})
	return {
		"owner": {
			"id": owner.id,
			"name": owner.name,
			"age": owner.age,
			"gender": owner.gender,
			"email": owner.email,
			"phone": owner.phone,
			"region": owner.region,
			"created_at": owner.created_at.isoformat() if owner.created_at else None,
		},
		"dogs": [d.model_dump(mode="json") for d in dog_reads],
		"dog_embeddings": dog_embeddings,
		"participations": participations_out,
		"visit_records": visit_rows,
	}


@app.get("/owners/{owner_id}", response_model=Owner)
def read_owner(owner_id: int, session: Session = Depends(get_session)):
	owner = session.get(Owner, owner_id)
	if not owner:
		raise HTTPException(status_code=404, detail="Owner not found")
	return owner

@app.patch("/owners/{owner_id}", response_model=Owner)
def update_owner(owner_id: int, owner_update: OwnerUpdate, session: Session = Depends(get_session)):
	db_owner = session.get(Owner, owner_id)
	if not db_owner:
		raise HTTPException(status_code=404, detail="Owner not found")
	
	update_data = owner_update.model_dump(exclude_unset=True)
	for field, value in update_data.items():
		setattr(db_owner, field, value)
	
	session.commit()
	session.refresh(db_owner)
	return db_owner

@app.delete("/owners/{owner_id}", status_code=204)
def delete_owner(owner_id: int, session: Session = Depends(get_session)):
	owner = session.get(Owner, owner_id)
	if not owner:
		raise HTTPException(status_code=404, detail="Owner not found")
	session.delete(owner)
	session.commit()
	return None


# --- Dogs Endpoints ---
@app.post("/dogs/", response_model=DogRead, status_code=201)
def create_dog(dog: DogCreate, session: Session = Depends(get_session)):
	owner = session.get(Owner, dog.owner_id)
	if not owner:
		raise HTTPException(status_code=400, detail=f"Owner with id={dog.owner_id} not found")
	
	breed = session.get(Breed, dog.breed_id)
	if not breed:
		raise HTTPException(status_code=400, detail=f"Breed with id={dog.breed_id} not found")
	
	db_dog = Dog.model_validate(dog)
	session.add(db_dog)
	session.commit()
	session.refresh(db_dog)
	return dog_to_read(session, db_dog)

@app.get("/dogs/", response_model=List[DogRead])
def read_dogs(
	skip: int = 0, 
	limit: int = 100, 
	owner_id: Optional[int] = None,
	session: Session = Depends(get_session)
):
	query = select(Dog)
	if owner_id:
		query = query.where(Dog.owner_id == owner_id)
	dogs = session.exec(query.offset(skip).limit(limit)).all()
	return [dog_to_read(session, d) for d in dogs]

@app.get("/dogs/{dog_id}", response_model=DogRead)
def read_dog(dog_id: int, session: Session = Depends(get_session)):
	dog = session.get(Dog, dog_id)
	if not dog:
		raise HTTPException(status_code=404, detail="Dog not found")
	return dog_to_read(session, dog)

@app.patch("/dogs/{dog_id}", response_model=DogRead)
def update_dog(dog_id: int, dog_update: DogUpdate, session: Session = Depends(get_session)):
	db_dog = session.get(Dog, dog_id)
	if not db_dog:
		raise HTTPException(status_code=404, detail="Dog not found")
	update_data = dog_update.model_dump(exclude_unset=True)
	if "owner_id" in update_data:
		if not session.get(Owner, update_data["owner_id"]):
			raise HTTPException(status_code=400, detail=f"Owner with id={update_data['owner_id']} not found")
	if "breed_id" in update_data:
		if not session.get(Breed, update_data["breed_id"]):
			raise HTTPException(status_code=400, detail=f"Breed with id={update_data['breed_id']} not found")
	for field, value in update_data.items():
		setattr(db_dog, field, value)
	session.commit()
	session.refresh(db_dog)
	return dog_to_read(session, db_dog)


@app.put("/dogs/{dog_id}/embedding", response_model=DogEmbeddingRead)
def upsert_dog_embedding(
	dog_id: int,
	body: DogEmbeddingUpsert,
	session: Session = Depends(get_session),
):
	"""Сохранить mean_vector в dog_embeddings (результат create_dogid и нормализации)."""
	if not session.get(Dog, dog_id):
		raise HTTPException(status_code=404, detail="Dog not found")
	vec_json = json.dumps(body.mean_vector)
	now = datetime.now()
	existing = session.exec(select(DogEmbedding).where(DogEmbedding.dog_id == dog_id)).first()
	if existing:
		existing.mean_vector = vec_json
		db = existing
	else:
		db = DogEmbedding(
			dog_id=dog_id,
			mean_vector=vec_json,
			created_at=now,
		)
		session.add(db)
	session.commit()
	session.refresh(db)
	return _dog_embedding_to_read(db)


@app.get("/dogs/{dog_id}/embedding", response_model=DogEmbeddingRead)
def read_dog_embedding(dog_id: int, session: Session = Depends(get_session)):
	row = session.exec(select(DogEmbedding).where(DogEmbedding.dog_id == dog_id)).first()
	if not row:
		raise HTTPException(status_code=404, detail="Dog embedding not found")
	return _dog_embedding_to_read(row)


@app.get("/dog-embeddings/", response_model=List[DogEmbeddingCatalogItem])
def read_dog_embeddings_catalog(
	skip: int = 0,
	limit: int = 500,
	session: Session = Depends(get_session),
):
	rows = session.exec(select(DogEmbedding).offset(skip).limit(limit)).all()
	return [_dog_embedding_to_catalog_item(session, row) for row in rows]


@app.delete("/dogs/{dog_id}", status_code=204)
def delete_dog(dog_id: int, session: Session = Depends(get_session)):
	dog = session.get(Dog, dog_id)
	if not dog:
		raise HTTPException(status_code=404, detail="Dog not found")
	emb = session.exec(select(DogEmbedding).where(DogEmbedding.dog_id == dog_id)).first()
	if emb:
		session.delete(emb)
	session.delete(dog)
	session.commit()
	return None


# --- Breeds ---
@app.post("/breeds/", response_model=Breed, status_code=201)
def create_breed(breed: BreedCreate, session: Session = Depends(get_session)):
	db = Breed.model_validate(breed)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/breeds/", response_model=List[Breed])
def read_breeds(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
	return session.exec(select(Breed).offset(skip).limit(limit)).all()


@app.get("/breeds/{breed_id}", response_model=Breed)
def read_breed(breed_id: int, session: Session = Depends(get_session)):
	b = session.get(Breed, breed_id)
	if not b:
		raise HTTPException(status_code=404, detail="Breed not found")
	return b


@app.patch("/breeds/{breed_id}", response_model=Breed)
def update_breed(breed_id: int, body: BreedUpdate, session: Session = Depends(get_session)):
	db = session.get(Breed, breed_id)
	if not db:
		raise HTTPException(status_code=404, detail="Breed not found")
	for k, v in body.model_dump(exclude_unset=True).items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/breeds/{breed_id}", status_code=204)
def delete_breed(breed_id: int, session: Session = Depends(get_session)):
	db = session.get(Breed, breed_id)
	if not db:
		raise HTTPException(status_code=404, detail="Breed not found")
	session.delete(db)
	session.commit()
	return None


# --- Roles ---
@app.post("/roles/", response_model=Role, status_code=201)
def create_role(role: RoleCreate, session: Session = Depends(get_session)):
	db = Role.model_validate(role)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/roles/", response_model=List[Role])
def read_roles(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
	return session.exec(select(Role).offset(skip).limit(limit)).all()


@app.get("/roles/{role_id}", response_model=Role)
def read_role(role_id: int, session: Session = Depends(get_session)):
	r = session.get(Role, role_id)
	if not r:
		raise HTTPException(status_code=404, detail="Role not found")
	return r


@app.patch("/roles/{role_id}", response_model=Role)
def update_role(role_id: int, body: RoleUpdate, session: Session = Depends(get_session)):
	db = session.get(Role, role_id)
	if not db:
		raise HTTPException(status_code=404, detail="Role not found")
	for k, v in body.model_dump(exclude_unset=True).items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: int, session: Session = Depends(get_session)):
	db = session.get(Role, role_id)
	if not db:
		raise HTTPException(status_code=404, detail="Role not found")
	session.delete(db)
	session.commit()
	return None


# --- Employees Endpoints ---
@app.post("/employees/", response_model=Employee, status_code=201)
def create_employee(employee: EmployeeCreate, session: Session = Depends(get_session)):
	# Проверка email
	if employee.email:
		existing = session.exec(select(Employee).where(Employee.email == employee.email)).first()
		if existing:
			raise HTTPException(status_code=400, detail="Email already registered")
	
	# Проверка роли
	role = session.get(Role, employee.role_id)
	if not role:
		raise HTTPException(status_code=400, detail=f"Role with id={employee.role_id} not found")
	
	db_employee = Employee.model_validate(employee)
	session.add(db_employee)
	session.commit()
	session.refresh(db_employee)
	return employee_to_read(session, db_employee)

@app.get("/employees/", response_model=List[EmployeeRead])
def read_employees(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
	emps = session.exec(select(Employee).offset(skip).limit(limit)).all()
	return [employee_to_read(session, e) for e in emps]


@app.get("/employees/{employee_id}", response_model=EmployeeRead)
def read_employee(employee_id: int, session: Session = Depends(get_session)):
	emp = session.get(Employee, employee_id)
	if not emp:
		raise HTTPException(status_code=404, detail="Employee not found")
	return employee_to_read(session, emp)


@app.patch("/employees/{employee_id}", response_model=EmployeeRead)
def update_employee(employee_id: int, body: EmployeeUpdate, session: Session = Depends(get_session)):
	db = session.get(Employee, employee_id)
	if not db:
		raise HTTPException(status_code=404, detail="Employee not found")
	data = body.model_dump(exclude_unset=True)
	if "role_id" in data and not session.get(Role, data["role_id"]):
		raise HTTPException(status_code=400, detail=f"Role with id={data['role_id']} not found")
	if "email" in data and data["email"]:
		existing = session.exec(select(Employee).where(Employee.email == data["email"], Employee.id != employee_id)).first()
		if existing:
			raise HTTPException(status_code=400, detail="Email already registered")
	for k, v in data.items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return employee_to_read(session, db)


@app.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, session: Session = Depends(get_session)):
	db = session.get(Employee, employee_id)
	if not db:
		raise HTTPException(status_code=404, detail="Employee not found")
	session.delete(db)
	session.commit()
	return None


# --- Events Endpoints ---
@app.post("/events/", response_model=Event, status_code=201)
def create_event(event: EventCreate, session: Session = Depends(get_session)):
	# Проверка менеджера
	manager = session.get(Employee, event.manager_id)
	if not manager:
		raise HTTPException(status_code=400, detail=f"Employee with id={event.manager_id} not found")
	
	db_event = Event.model_validate(event)
	session.add(db_event)
	session.commit()
	session.refresh(db_event)
	return event_to_read_full(session, db_event)

@app.get("/events/", response_model=List[EventReadFull])
def read_events(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
	evs = session.exec(select(Event).offset(skip).limit(limit)).all()
	return [event_to_read_full(session, ev) for ev in evs]


@app.get("/events/{event_id}", response_model=EventReadFull)
def read_event(event_id: int, session: Session = Depends(get_session)):
	ev = session.get(Event, event_id)
	if not ev:
		raise HTTPException(status_code=404, detail="Event not found")
	return event_to_read_full(session, ev)


@app.patch("/events/{event_id}", response_model=EventReadFull)
def update_event(event_id: int, body: EventUpdate, session: Session = Depends(get_session)):
	db = session.get(Event, event_id)
	if not db:
		raise HTTPException(status_code=404, detail="Event not found")
	data = body.model_dump(exclude_unset=True)
	if "manager_id" in data and not session.get(Employee, data["manager_id"]):
		raise HTTPException(status_code=400, detail=f"Employee with id={data['manager_id']} not found")
	for k, v in data.items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return event_to_read_full(session, db)


@app.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, session: Session = Depends(get_session)):
	db = session.get(Event, event_id)
	if not db:
		raise HTTPException(status_code=404, detail="Event not found")
	session.delete(db)
	session.commit()
	return None


# --- Schedules ---
@app.post("/schedules/", response_model=Schedule, status_code=201)
def create_schedule(item: ScheduleCreate, session: Session = Depends(get_session)):
	if not session.get(Event, item.event_id):
		raise HTTPException(status_code=400, detail=f"Event with id={item.event_id} not found")
	db = Schedule.model_validate(item)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/schedules/", response_model=List[Schedule])
def read_schedules(
	skip: int = 0,
	limit: int = 100,
	event_id: Optional[int] = None,
	session: Session = Depends(get_session),
):
	q = select(Schedule)
	if event_id is not None:
		q = q.where(Schedule.event_id == event_id)
	return session.exec(q.offset(skip).limit(limit)).all()


@app.get("/schedules/{schedule_id}", response_model=Schedule)
def read_schedule(schedule_id: int, session: Session = Depends(get_session)):
	s = session.get(Schedule, schedule_id)
	if not s:
		raise HTTPException(status_code=404, detail="Schedule not found")
	return s


@app.patch("/schedules/{schedule_id}", response_model=Schedule)
def update_schedule(schedule_id: int, body: ScheduleUpdate, session: Session = Depends(get_session)):
	db = session.get(Schedule, schedule_id)
	if not db:
		raise HTTPException(status_code=404, detail="Schedule not found")
	data = body.model_dump(exclude_unset=True)
	if "event_id" in data and not session.get(Event, data["event_id"]):
		raise HTTPException(status_code=400, detail=f"Event with id={data['event_id']} not found")
	for k, v in data.items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, session: Session = Depends(get_session)):
	db = session.get(Schedule, schedule_id)
	if not db:
		raise HTTPException(status_code=404, detail="Schedule not found")
	session.delete(db)
	session.commit()
	return None


# --- Participations ---
@app.post("/participations/", response_model=Participation, status_code=201)
def create_participation(item: ParticipationCreate, session: Session = Depends(get_session)):
	if not session.get(Schedule, item.scheduled_event_id):
		raise HTTPException(status_code=400, detail=f"Schedule with id={item.scheduled_event_id} not found")
	if not session.get(Owner, item.visitor_id):
		raise HTTPException(status_code=400, detail=f"Owner with id={item.visitor_id} not found")
	db = Participation.model_validate(item)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/participations/", response_model=List[Participation])
def read_participations(
	skip: int = 0,
	limit: int = 100,
	visitor_id: Optional[int] = None,
	session: Session = Depends(get_session),
):
	q = select(Participation)
	if visitor_id is not None:
		q = q.where(Participation.visitor_id == visitor_id)
	return session.exec(q.offset(skip).limit(limit)).all()


@app.get("/participations/{participation_id}", response_model=Participation)
def read_participation(participation_id: int, session: Session = Depends(get_session)):
	p = session.get(Participation, participation_id)
	if not p:
		raise HTTPException(status_code=404, detail="Participation not found")
	return p


@app.patch("/participations/{participation_id}", response_model=Participation)
def update_participation(participation_id: int, body: ParticipationUpdate, session: Session = Depends(get_session)):
	db = session.get(Participation, participation_id)
	if not db:
		raise HTTPException(status_code=404, detail="Participation not found")
	data = body.model_dump(exclude_unset=True)
	if "scheduled_event_id" in data and not session.get(Schedule, data["scheduled_event_id"]):
		raise HTTPException(status_code=400, detail=f"Schedule with id={data['scheduled_event_id']} not found")
	if "visitor_id" in data and not session.get(Owner, data["visitor_id"]):
		raise HTTPException(status_code=400, detail=f"Owner with id={data['visitor_id']} not found")
	for k, v in data.items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/participations/{participation_id}", status_code=204)
def delete_participation(participation_id: int, session: Session = Depends(get_session)):
	db = session.get(Participation, participation_id)
	if not db:
		raise HTTPException(status_code=404, detail="Participation not found")
	session.delete(db)
	session.commit()
	return None


def _season_from_month(month: int) -> str:
	if month in (12, 1, 2):
		return "winter"
	if month in (3, 4, 5):
		return "spring"
	if month in (6, 7, 8):
		return "summer"
	return "autumn"


def _dog_age_bucket_years(age_years: Optional[int]) -> str:
	if age_years is None:
		return "unknown"
	if age_years <= 1:
		return "0-1y"
	if age_years <= 4:
		return "2-4y"
	if age_years <= 8:
		return "5-8y"
	return "9+y"


# --- Services & visit records (аналитика) ---
@app.post("/services/", response_model=Service, status_code=201)
def create_service(body: ServiceCreate, session: Session = Depends(get_session)):
	db = Service(name=body.name, category=body.category)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/services/", response_model=List[Service])
def read_services(skip: int = 0, limit: int = 200, session: Session = Depends(get_session)):
	return session.exec(select(Service).offset(skip).limit(limit)).all()


@app.get("/services/{service_id}", response_model=Service)
def read_service(service_id: int, session: Session = Depends(get_session)):
	s = session.get(Service, service_id)
	if not s:
		raise HTTPException(status_code=404, detail="Service not found")
	return s


@app.patch("/services/{service_id}", response_model=Service)
def update_service(service_id: int, body: ServiceUpdate, session: Session = Depends(get_session)):
	db = session.get(Service, service_id)
	if not db:
		raise HTTPException(status_code=404, detail="Service not found")
	for k, v in body.model_dump(exclude_unset=True).items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: int, session: Session = Depends(get_session)):
	db = session.get(Service, service_id)
	if not db:
		raise HTTPException(status_code=404, detail="Service not found")
	session.delete(db)
	session.commit()
	return None


@app.post("/visit-records/", response_model=VisitRecord, status_code=201)
def create_visit_record(body: VisitRecordCreate, session: Session = Depends(get_session)):
	if not session.get(Dog, body.dog_id):
		raise HTTPException(status_code=400, detail="Dog not found")
	if not session.get(Service, body.service_id):
		raise HTTPException(status_code=400, detail="Service not found")
	db = VisitRecord(
		dog_id=body.dog_id,
		service_id=body.service_id,
		visited_at=body.visited_at,
		amount_rub=body.amount_rub,
	)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/visit-records/", response_model=List[VisitRecord])
def read_visit_records(
	skip: int = 0,
	limit: int = 500,
	dog_id: Optional[int] = None,
	session: Session = Depends(get_session),
):
	q = select(VisitRecord)
	if dog_id is not None:
		q = q.where(VisitRecord.dog_id == dog_id)
	return session.exec(q.offset(skip).limit(limit)).all()


@app.get("/visit-records/{visit_id}", response_model=VisitRecord)
def read_visit_record(visit_id: int, session: Session = Depends(get_session)):
	v = session.get(VisitRecord, visit_id)
	if not v:
		raise HTTPException(status_code=404, detail="Visit not found")
	return v


@app.patch("/visit-records/{visit_id}", response_model=VisitRecord)
def update_visit_record(visit_id: int, body: VisitRecordUpdate, session: Session = Depends(get_session)):
	db = session.get(VisitRecord, visit_id)
	if not db:
		raise HTTPException(status_code=404, detail="Visit not found")
	data = body.model_dump(exclude_unset=True)
	if "dog_id" in data and not session.get(Dog, data["dog_id"]):
		raise HTTPException(status_code=400, detail="Dog not found")
	if "service_id" in data and not session.get(Service, data["service_id"]):
		raise HTTPException(status_code=400, detail="Service not found")
	for k, v in data.items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/visit-records/{visit_id}", status_code=204)
def delete_visit_record(visit_id: int, session: Session = Depends(get_session)):
	db = session.get(VisitRecord, visit_id)
	if not db:
		raise HTTPException(status_code=404, detail="Visit not found")
	session.delete(db)
	session.commit()
	return None


@app.post("/dog-activity-periods/", response_model=DogActivityPeriod, status_code=201)
def create_dog_activity_period(body: DogActivityPeriodCreate, session: Session = Depends(get_session)):
	if not session.get(Dog, body.dog_id):
		raise HTTPException(status_code=400, detail="Dog not found")
	if body.ended_at is not None and body.ended_at < body.started_at:
		raise HTTPException(status_code=400, detail="ended_at must be greater than or equal to started_at")
	db = DogActivityPeriod.model_validate(body)
	session.add(db)
	session.commit()
	session.refresh(db)
	return db


@app.get("/dog-activity-periods/", response_model=List[DogActivityPeriod])
def read_dog_activity_periods(
	skip: int = 0,
	limit: int = 500,
	dog_id: Optional[int] = None,
	activity_level: Optional[str] = None,
	open_only: bool = False,
	session: Session = Depends(get_session),
):
	q = select(DogActivityPeriod)
	if dog_id is not None:
		q = q.where(DogActivityPeriod.dog_id == dog_id)
	if activity_level:
		q = q.where(DogActivityPeriod.activity_level == activity_level)
	if open_only:
		q = q.where(DogActivityPeriod.ended_at.is_(None))
	return session.exec(q.offset(skip).limit(limit)).all()


@app.get("/dog-activity-periods/{period_id}", response_model=DogActivityPeriod)
def read_dog_activity_period(period_id: int, session: Session = Depends(get_session)):
	row = session.get(DogActivityPeriod, period_id)
	if not row:
		raise HTTPException(status_code=404, detail="Dog activity period not found")
	return row


@app.patch("/dog-activity-periods/{period_id}", response_model=DogActivityPeriod)
def update_dog_activity_period(
	period_id: int,
	body: DogActivityPeriodUpdate,
	session: Session = Depends(get_session),
):
	db = session.get(DogActivityPeriod, period_id)
	if not db:
		raise HTTPException(status_code=404, detail="Dog activity period not found")
	data = body.model_dump(exclude_unset=True)
	started_at = data.get("started_at", db.started_at)
	ended_at = data.get("ended_at", db.ended_at)
	if ended_at is not None and started_at is not None and ended_at < started_at:
		raise HTTPException(status_code=400, detail="ended_at must be greater than or equal to started_at")
	for k, v in data.items():
		setattr(db, k, v)
	session.commit()
	session.refresh(db)
	return db


@app.delete("/dog-activity-periods/{period_id}", status_code=204)
def delete_dog_activity_period(period_id: int, session: Session = Depends(get_session)):
	db = session.get(DogActivityPeriod, period_id)
	if not db:
		raise HTTPException(status_code=404, detail="Dog activity period not found")
	session.delete(db)
	session.commit()
	return None


@app.get("/analytics/ml-dataset")
def analytics_ml_dataset(session: Session = Depends(get_session)) -> List[dict[str, Any]]:
	"""Плоские строки визитов для ML-дашбордов (порода, пол, сезон, услуга, сумма)."""
	out: list[dict[str, Any]] = []
	for v in session.exec(select(VisitRecord)).all():
		dog = session.get(Dog, v.dog_id)
		if not dog:
			continue
		breed = session.get(Breed, dog.breed_id)
		owner = session.get(Owner, dog.owner_id)
		svc = session.get(Service, v.service_id)
		if not svc:
			continue
		dt = v.visited_at
		if dt.tzinfo is None:
			month = dt.month
		else:
			month = dt.astimezone(timezone.utc).month
		age_y = dog.age
		age_months = int(age_y * 12) if age_y is not None else None
		row: dict[str, Any] = {
			"visit_id": v.id,
			"dog_id": dog.id,
			"dog_name": dog.name,
			"breed_id": breed.id if breed else None,
			"breed_name": breed.name if breed else None,
			"breed_size_group": breed.size_group if breed else None,
			"breed_coat_group": breed.coat_group if breed else None,
			"dog_age_years": age_y,
			"dog_age_months": age_months,
			"age_bucket": _dog_age_bucket_years(age_y),
			"dog_gender": dog.gender,
			"owner_id": owner.id if owner else None,
			"owner_gender": owner.gender if owner else None,
			"owner_region": owner.region if owner else None,
			"service_id": svc.id,
			"service_name": svc.name,
			"service_category": svc.category,
			"visited_at": v.visited_at.isoformat(),
			"month": month,
			"season": _season_from_month(month),
			"amount_rub": v.amount_rub,
		}
		out.append(row)
	return out


@app.get("/health")
def health():
	return {"status": "ok"}


@app.get("/analytics/summary")
def analytics_summary(session: Session = Depends(get_session)):
	return {
		"owners": len(session.exec(select(Owner)).all()),
		"dogs": len(session.exec(select(Dog)).all()),
		"employees": len(session.exec(select(Employee)).all()),
		"events": len(session.exec(select(Event)).all()),
		"breeds": len(session.exec(select(Breed)).all()),
		"roles": len(session.exec(select(Role)).all()),
		"schedules": len(session.exec(select(Schedule)).all()),
		"participations": len(session.exec(select(Participation)).all()),
		"services": len(session.exec(select(Service)).all()),
		"visit_records": len(session.exec(select(VisitRecord)).all()),
		"dog_activity_periods": len(session.exec(select(DogActivityPeriod)).all()),
	}


# Настройки безопасности
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def _normalize_password(password: str) -> str:
	return password.encode('utf-8')[:72].decode('utf-8', errors='ignore')

def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(_normalize_password(plain_password), hashed_password)

def get_password_hash(password: str) -> str:
	return pwd_context.hash(_normalize_password(password))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(timezone.utc) + expires_delta
	else:
		expire = datetime.now(timezone.utc) + timedelta(minutes=15)
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
	return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		login: str = payload.get("sub")
		if login is None:
			raise credentials_exception
	except JWTError:
		raise credentials_exception
	
	user = session.exec(select(User).where(User.login == login)).first()
	if user is None:
		raise credentials_exception
	return user


@app.post("/register", response_model=User)
def register(user_data: UserRegister, session: Session = Depends(get_session)):
	# Проверка, занят ли логин
	existing_user = session.exec(select(User).where(User.login == user_data.login)).first()
	if existing_user:
		raise HTTPException(status_code=400, detail="Login already registered")
	
	# Хеширование пароля
	hashed_pw = get_password_hash(user_data.password)
	
	db_user = User(
		login=user_data.login,
		hashed_password=hashed_pw,
		user_type=user_data.user_type
	)
	session.add(db_user)
	session.commit()
	session.refresh(db_user)
	return db_user

@app.post("/token", response_model=Token)
def login_for_access_token(
	form_data: OAuth2PasswordRequestForm = Depends(),
	session: Session = Depends(get_session),
):
	login = form_data.username
	password = form_data.password
	user = session.exec(select(User).where(User.login == login)).first()
	if not user or not verify_password(password, user.hashed_password):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Incorrect username or password",
			headers={"WWW-Authenticate": "Bearer"},
		)
	
	# Создание токена
	access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
	access_token = create_access_token(
		data={"sub": user.login}, expires_delta=access_token_expires
	)
	return {"access_token": access_token, "token_type": "bearer"}
