# HSE_DogCare_VKR
"Автоматизации услуг детского сада для собак методами машинного обученияAutomation of Dog Daycare Services Using Machine Learning Methods"

## Запуск
### Докер
Докер в app: `docker compose up --build`

В докере контейнеры с **БД**, **API для доступа к БД** и **аналитический кластер**.

dbAPI: `http://127.0.0.1:8000/`
### Веб-приложение
Запуск flask веб-сервера: `python ./app/flask_server/app.py`

web-app: `http://127.0.0.1:5000/`

