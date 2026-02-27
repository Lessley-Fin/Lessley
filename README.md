# Lessley

## Secrets & environment files

- **Do not commit** the real environment file `lessley-cd/.env`. Keep secrets out of Git history.
- **Provide** a template `lessley-cd/.env.template` with placeholder values for contributors.
- **If a secret was committed**, rotate those secrets immediately and remove the file from Git history (see below).

If the secret was already pushed, rotate the secret in the service and purge it from history using a tool like `git filter-repo` or `BFG Repo-Cleaner`.

Store production secrets in your CI/CD provider or secret manager (GitHub Actions Secrets, Azure Key Vault, AWS Secrets Manager, etc.) rather than in the repository.
