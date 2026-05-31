"""
Contract Testing: Verify Service Boundaries

Ensures Python Scraper, Node.js Optimizer, and Personalization services
understand each other's JSON payloads.

Usage:
    pytest contract_tests.py -v
    pytest contract_tests.py::test_scraper_optimizer_contract -v
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from enum import Enum

import pytest
import jsonschema
from jsonschema import validate, ValidationError


logger = logging.getLogger(__name__)


# ============================================================================
# Shared Schema Definitions (Contract)
# ============================================================================

class ServiceContract:
    """Contracts published by each service."""
    
    # ─────────────────────────────────────────────────────────────────────
    # SCRAPER.FINISH: Python Scraper → Node.js Optimizer + Personalization
    # ─────────────────────────────────────────────────────────────────────
    
    SCRAPER_FINISH_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["batch_id", "timestamp", "scraped_deals", "status"],
        "properties": {
            "batch_id": {
                "type": "string",
                "pattern": "^batch-[a-z0-9-]+$"
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
                        "url": {"type": "string", "format": "uri"},
                        "store_id": {"type": "string"},
                        "title": {"type": "string"},
                        "price": {"type": "number", "minimum": 0},  # ← NUMBER, not string
                        "category": {"type": "string"},
                        "original_price": {"type": "number"},
                        "valid_until": {"type": "string", "format": "date-time"}
                    }
                }
            },
            "status": {
                "type": "string",
                "enum": ["success", "partial", "failed"]
            },
            "error": {
                "type": "string"
            }
        }
    }
    
    # ─────────────────────────────────────────────────────────────────────
    # OPTIMIZER.READY: Node.js Optimizer → Personalization
    # ─────────────────────────────────────────────────────────────────────
    
    OPTIMIZER_READY_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["batch_id", "timestamp", "optimized_deals"],
        "properties": {
            "batch_id": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "optimized_deals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["deal_id", "store_id", "ranking_score"],
                    "properties": {
                        "deal_id": {"type": "string"},
                        "store_id": {"type": "string"},
                        "ranking_score": {"type": "number", "minimum": 0, "maximum": 100},
                        "recommendation_reason": {"type": "string"}
                    }
                }
            }
        }
    }
    
    # ─────────────────────────────────────────────────────────────────────
    # PERSONALIZE.HOTDEAL: Personalization → API Gateway
    # ─────────────────────────────────────────────────────────────────────
    
    PERSONALIZE_HOTDEAL_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["user_id", "deal_id", "timestamp", "savings_estimate"],
        "properties": {
            "user_id": {"type": "string"},
            "deal_id": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "deal_title": {"type": "string"},
            "savings_estimate": {"type": "number", "minimum": 0},  # ← NUMBER
            "deal_url": {"type": "string", "format": "uri"},
            "store_id": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        }
    }


# ============================================================================
# Contract Validation Helpers
# ============================================================================

def validate_contract(payload: Dict[str, Any], schema: Dict[str, Any], service_name: str) -> bool:
    """
    Validate payload against contract schema.
    
    Returns True if valid, raises ValidationError if not.
    """
    try:
        validate(instance=payload, schema=schema)
        logger.info(f"✓ {service_name} payload valid")
        return True
    except ValidationError as e:
        logger.error(f"✗ {service_name} contract violation:")
        logger.error(f"  Path: {'.'.join(str(p) for p in e.path)}")
        logger.error(f"  Error: {e.message}")
        raise


# ============================================================================
# Contract Tests
# ============================================================================

class TestScraperOptimzerContract:
    """
    Python Scraper publishes Scraper.finish events.
    Node.js Optimizer consumes them.
    Verify payloads match contract.
    """
    
    def test_scraper_publishes_valid_finish_event(self):
        """Scraper must publish Scraper.finish with correct schema."""
        
        payload = {
            "batch_id": "batch-001",
            "timestamp": datetime.now().isoformat(),
            "scraped_deals": [
                {
                    "url": "https://store.com/deals/coffee",
                    "store_id": "store-hever-001",
                    "title": "50% off coffee",
                    "price": 2.50,  # ← NUMBER
                    "category": "food",
                    "original_price": 5.00,
                    "valid_until": (datetime.now() + timedelta(days=7)).isoformat()
                }
            ],
            "status": "success"
        }
        
        # Validate against Scraper contract
        validate_contract(
            payload,
            ServiceContract.SCRAPER_FINISH_SCHEMA,
            "Scraper.finish"
        )
    
    def test_scraper_price_must_be_number_not_string(self):
        """Common bug: price as string instead of number."""
        
        payload = {
            "batch_id": "batch-001",
            "timestamp": datetime.now().isoformat(),
            "scraped_deals": [
                {
                    "url": "https://store.com/deal",
                    "store_id": "store-123",
                    "title": "Deal",
                    "price": "2.50",  # ← STRING (WRONG!)
                    "status": "success"
                }
            ],
            "status": "success"
        }
        
        # Should fail validation
        with pytest.raises(ValidationError):
            validate_contract(
                payload,
                ServiceContract.SCRAPER_FINISH_SCHEMA,
                "Scraper.finish"
            )
    
    def test_scraper_batch_id_format(self):
        """Batch ID must follow pattern batch-<id>."""
        
        valid_payload = {
            "batch_id": "batch-night-001",
            "timestamp": datetime.now().isoformat(),
            "scraped_deals": [],
            "status": "success"
        }
        
        validate_contract(
            valid_payload,
            ServiceContract.SCRAPER_FINISH_SCHEMA,
            "Scraper.finish"
        )
        
        # Invalid format
        invalid_payload = valid_payload.copy()
        invalid_payload["batch_id"] = "BATCH_NIGHT_001"  # Invalid format
        
        with pytest.raises(ValidationError):
            validate_contract(
                invalid_payload,
                ServiceContract.SCRAPER_FINISH_SCHEMA,
                "Scraper.finish"
            )
    
    def test_optimizer_ready_event_schema(self):
        """Optimizer publishes Optimizer.ready with correct schema."""
        
        payload = {
            "batch_id": "batch-001",
            "timestamp": datetime.now().isoformat(),
            "optimized_deals": [
                {
                    "deal_id": "deal-coffee-50",
                    "store_id": "store-hever-001",
                    "ranking_score": 85.5,
                    "recommendation_reason": "Popular in your area"
                }
            ]
        }
        
        validate_contract(
            payload,
            ServiceContract.OPTIMIZER_READY_SCHEMA,
            "Optimizer.ready"
        )


class TestPersonalizationContract:
    """
    Personalization service consumes Optimizer.ready.
    Personalization publishes Personalize.hotdeal.
    Verify payloads match contract.
    """
    
    def test_personalization_hotdeal_event_schema(self):
        """Personalization publishes valid Personalize.hotdeal."""
        
        payload = {
            "user_id": "user-alice-001",
            "deal_id": "deal-coffee-50",
            "timestamp": datetime.now().isoformat(),
            "deal_title": "50% off coffee",
            "savings_estimate": 2.50,  # ← NUMBER
            "deal_url": "https://store.com/deals/coffee",
            "store_id": "store-hever-001",
            "confidence": 0.95
        }
        
        validate_contract(
            payload,
            ServiceContract.PERSONALIZE_HOTDEAL_SCHEMA,
            "Personalize.hotdeal"
        )
    
    def test_hotdeal_savings_must_be_number(self):
        """Savings estimate must be numeric."""
        
        invalid_payload = {
            "user_id": "user-alice-001",
            "deal_id": "deal-coffee-50",
            "timestamp": datetime.now().isoformat(),
            "deal_title": "50% off coffee",
            "savings_estimate": "2.50",  # ← STRING (WRONG!)
            "deal_url": "https://store.com/deals/coffee",
            "store_id": "store-hever-001",
            "confidence": 0.95
        }
        
        with pytest.raises(ValidationError):
            validate_contract(
                invalid_payload,
                ServiceContract.PERSONALIZE_HOTDEAL_SCHEMA,
                "Personalize.hotdeal"
            )
    
    def test_confidence_must_be_between_0_and_1(self):
        """Confidence is a probability."""
        
        invalid_payload = {
            "user_id": "user-alice-001",
            "deal_id": "deal-coffee-50",
            "timestamp": datetime.now().isoformat(),
            "deal_title": "50% off coffee",
            "savings_estimate": 2.50,
            "deal_url": "https://store.com/deals/coffee",
            "store_id": "store-hever-001",
            "confidence": 150  # ← Invalid (>1)
        }
        
        with pytest.raises(ValidationError):
            validate_contract(
                invalid_payload,
                ServiceContract.PERSONALIZE_HOTDEAL_SCHEMA,
                "Personalize.hotdeal"
            )


class TestSchemaVersioning:
    """
    When services evolve, contracts must be backward compatible.
    """
    
    def test_new_optional_fields_dont_break_old_consumers(self):
        """
        Scraper adds a new field. Old Optimizer should still accept it.
        """
        
        # Old payload (v1)
        old_payload = {
            "batch_id": "batch-001",
            "timestamp": datetime.now().isoformat(),
            "scraped_deals": [
                {
                    "url": "https://store.com/deal",
                    "store_id": "store-123",
                    "title": "Deal",
                    "price": 50
                }
            ],
            "status": "success"
        }
        
        validate_contract(old_payload, ServiceContract.SCRAPER_FINISH_SCHEMA, "Scraper.finish v1")
        
        # New payload (v2) with new optional field
        new_payload = old_payload.copy()
        new_payload["scraped_deals"][0]["sustainability_score"] = 0.8  # New field
        
        # Should still validate (extra fields allowed)
        validate_contract(new_payload, ServiceContract.SCRAPER_FINISH_SCHEMA, "Scraper.finish v2")


# ============================================================================
# Payload Examples for Integration Tests
# ============================================================================

class PayloadFactory:
    """Generate valid test payloads."""
    
    @staticmethod
    def scraper_finish_event(batch_id: str = "batch-001", deal_count: int = 5) -> Dict[str, Any]:
        """Generate Scraper.finish event."""
        deals = [
            {
                "url": f"https://store-{i}.com/deal-{i}",
                "store_id": f"store-{i:03d}",
                "title": f"Deal {i}",
                "price": 10.0 + i,
                "category": "food"
            }
            for i in range(deal_count)
        ]
        
        return {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "scraped_deals": deals,
            "status": "success"
        }
    
    @staticmethod
    def optimizer_ready_event(batch_id: str = "batch-001", deal_count: int = 5) -> Dict[str, Any]:
        """Generate Optimizer.ready event."""
        deals = [
            {
                "deal_id": f"deal-{i}",
                "store_id": f"store-{i:03d}",
                "ranking_score": 50 + i * 10,
                "recommendation_reason": f"Reason {i}"
            }
            for i in range(deal_count)
        ]
        
        return {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "optimized_deals": deals
        }
    
    @staticmethod
    def hotdeal_event(user_id: str = "user-alice", deal_id: str = "deal-0") -> Dict[str, Any]:
        """Generate Personalize.hotdeal event."""
        return {
            "user_id": user_id,
            "deal_id": deal_id,
            "timestamp": datetime.now().isoformat(),
            "deal_title": "50% off",
            "savings_estimate": 25.0,
            "deal_url": "https://store.com/deal",
            "store_id": "store-001",
            "confidence": 0.9
        }


# ============================================================================
# CLI & Main
# ============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    # Quick validation of payload examples
    print("Validating Scraper.finish payload...")
    payload = PayloadFactory.scraper_finish_event()
    validate_contract(payload, ServiceContract.SCRAPER_FINISH_SCHEMA, "Scraper.finish")
    print("✓ Valid\n")
    
    print("Validating Optimizer.ready payload...")
    payload = PayloadFactory.optimizer_ready_event()
    validate_contract(payload, ServiceContract.OPTIMIZER_READY_SCHEMA, "Optimizer.ready")
    print("✓ Valid\n")
    
    print("Validating Personalize.hotdeal payload...")
    payload = PayloadFactory.hotdeal_event()
    validate_contract(payload, ServiceContract.PERSONALIZE_HOTDEAL_SCHEMA, "Personalize.hotdeal")
    print("✓ Valid\n")
    
    print("All contracts validated successfully!")
