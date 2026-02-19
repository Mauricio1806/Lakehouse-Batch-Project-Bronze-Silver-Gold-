.PHONY: up down logs restart

up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

restart:
	docker compose restart
