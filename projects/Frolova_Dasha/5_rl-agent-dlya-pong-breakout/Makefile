.PHONY: up down build train tests smoke logs

up:            ## собрать и поднять весь стек
	docker compose up -d --build

down:          ## остановить всё
	docker compose down -v

train:         ## запустить обучение
	docker compose run --rm trainer

tests:         ## юнит-тесты
	docker compose run --rm tests

smoke:         ## smoke-тест API по сети 
	docker compose run --rm smoke

logs:          ## логи всех сервисов
	docker compose logs -f
