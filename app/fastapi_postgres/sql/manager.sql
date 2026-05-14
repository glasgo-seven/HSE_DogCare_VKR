-- Роли сотрудников
CREATE TABLE roles (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT
);

-- Сотрудники
CREATE TABLE employees (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    age INT CHECK (age >= 18 AND age <= 100),
    gender BOOLEAN,
    email VARCHAR(128) UNIQUE,
    phone VARCHAR(16),
    role_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);
CREATE INDEX idx_employees_role ON employees(role_id);
CREATE INDEX idx_employees_email ON employees(email);

-- События
CREATE TABLE events (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    manager_id INT NOT NULL,
    duration_min INT CHECK (duration_min > 0),
    visitor_amount INT NOT NULL CHECK (visitor_amount > 0),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE RESTRICT
);
CREATE INDEX idx_events_manager ON events(manager_id);

-- Расписание (слоты времени для событий)
CREATE TABLE schedule (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INT NOT NULL,
    time_start TIMESTAMP NOT NULL,
    time_end TIMESTAMP not null,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);
CREATE INDEX idx_schedule_event ON schedule(event_id);
CREATE INDEX idx_schedule_time ON schedule(time_start);

-- Участие владельцев в событиях
CREATE TABLE participations (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scheduled_event_id INT NOT NULL,
    visitor_id INT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Уникальность: владелец не может записаться на один слот дважды
    UNIQUE(scheduled_event_id, visitor_id),

    FOREIGN KEY (scheduled_event_id) REFERENCES schedule(id) ON DELETE CASCADE,
    FOREIGN KEY (visitor_id) REFERENCES owners(id) ON DELETE CASCADE
);
CREATE INDEX idx_participations_event ON participations(scheduled_event_id);
CREATE INDEX idx_participations_visitor ON participations(visitor_id);

-- Таблица аутентификации (отделена от предметной области)
CREATE TABLE users (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_type BOOLEAN NOT NULL DEFAULT FALSE,
    login VARCHAR(128) UNIQUE NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_login ON users(login);
