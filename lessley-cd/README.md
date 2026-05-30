# Lessley CD Environment Guide

Welcome to the Lessley Continuous Deployment (CD) repository. This guide covers how to set up the project locally, manage Docker containers using built-in shortcuts, and initialize the database.

## 🚀 Getting Started

Follow these steps to set up and run the environment.

### 1. Create the Environment File
Copy the provided template to create your `.env` file:
```bash
copy .env.template .env
```

### 2. Configure Secrets
Carefully configure your secrets, passwords, and other variables in the `.env` file. 
> **Note:** Remember to check other projects for `.env` and `appsettings.json` files and carefully update them as well.

### 3. Run Infrastructure
Start the required infrastructure services (MongoDB, RabbitMQ, Loki, etc.):
```bash
.\manage.bat infra up
```

### 4. Run Services
Build and start the application services (Personalization, Gateway, etc.):
```bash
.\manage.bat app build
```

### 5. Have Fun! 🎉
Your Lessley environment should now be up and running.

---

## 🛠️ Lessley Shortcuts (`manage.bat`)

Use the provided batch script to manage your environment without typing long Docker commands.
Utilize application and infrastructure split commands. 
Meaning: `docker compose down` removes all containers but `.\manage.bat app down` removes only application containers, keeps mongodb and rabbitmq running.

### General Commands
| Command               | Description |
|-----------------------|-------------|
| `.\manage.bat help`   | Show help menu |
| `.\manage.bat status` | Show status of all containers (similar to `docker ps`) |

### Infrastructure (RabbitMQ, Grafana, Loki, MongoDB)
| Command                       | Description |
|-------------------------------|-------------|
| `.\manage.bat infra up`       | Start infrastructure containers |
| `.\manage.bat infra down`     | Remove containers (use `-v` to wipe volumes) |
| `.\manage.bat infra status`   | Show status of infrastructure containers |

### Application (Personalization, Gateway)
| Command                       | Description |
|-------------------------------|-------------|
| `.\manage.bat app up`         | Start application containers |
| `.\manage.bat app build`      | Rebuild code and start containers |
| `.\manage.bat app down`       | Remove application containers |
| `.\manage.bat app status`     | Show status of application containers |

---

## 🐳 Docker Basics Reference

If you prefer using native Docker and Docker Compose commands, here are the most common operations:

- **List all containers:** `docker ps`
- **Start containers:** `docker-compose -f FILENAME.yml up -d`
- **Start containers (with build):** `docker-compose -f FILENAME.yml up -d --build`
- **Stop and remove containers:** `docker-compose -f FILENAME.yml down`
- **Stop and wipe data volumes:** `docker-compose -f FILENAME.yml down -v` *(Use when you want to reset DB, RabbitMQ, etc.)*

---

## 🗄️ MongoDB Initialization

Follow these steps to seed MongoDB with initial JSON files.

### Step 1: Navigate to the CD folder
```bash
cd .\lessley-cd\     
```

## Step 2: Insert into mongodb container
```bash
docker cp ..\main\resources\mccs.json mongodb:/tmp/mcc_list.json
```

## Step 3: Read from container and write to mongodb 
```bash
docker exec -it mongodb mongoimport --db lessley --collection mcc_list --file /tmp/mcc_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

## Step 4: Repeat for deals and clubs
### stores
```bash
docker cp ..\main\resources\stores.json mongodb:/tmp/store_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection store_list --file /tmp/store_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

### deals
```bash
docker cp ..\main\resources\deals.json mongodb:/tmp/deal_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection deal_list --file /tmp/deal_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

### clubs
```bash
docker cp ..\main\resources\clubs.json mongodb:/tmp/club_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection club_list --file /tmp/club_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```