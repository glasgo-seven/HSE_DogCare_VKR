-- Владельцы
CREATE TABLE owners (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    age INT CHECK (age >= 0 AND age <= 150),
    gender BOOLEAN,
    email VARCHAR(128) UNIQUE,
    phone VARCHAR(16),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для поиска по имени владельца
CREATE INDEX idx_owners_name ON owners(name);

-- Порода собак
CREATE TABLE breeds (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE
);

-- Собаки
CREATE TABLE dogs (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    breed_id INT NOT NULL,
    age INT CHECK (age >= 0 AND age <= 30),
    owner_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (owner_id) REFERENCES owners(id) ON DELETE CASCADE,
    FOREIGN KEY (breed_id) REFERENCES breeds(id) ON DELETE RESTRICT
);

CREATE INDEX idx_dogs_owner ON dogs(owner_id);
CREATE INDEX idx_dogs_breed ON dogs(breed_id);

-- ML-эмбеддинги
CREATE TABLE dog_embeddings (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dog_id INT NOT NULL,
    mean_vector TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dog_id) REFERENCES dogs(id) ON DELETE CASCADE
);

CREATE INDEX idx_embeddings_dog ON dog_embeddings(dog_id);