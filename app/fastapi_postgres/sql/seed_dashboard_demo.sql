BEGIN;

SET client_encoding = 'UTF8';

ALTER TABLE breed ADD COLUMN IF NOT EXISTS size_group VARCHAR(64);
ALTER TABLE breed ADD COLUMN IF NOT EXISTS coat_group VARCHAR(64);
ALTER TABLE owner ADD COLUMN IF NOT EXISTS region VARCHAR(128);

TRUNCATE TABLE
	visitrecord,
	participation,
	"schedule",
	"event",
	dog_embeddings,
	dog,
	employee,
	service,
	owner,
	breed,
	role
RESTART IDENTITY CASCADE;

INSERT INTO role (name) VALUES
	('Администратор'),
	('Грумер'),
	('Кинолог');

INSERT INTO employee (name, age, gender, email, phone, role_id, created_at) VALUES
	('Мария Соколова', 32, false, 'emp.maria@seed.local', '+79001001001', 1, CURRENT_TIMESTAMP),
	('Дмитрий Волков', 28, true,  'emp.dmitry@seed.local', '+79001001002', 2, CURRENT_TIMESTAMP),
	('Елена Ким',      41, false, 'emp.elena@seed.local',  '+79001001003', 3, CURRENT_TIMESTAMP);

INSERT INTO breed (name, size_group, coat_group) VALUES
	('Золотистый ретривер', 'L', 'long'),
	('Лабрадор',            'L', 'short'),
	('Хаски',               'M', 'long'),
	('Такса',               'S', 'short'),
	('Корги',               'S', 'medium'),
	('Немецкая овчарка',    'L', 'medium'),
	('Пудель',              'M', 'long'),
	('Бигль',               'M', 'short');

INSERT INTO owner (name, age, gender, email, phone, region, created_at) VALUES
	('Анна Петрова',     34, false, 'owner01@seed.local', '+79110000001', 'Москва', CURRENT_TIMESTAMP),
	('Иван Сидоров',     42, true,  'owner02@seed.local', '+79110000002', 'Москва', CURRENT_TIMESTAMP),
	('Ольга Морозова',   29, false, 'owner03@seed.local', '+79110000003', 'Санкт-Петербург', CURRENT_TIMESTAMP),
	('Пётр Николаев',    51, true,  'owner04@seed.local', '+79110000004', 'Санкт-Петербург', CURRENT_TIMESTAMP),
	('Екатерина Волкова',38, false, 'owner05@seed.local', '+79110000005', 'Казань', CURRENT_TIMESTAMP),
	('Сергей Орлов',     45, true,  'owner06@seed.local', '+79110000006', 'Казань', CURRENT_TIMESTAMP),
	('Марина Белова',    33, false, 'owner07@seed.local', '+79110000007', 'Москва', CURRENT_TIMESTAMP),
	('Алексей Громов',   36, true,  'owner08@seed.local', '+79110000008', 'Москва', CURRENT_TIMESTAMP),
	('Дарья Кузнецова',  27, false, 'owner09@seed.local', '+79110000009', 'Санкт-Петербург', CURRENT_TIMESTAMP),
	('Константин Зайцев',48, true,  'owner10@seed.local', '+79110000010', 'Казань', CURRENT_TIMESTAMP),
	('Наталья Фёдорова', 40, false, 'owner11@seed.local', '+79110000011', 'Москва', CURRENT_TIMESTAMP),
	('Виктор Павлов',    55, true,  'owner12@seed.local', '+79110000012', 'Санкт-Петербург', CURRENT_TIMESTAMP);

INSERT INTO dog (name, breed_id, age, gender, owner_id, created_at) VALUES
	('Рекс',    1,  3, true,  1, CURRENT_TIMESTAMP),
	('Майя',    1,  3, false, 7, CURRENT_TIMESTAMP),
	('Грэй',    1,  4, true,  11, CURRENT_TIMESTAMP),
	('Барни',   2,  5, false, 2, CURRENT_TIMESTAMP),
	('Чарли',   2,  6, true,  4, CURRENT_TIMESTAMP),
	('Локи',    3,  2, true,  3, CURRENT_TIMESTAMP),
	('Скай',    3,  1, false, 9, CURRENT_TIMESTAMP),
	('Фред',    4, 10, false, 5, CURRENT_TIMESTAMP),
	('Оскар',   4, 11, true,  10, CURRENT_TIMESTAMP),
	('Бейли',   5,  1, false, 6, CURRENT_TIMESTAMP),
	('Милли',   5,  2, false, 8, CURRENT_TIMESTAMP),
	('Вольт',   6,  4, true,  12, CURRENT_TIMESTAMP),
	('Шарик',   7,  5, true,  1, CURRENT_TIMESTAMP),
	('Джек',    8,  3, false, 2, CURRENT_TIMESTAMP);

INSERT INTO service (name, category, created_at) VALUES
	('Груминг',              'уход', CURRENT_TIMESTAMP),
	('Ветеринарный приём',   'здоровье', CURRENT_TIMESTAMP),
	('Дрессировка',          'поведение', CURRENT_TIMESTAMP),
	('Стрижка когтей',       'уход', CURRENT_TIMESTAMP),
	('SPA-собака',           'уход', CURRENT_TIMESTAMP);

INSERT INTO visitrecord (dog_id, service_id, visited_at, amount_rub, created_at) VALUES
	(1, 1, '2024-12-10', 3200, '2024-12-10'),
	(2, 1, '2024-12-10', 3200, '2024-12-10'),
	(3, 1, '2024-12-10', 3200, '2024-12-10'),
	(1, 1, '2025-01-18', 3400, '2025-01-18'),
	(2, 1, '2025-01-18', 3400, '2025-01-18'),
	(3, 1, '2025-01-18', 3400, '2025-01-18'),
	(1, 1, '2025-02-05', 3100, '2025-02-05'),
	(2, 1, '2025-02-05', 3100, '2025-02-05'),
	(3, 1, '2025-02-05', 3100, '2025-02-05'),
	(1, 1, '2025-03-12', 3300, '2025-03-12'),
	(2, 1, '2025-03-12', 3300, '2025-03-12'),
	(3, 1, '2025-03-12', 3300, '2025-03-12'),
	(1, 1, '2024-11-20', 3000, '2024-11-20'),
	(2, 1, '2024-11-20', 3000, '2024-11-20'),
	(3, 1, '2024-11-20', 3000, '2024-11-20'),
	(1, 1, '2025-01-22', 2900, '2025-01-22'),
	(1, 1, '2025-04-08', 3150, '2025-04-08'),
	(1, 1, '2025-05-05', 3250, '2025-05-05'),
	(2, 1, '2025-05-05', 3250, '2025-05-05'),
	(3, 1, '2025-05-05', 3250, '2025-05-05'),
	(1, 1, '2025-06-14', 3180, '2025-06-14'),
	(2, 1, '2025-06-14', 3180, '2025-06-14'),
	(3, 1, '2025-06-14', 3180, '2025-06-14'),
	(1, 1, '2025-08-01', 3320, '2025-08-01'),
	(2, 1, '2025-08-01', 3320, '2025-08-01'),
	(3, 1, '2025-08-01', 3320, '2025-08-01'),
	(1, 1, '2025-09-18', 3280, '2025-09-18'),
	(2, 1, '2025-09-18', 3280, '2025-09-18'),
	(3, 1, '2025-09-18', 3280, '2025-09-18'),
	(1, 1, '2025-11-25', 3350, '2025-11-25'),
	(2, 1, '2025-11-25', 3350, '2025-11-25'),
	(3, 1, '2025-11-25', 3350, '2025-11-25');

INSERT INTO visitrecord (dog_id, service_id, visited_at, amount_rub, created_at) VALUES
	(4, 2, '2025-02-14', 5200, '2025-02-14'),
	(5, 2, '2025-02-14', 5200, '2025-02-14'),
	(4, 2, '2025-05-20', 4800, '2025-05-20'),
	(5, 2, '2025-08-03', 5100, '2025-08-03'),
	(4, 2, '2024-12-01', 5500, '2024-12-01'),
	(5, 2, '2024-12-01', 5300, '2024-12-01'),
	(4, 1, '2025-03-25', 3600, '2025-03-25'),
	(5, 1, '2025-06-10', 3700, '2025-06-10');

INSERT INTO visitrecord (dog_id, service_id, visited_at, amount_rub, created_at) VALUES
	(6, 3, '2025-04-15', 6200, '2025-04-15'),
	(7, 3, '2025-04-15', 6100, '2025-04-15'),
	(6, 3, '2025-06-22', 6500, '2025-06-22'),
	(7, 3, '2025-07-08', 6000, '2025-07-08'),
	(6, 3, '2025-08-12', 6400, '2025-08-12'),
	(6, 3, '2024-05-10', 5800, '2024-05-10'),
	(7, 1, '2025-01-30', 2800, '2025-01-30');

INSERT INTO visitrecord (dog_id, service_id, visited_at, amount_rub, created_at) VALUES
	(8, 2, '2024-10-05', 4500, '2024-10-05'),
	(9, 2, '2024-11-18', 4300, '2024-11-18'),
	(8, 2, '2025-01-10', 4600, '2025-01-10'),
	(9, 2, '2025-09-02', 4400, '2025-09-02'),
	(8, 4, '2025-02-28', 800, '2025-02-28'),
	(9, 4, '2025-07-15', 850, '2025-07-15');

INSERT INTO visitrecord (dog_id, service_id, visited_at, amount_rub, created_at) VALUES
	(10, 1, '2025-02-01', 2500, '2025-02-01'),
	(11, 1, '2025-02-01', 2550, '2025-02-01'),
	(10, 1, '2025-04-20', 2700, '2025-04-20'),
	(11, 1, '2025-07-01', 2600, '2025-07-01'),
	(10, 1, '2025-10-12', 2800, '2025-10-12'),
	(11, 5, '2025-06-30', 4200, '2025-06-30'),
	(10, 5, '2025-12-05', 4500, '2025-12-05');

INSERT INTO visitrecord (dog_id, service_id, visited_at, amount_rub, created_at) VALUES
	(12, 3, '2025-01-05', 7000, '2025-01-05'),
	(12, 3, '2025-03-15', 7200, '2025-03-15'),
	(12, 3, '2025-05-25', 7100, '2025-05-25'),
	(12, 3, '2025-09-10', 7300, '2025-09-10'),
	(13, 1, '2025-02-10', 4000, '2025-02-10'),
	(13, 1, '2025-04-05', 4100, '2025-04-05'),
	(13, 1, '2025-06-18', 4050, '2025-06-18'),
	(13, 1, '2025-08-22', 4200, '2025-08-22'),
	(13, 1, '2025-11-30', 4150, '2025-11-30'),
	(14, 2, '2025-03-03', 3800, '2025-03-03'),
	(14, 2, '2025-07-20', 3900, '2025-07-20'),
	(14, 4, '2025-01-12', 600, '2025-01-12'),
	(14, 4, '2025-05-08', 650, '2025-05-08'),
	(14, 4, '2025-09-14', 620, '2025-09-14');

INSERT INTO "event" (name, manager_id, duration_min, visitor_amount, created_at)
VALUES ('Групповой груминг', 1, 90, 8, CURRENT_TIMESTAMP);

INSERT INTO "schedule" (event_id, time_start, created_at)
VALUES (1, '2025-06-15 11:00:00', CURRENT_TIMESTAMP);

INSERT INTO participation (scheduled_event_id, visitor_id, created_at)
VALUES (1, 1, CURRENT_TIMESTAMP), (1, 7, CURRENT_TIMESTAMP);

INSERT INTO "event" (name, manager_id, duration_min, visitor_amount, created_at)
VALUES ('Лекция по питанию', 3, 60, 20, CURRENT_TIMESTAMP);

INSERT INTO "schedule" (event_id, time_start, created_at)
VALUES (2, '2025-04-22 18:00:00', CURRENT_TIMESTAMP);

COMMIT;
