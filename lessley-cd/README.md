# Lessley CD

Docker Compose environment: `manage.bat` shortcuts and database seeding.

> **To run the stack, see [RUNNING.md](RUNNING.md)** — three modes plus first-time config.

## Dev mirrors production

Dev and prod run the same topology and the **same Caddyfile**. In both, the browser talks
only to Caddy, which terminates TLS, serves the SPA, and routes `/api/v1` to whichever
service owns the prefix over a private network. Container ports are identical (gateway
`5001`, personalization `5002`), so the one Caddyfile works unchanged.

| | Dev | Prod |
|---|---|---|
| App URL | `https://localhost` (internal-CA cert) | `https://<DOMAIN>` (Let's Encrypt) |
| Swagger, FastAPI `/docs` | on | off |
| mongo-express | included | removed |
| HSTS | `max-age=0` | strong default |
| Host-published ports | services exposed for tooling | Caddy only |

## `manage.bat`

Splits application from infrastructure, so `app down` leaves MongoDB and RabbitMQ running
(unlike `docker compose down`, which takes everything with it).

| Command | Description |
|---|---|
| `.\manage.bat help` | Show help menu |
| `.\manage.bat status` | Status of all containers |
| `.\manage.bat infra up\|down\|status` | Infra + Caddy edge (MongoDB, RabbitMQ, Loki, Grafana) |
| `.\manage.bat app up\|build\|down\|status` | Gateway + Personalization (`build` recompiles first) |

After editing the SPA, rebuild the edge image that carries it:
`docker compose up -d --build caddy`.

## Seeding MongoDB

Reference data lives in `main/resources/`. From this folder, for each collection:

#### clubs
```bash
docker cp ..\main\resources\clubs.json mongodb:/tmp/club_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection club_list --file /tmp/club_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```
#### deals
```bash
docker cp ..\main\resources\deals.json mongodb:/tmp/deal_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection deal_list --file /tmp/deal_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

#### mccs
```bash
docker cp ..\main\resources\mccs.json mongodb:/tmp/mccs.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection mccs --file /tmp/mccs.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

#### stores
```bash
docker cp ..\main\resources\stores.json mongodb:/tmp/store_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection store_list --file /tmp/store_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

Repeat with the remaining three, substituting file and collection:

| File | Collection |
|---|---|
| `stores.json` | `store_list` |
| `deals.json` | `deal_list` |
| `clubs.json` | `club_list` |
