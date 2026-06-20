# Lessley

Lessley is a loyalty optimization platform that helps users track spending, discover matching clubs, and receive personalized deal notifications — all powered by Open Finance data.

## Architecture

### Services

| Service | Language | Description |
|---------|----------|-------------|
| **Lessley.Gateway.Api** | C# / .NET 8 | Central API gateway — authentication, user management, real-time notifications (SignalR), and admin operations |
| **Lessley.Personalization** | Python / FastAPI | AI-driven financial insights and recommendations engine |
| **Lessley.CategoriesEnricher** | Python / FastAPI | LLM-powered transaction category enrichment |

### Communication Patterns

- **Insights** (categories, top-accounts, top-stores) are **HTTP-only** — lightweight, synchronous requests from Gateway to Personalization.
- **Recommendations** (missed-savings, matching-clubs) use **RabbitMQ** — heavyweight async operations. The Personalization service publishes results back to the Gateway, which stores them as notifications and pushes them via SignalR.
- **Notifications** are managed exclusively through the Gateway:
  - **Admin** users can push notifications and change user configuration.
  - **Deal broadcasts** are published via RabbitMQ from the Personalization service to the Gateway.
  - **Real-time delivery** uses SignalR with tag-based groups.

### Data Flow

```
Client ──► Gateway.Api ──HTTP──► Personalization (insights)
                │
                └──RabbitMQ──► Personalization (recommendations)
                                    │
                                    └──RabbitMQ──► Gateway.Api ──SignalR──► Client
```

## Secrets & Environment Files

- **Do not commit** the real environment file `lessley-cd/.env`. Keep secrets out of Git history.
- **Provide** a template `lessley-cd/.env.template` with placeholder values for contributors.
- **If a secret was committed**, rotate those secrets immediately and remove the file from Git history using `git filter-repo` or `BFG Repo-Cleaner`.

Store production secrets in your CI/CD provider or secret manager (GitHub Actions Secrets, Azure Key Vault, AWS Secrets Manager, etc.) rather than in the repository.
