---
title: "Contract Testing for Microservices"
description: "Ensure service boundaries stay compatible with consumer expectations"
---

# Contract Testing for Microservices

Contract testing validates that a service provider (e.g., Python Scraper) correctly implements the interface that service consumers (e.g., Node.js Optimizer) expect to consume.

## Problem

Without contract testing, you discover integration issues too late:
- Scraper publishes `{"price": "12.50"}` (string) but Optimizer expects `{"price": 12.50}` (number)
- Schema changes in production break consumers that weren't told about the change
- Different teams build incompatible versions that fail at runtime

## Solution: Consumer-Driven Contracts

Define the expected contract at the **consumer** boundary, not the producer. The producer must satisfy the consumer's requirements.

### Contract Definition

A contract is a JSON Schema defining:
- Required fields
- Field types (string, number, boolean, array)
- Field constraints (min/max length, enum values, formats)
- Nested object structures

```json
{
  "type": "object",
  "required": ["batch_id", "timestamp", "scraped_deals"],
  "properties": {
    "batch_id": {
      "type": "string",
      "pattern": "^batch-[0-9]+$"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "scraped_deals": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["url", "store_id", "title", "price"],
        "properties": {
          "price": {
            "type": "number",
            "minimum": 0,
            "maximum": 10000
          }
        }
      }
    }
  }
}
```

### Testing Flow

1. **Consumer writes contract tests** that validate producer payloads against schema
2. **Producer runs consumer's tests** as part of CI/CD pipeline
3. **Breaking changes detected early** before merging to main branch
4. **Both teams notified** when contract compatibility breaks

### Implementation in Lessley

See `contract_tests.py`:

```python
class ServiceContract:
    SCRAPER_FINISH_SCHEMA = {
        "type": "object",
        "required": ["batch_id", "timestamp", "scraped_deals"],
        "properties": {
            "batch_id": {"type": "string"},
            "timestamp": {"type": "string"},
            "scraped_deals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["url", "store_id", "title", "price"],
                    "properties": {
                        "url": {"type": "string"},
                        "store_id": {"type": "string"},
                        "title": {"type": "string"},
                        "price": {"type": "number"}  # Must be number!
                    }
                }
            }
        }
    }

def test_scraper_price_must_be_number_not_string():
    """Price as string breaks Optimizer."""
    
    invalid_payload = {
        "batch_id": "batch-1",
        "timestamp": "2024-01-15T10:00:00",
        "scraped_deals": [
            {
                "url": "...",
                "store_id": "store-1",
                "title": "Deal",
                "price": "12.50"  # ERROR: string instead of number
            }
        ]
    }
    
    with pytest.raises(ValidationError):
        validate_contract(invalid_payload, ServiceContract.SCRAPER_FINISH_SCHEMA)
```

## Schema Versioning

When contracts must evolve:

### Forward Compatibility (Producers)
Producers can add new *optional* fields without breaking consumers.

**Old consumer sees:**
```json
{
  "batch_id": "batch-1",
  "scraped_deals": [...]
}
```

**New producer adds optional field:**
```json
{
  "batch_id": "batch-1",
  "scraped_deals": [...],
  "additional_metadata": "..."  // New optional field
}
```

Consumer ignores the new field—no breakage.

### Backward Compatibility (Consumers)
Consumers reading from producers must be defensive:

```python
# Handle both old and new schema
deal_count = payload.get("total_deals", len(payload.get("scraped_deals", [])))
```

### Breaking Changes
When breaking changes are necessary:
1. Release producer with new schema
2. Run in parallel with old schema (via feature flag or separate endpoint)
3. Migrate consumers one by one
4. Retire old schema

## Common Contract Violations

### 1. Type Mismatch
```python
# ❌ Producer sends
{"price": "100"}  # string

# ✓ Consumer expects
{"price": 100}    # number

# Fix: Scraper converts to number
price = float(deal_price_text)
```

### 2. Missing Required Field
```python
# ❌ Producer publishes
{"batch_id": "batch-1"}  # No timestamp

# ✓ Consumer expects
{"batch_id": "...", "timestamp": "..."}

# Fix: Always include timestamp
"timestamp": datetime.now().isoformat()
```

### 3. Enum Violation
```python
# ❌ Producer sends
{"status": "processing"}

# ✓ Consumer expects
{"status": "success" | "failed" | "pending"}

# Fix: Use predefined status values
valid_statuses = ["success", "failed", "pending"]
```

### 4. Array Item Type Mismatch
```python
# ❌ Producer sends array of mixed types
{"deals": [{"price": 10}, {"price": "20"}]}

# ✓ Consumer expects consistent types
{"deals": [{"price": 10}, {"price": 15}]}  # All numbers

# Fix: Ensure all array items match schema
```

## Monitoring Contract Compliance

### In Production

Log contract validation failures to understand real-world breakage:

```python
def publish_with_contract_validation(event, schema):
    try:
        validate_contract(event, schema)
        publish_to_rabbitmq(event)
    except ValidationError as e:
        logger.error(f"Contract violation detected", extra={
            "error_path": e.path,
            "error_message": e.message,
            "payload": event
        })
        # Alert: notify team of potential integration issue
        metrics.increment("contract_violations")
```

### CI/CD Integration

Run contract tests in producer's CI pipeline:

```yaml
# .github/workflows/contract-tests.yml
on: [pull_request]
jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run contract validation
        run: pytest contract_tests.py -v
```

## Best Practices

1. **Consumer Drives Contract** - Consumer writes what they need, producer implements it
2. **Version Explicitly** - Include schema version in contract definition
3. **Test Both Directions** - Producer tests it satisfies contract, Consumer tests it handles schema
4. **Document Changes** - When schema evolves, document the migration path
5. **Alert on Violations** - Immediately notify team of contract breaches in production

## Cross-Language Considerations

In Lessley (Python/Node.js/C#):

- **JSON Schema** works across all languages (language-agnostic)
- Each language has validation libraries:
  - Python: `jsonschema`
  - Node.js: `ajv`
  - C#: `JsonSchema.Net`

- Define contracts in shared location (Git repo)
- Each service references the same schema files
- Changes to contract require review and approval from all consumers

## References

- [JSON Schema Specification](https://json-schema.org/)
- [Consumer-Driven Contracts Pattern](https://martinfowler.com/articles/consumerDrivenContracts.html)
- [Pact Framework](https://pact.foundation/) (more formal tool for contract testing)
