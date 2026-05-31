# Lessley Project

## Project Overview

Lessley is a microservices-based financial platform providing personalization, gap analysis, and open finance integrations. The system relies on event-driven architecture and structured observability. 

### Architecture & Microservices
- **Gateway API (Lessley.Gateway.Api)**: Written in **C# .NET**. Handles user authentication, MongoDB connections, open finance routing, and exposes a centralized Swagger UI.
- **Personalization Engine (Lessley.Personalization)**: Written in **Python (FastAPI)**. Responsible for AI-driven financial gap analysis and recommendations. Uses RabbitMQ as an asynchronous consumer.
- **Categories Enricher (Lessley.CategoriesEnricher)**: Written in **Python (FastAPI)**. Enriches transaction categories asynchronously via RabbitMQ events.

### Main Infrastructure
- **Message Broker**: RabbitMQ
- **Database**: MongoDB (managed via Mongo Express)
- **Logging & Observability**: Loki and Grafana for centralized log aggregation.

## Building and Running

The project heavily utilizes Docker Compose for orchestration. The lessley-cd/manage.bat script is the primary utility to interact with the environment. 

### Prerequisites
Before running, you must set up your environment variables. Ensure that .env files are created based on the provided .env.template files in each service directory and lessley-cd.
*(Do not commit your .env files.)*

### Commands (from lessley-cd folder)

**Infrastructure (DB, Message Broker, Observability):**
- Start Infrastructure: manage.bat infra up
- Stop Infrastructure: manage.bat infra down (Add -v to wipe volumes)
- View Infrastructure Status: manage.bat infra status

**Core Services (Gateway, Personalization):**
- Start Services: manage.bat app up
- Rebuild & Start Services: manage.bat app build
- Stop Services: manage.bat app down
- View Services Status: manage.bat app status

**Global Commands:**
- Check all container statuses: manage.bat status

## Development Conventions

- **Structured Logging & Observability**: The architecture places a high emphasis on centralized logging using Grafana Loki.
  - **C#**: Uses Serilog connected to Loki. Follow the custom ExceptionAsArrayEnricher and CustomLogFormatter. Log context injection handles injecting username and equest_id for tracing.
  - **Python**: Uses logging_loki integrated with a custom QueueHandler to avoid blocking async event loops. A custom ContextInjectingFilter ensures context variables (equest_id, username) track across background worker tasks.
- **RabbitMQ Integration**: Python services utilize io_pika to asynchronously consume topic-based messages (e.g. Personalize.calc_history, Categories.enrich). Maintain this pattern for high-throughput decoupling. 
- **Error Handling & Rate Limiting**: The Python services implement slowapi for Rate Limiting and structured JSON responses mapping to respective Exception handlers (RateLimitExceeded, StarletteHTTPException, ValueError, ConnectionError). Ensure HTTP codes strictly adhere to semantic correctness.
- **Dependency Injection**: Utilize DI Container concepts natively supported in .NET, and emulate them using the services.di_container.DIContainer implementations in Python for service logic decoupling.
