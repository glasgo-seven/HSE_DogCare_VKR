from typing import Optional, List
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Text

# --- 2. MODELS (SQLModel tables) ---
class Owner(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=256)
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = Field(default=None, max_length=128, unique=True)
	phone: Optional[str] = Field(default=None, max_length=16)
	region: Optional[str] = Field(default=None, max_length=128)
	created_at: datetime = Field(default_factory=datetime.now)
	
	dogs: List["Dog"] = Relationship(back_populates="owner")
	participations: List["Participation"] = Relationship(back_populates="visitor")

class Breed(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=128)
	size_group: Optional[str] = Field(default=None, max_length=64)
	coat_group: Optional[str] = Field(default=None, max_length=64)

	dogs: List["Dog"] = Relationship(back_populates="breed_ref")

class Dog(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=100)
	breed_id: int = Field(foreign_key="breed.id")
	age: Optional[int] = None
	gender: Optional[bool] = None
	owner_id: int = Field(foreign_key="owner.id")
	photo_url: Optional[str] = Field(default=None, max_length=512)
	created_at: datetime = Field(default_factory=datetime.now)

	owner: Owner = Relationship(back_populates="dogs")
	breed_ref: Breed = Relationship(back_populates="dogs")
	visit_records: List["VisitRecord"] = Relationship(back_populates="dog_ref")
	activity_periods: List["DogActivityPeriod"] = Relationship(back_populates="dog_ref")
	dog_embedding: Optional["DogEmbedding"] = Relationship(
		back_populates="dog_ref",
		sa_relationship_kwargs={"uselist": False},
	)


class DogEmbedding(SQLModel, table=True):
	__tablename__ = "dog_embeddings"

	id: Optional[int] = Field(default=None, primary_key=True)
	dog_id: int = Field(foreign_key="dog.id", unique=True, index=True)
	mean_vector: str = Field(sa_column=Column(Text))
	created_at: datetime = Field(default_factory=datetime.now)

	dog_ref: Optional["Dog"] = Relationship(back_populates="dog_embedding")


class DogActivityPeriod(SQLModel, table=True):
	__tablename__ = "dog_activity_period"

	id: Optional[int] = Field(default=None, primary_key=True)
	dog_id: int = Field(foreign_key="dog.id", index=True)
	activity_level: str = Field(max_length=32)
	started_at: datetime
	ended_at: Optional[datetime] = None
	avg_speed: Optional[float] = None
	peak_speed: Optional[float] = None
	sample_count: int = Field(default=0)
	camera_index: Optional[int] = None
	created_at: datetime = Field(default_factory=datetime.now)

	dog_ref: Optional["Dog"] = Relationship(back_populates="activity_periods")


class Role(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=128)
	
	employees: List["Employee"] = Relationship(back_populates="role_ref")

class Employee(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=256)
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = Field(default=None, max_length=128, unique=True)
	phone: Optional[str] = Field(default=None, max_length=16)
	role_id: int = Field(foreign_key="role.id")
	created_at: datetime = Field(default_factory=datetime.now)

	role_ref: Role = Relationship(back_populates="employees")
	managed_events: List["Event"] = Relationship(back_populates="manager_ref")

class Event(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=256)
	manager_id: int = Field(foreign_key="employee.id")
	duration_min: Optional[int] = None
	visitor_amount: int
	created_at: datetime = Field(default_factory=datetime.now)

	manager_ref: Employee = Relationship(back_populates="managed_events")
	schedules: List["Schedule"] = Relationship(back_populates="event_ref")

class Schedule(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	event_id: int = Field(foreign_key="event.id")
	time_start: datetime
	created_at: datetime = Field(default_factory=datetime.now)

	event_ref: Event = Relationship(back_populates="schedules")
	participations: List["Participation"] = Relationship(back_populates="scheduled_event_ref")

class Participation(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	scheduled_event_id: int = Field(foreign_key="schedule.id")
	visitor_id: int = Field(foreign_key="owner.id")
	created_at: datetime = Field(default_factory=datetime.now)

	scheduled_event_ref: Schedule = Relationship(back_populates="participations")
	visitor: Owner = Relationship(back_populates="participations")


class Service(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=256)
	category: Optional[str] = Field(default=None, max_length=128)
	created_at: datetime = Field(default_factory=datetime.now)

	visit_records: List["VisitRecord"] = Relationship(back_populates="service_ref")


class VisitRecord(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	dog_id: int = Field(foreign_key="dog.id")
	service_id: int = Field(foreign_key="service.id")
	visited_at: datetime
	amount_rub: Optional[int] = None
	created_at: datetime = Field(default_factory=datetime.now)

	dog_ref: Dog = Relationship(back_populates="visit_records")
	service_ref: Service = Relationship(back_populates="visit_records")

class User(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	user_type: bool = Field(default=False) # False=Owner, True=Employee
	login: str = Field(unique=True, index=True)
	hashed_password: str
	created_at: datetime = Field(default_factory=datetime.now)

# --- 3. SCHEMAS (Pydantic models for Request/Response) ---

# --- Owner ---
class OwnerCreate(SQLModel):
	name: str  # Обязательно
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = None
	phone: Optional[str] = None
	region: Optional[str] = None

class OwnerUpdate(SQLModel):
	name: Optional[str] = None
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = None
	phone: Optional[str] = None
	region: Optional[str] = None

# --- Dog ---
class DogCreate(SQLModel):
	name: str
	breed_id: int
	age: Optional[int] = None
	gender: Optional[bool] = None
	owner_id: int
	photo_url: Optional[str] = None


class DogRead(SQLModel):
	id: Optional[int] = None
	name: str
	age: Optional[int] = None
	gender: Optional[bool] = None
	breed_id: int
	breed: str
	owner_id: int
	owner: str
	photo_url: Optional[str] = None
	created_at: datetime

# --- Employee ---
class EmployeeCreate(SQLModel):
	name: str
	role_id: int
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = None
	phone: Optional[str] = None


class EmployeeRead(SQLModel):
	id: Optional[int] = None
	name: str
	role_id: int
	role: str
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = None
	phone: Optional[str] = None
	created_at: datetime

# --- Event ---
class EventCreate(SQLModel):
	name: str
	manager_id: int
	visitor_amount: int
	duration_min: Optional[int] = None


class EventReadFull(SQLModel):
	id: Optional[int] = None
	name: str
	manager_id: int
	manager_name: str
	duration_min: Optional[int] = None
	visitor_amount: int
	created_at: datetime
	time_start: Optional[datetime] = None
	participants: Optional[str] = None

# --- Auth ---
class UserRegister(SQLModel):
	login: str
	password: str = Field(..., max_length=72)
	user_type: bool = False

class Token(SQLModel):
	access_token: str
	token_type: str


# --- Breed / Role (CRUD schemas) ---
class BreedCreate(SQLModel):
	name: str
	size_group: Optional[str] = None
	coat_group: Optional[str] = None

class BreedUpdate(SQLModel):
	name: Optional[str] = None
	size_group: Optional[str] = None
	coat_group: Optional[str] = None

class RoleCreate(SQLModel):
	name: str

class RoleUpdate(SQLModel):
	name: Optional[str] = None


class DogUpdate(SQLModel):
	name: Optional[str] = None
	breed_id: Optional[int] = None
	age: Optional[int] = None
	gender: Optional[bool] = None
	owner_id: Optional[int] = None
	photo_url: Optional[str] = None


class DogEmbeddingUpsert(SQLModel):
	mean_vector: list[float]


class DogEmbeddingRead(SQLModel):
	dog_id: int
	embedding_dim: int
	created_at: datetime


class DogEmbeddingCatalogItem(SQLModel):
	dog_id: int
	dog_name: str
	mean_vector: list[float]
	created_at: datetime


class EmployeeUpdate(SQLModel):
	name: Optional[str] = None
	role_id: Optional[int] = None
	age: Optional[int] = None
	gender: Optional[bool] = None
	email: Optional[str] = None
	phone: Optional[str] = None


class EventUpdate(SQLModel):
	name: Optional[str] = None
	manager_id: Optional[int] = None
	visitor_amount: Optional[int] = None
	duration_min: Optional[int] = None


class ScheduleCreate(SQLModel):
	event_id: int
	time_start: datetime


class ScheduleUpdate(SQLModel):
	event_id: Optional[int] = None
	time_start: Optional[datetime] = None


class ParticipationCreate(SQLModel):
	scheduled_event_id: int
	visitor_id: int


class ParticipationUpdate(SQLModel):
	scheduled_event_id: Optional[int] = None
	visitor_id: Optional[int] = None


class ServiceCreate(SQLModel):
	name: str
	category: Optional[str] = None


class ServiceUpdate(SQLModel):
	name: Optional[str] = None
	category: Optional[str] = None


class VisitRecordCreate(SQLModel):
	dog_id: int
	service_id: int
	visited_at: datetime
	amount_rub: Optional[int] = None


class VisitRecordUpdate(SQLModel):
	dog_id: Optional[int] = None
	service_id: Optional[int] = None
	visited_at: Optional[datetime] = None
	amount_rub: Optional[int] = None


class DogActivityPeriodCreate(SQLModel):
	dog_id: int
	activity_level: str
	started_at: datetime
	ended_at: Optional[datetime] = None
	avg_speed: Optional[float] = None
	peak_speed: Optional[float] = None
	sample_count: int = 0
	camera_index: Optional[int] = None


class DogActivityPeriodUpdate(SQLModel):
	activity_level: Optional[str] = None
	started_at: Optional[datetime] = None
	ended_at: Optional[datetime] = None
	avg_speed: Optional[float] = None
	peak_speed: Optional[float] = None
	sample_count: Optional[int] = None
	camera_index: Optional[int] = None
