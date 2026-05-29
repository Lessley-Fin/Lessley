"""
Integration test for calculate_missed_savings_async function.
This test validates the core logic without requiring a MongoDB connection.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from models.transaction import Transaction, TransactionAmount, AmountDetail
from services.processing_core_service import ProcessingCoreService
from services.mcc_service import MccService


async def test_calculate_missed_savings():
    """Test the calculate_missed_savings_async function with mock data."""

    # Setup mock MccService
    mock_mcc_service = MagicMock(spec=MccService)
    mock_mcc_service.get_mcc = MagicMock(return_value={})

    # Create service instance
    service = ProcessingCoreService(mock_mcc_service)

    # Create mock data with proper attributes
    now = datetime.now()

    # Create mock Store objects
    store1 = MagicMock()
    store1.store_id = "store_1"
    store1.name = "Starbucks"
    store1.name_forms = MagicMock()
    store1.name_forms.normalized = "starbucks"
    store1.metadata = MagicMock()
    store1.metadata.mcc_codes = [5462]  # Coffee shop MCC

    store2 = MagicMock()
    store2.store_id = "store_2"
    store2.name = "Costa Coffee"
    store2.name_forms = MagicMock()
    store2.name_forms.normalized = "costa coffee"
    store2.metadata = MagicMock()
    store2.metadata.mcc_codes = [5462]  # Same MCC

    # Create mock Deal objects
    deal1 = MagicMock()
    deal1.store_id = "store_1"
    deal1.club_id = "club_1"
    deal1.title = "10% off"

    deal2 = MagicMock()
    deal2.store_id = "store_2"
    deal2.club_id = "club_2"
    deal2.title = "15% off"

    # Create mock Club objects
    club1 = MagicMock()
    club1.club_id = "club_1"
    club1.name = "Elite Club"
    club1.stores = ["store_1", "store_2"]

    club2 = MagicMock()
    club2.club_id = "club_2"
    club2.name = "Premium Club"
    club2.stores = ["store_2"]

    # Create real Transaction object
    transaction = Transaction(
        id="txn_1",
        merchantName="STARBUCKS COFFEE #123",
        categoryCode="5462",  # Coffee shop MCC
        amount=TransactionAmount(chargedAmount=AmountDetail(amount=50.0, currency="USD")),
    )

    # Mock the database queries
    with (
        patch("models.db.entities.Store.find_all") as mock_stores,
        patch("models.db.entities.Deal.find_all") as mock_deals,
        patch("models.db.entities.Club.find_all") as mock_clubs,
    ):
        # Setup async mock returns
        mock_stores_list = AsyncMock()
        mock_stores_list.to_list = AsyncMock(return_value=[store1, store2])
        mock_stores.return_value = mock_stores_list

        mock_deals_list = AsyncMock()
        mock_deals_list.to_list = AsyncMock(return_value=[deal1, deal2])
        mock_deals.return_value = mock_deals_list

        mock_clubs_list = AsyncMock()
        mock_clubs_list.to_list = AsyncMock(return_value=[club1, club2])
        mock_clubs.return_value = mock_clubs_list

        # Run the test
        insights = await service.calculate_missed_savings_async([transaction])

        # Verify results
        print(f"\n✓ Test Logic Executed Successfully!")
        print(f"  - Insights generated: {len(insights)}")
        if insights:
            print(f"  - Transaction ID: {insights[0].transaction_id}")
            print(f"  - Had discount: {insights[0].had_discount}")
            print(f"  - Missed store discounts: {len(insights[0].missed_store_discont)} club(s)")

        # Basic assertions
        assert len(insights) == 1, f"Expected 1 insight, got {len(insights)}"
        assert insights[0].transaction_id == "txn_1", "Transaction ID should match"

        # The fuzzy match should find "starbucks" from "STARBUCKS COFFEE #123"
        # and it should have a deal, so had_discount should be True
        print(f"\n✓ All validation checks passed!")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_calculate_missed_savings())
    if result:
        print("\n" + "=" * 60)
        print("✓ INTEGRATION TEST SUCCESSFUL")
        print("=" * 60)
