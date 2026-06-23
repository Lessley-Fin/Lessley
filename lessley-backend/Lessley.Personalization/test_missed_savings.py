"""
Integration test for calculate_missed_savings_async function.
Tests the simplified category-name-based deal discovery logic.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from models.transaction import Transaction, TransactionAmount, AmountDetail
from services.processing_core_service import ProcessingCoreService
from services.mcc_service import MccService


async def test_calculate_missed_savings():
    """Test the calculate_missed_savings_async function with mock data."""

    # Setup mock MccService that translates numeric codes to category names
    mock_mcc_service = MagicMock(spec=MccService)
    mock_mcc_service.get_mcc = MagicMock(return_value={})
    mock_mcc_service.get_mcc_by_id = MagicMock(return_value="COFFEE_&_SNACKS")

    # Create service instance
    service = ProcessingCoreService(mock_mcc_service)

    # Create mock Store objects with category name strings
    store1 = MagicMock()
    store1.store_id = "store_1"
    store1.name = "Starbucks"
    store1.metadata = MagicMock()
    store1.metadata.mcc_codes = ["COFFEE_&_SNACKS"]

    store2 = MagicMock()
    store2.store_id = "store_2"
    store2.name = "Costa Coffee"
    store2.metadata = MagicMock()
    store2.metadata.mcc_codes = ["COFFEE_&_SNACKS"]

    store3 = MagicMock()
    store3.store_id = "store_3"
    store3.name = "McDonald's"
    store3.metadata = MagicMock()
    store3.metadata.mcc_codes = ["RESTAURANT"]

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

    # Create real Transaction object — categoryCode stays numeric, mcc_service translates it
    transaction = Transaction(
        id="txn_1",
        merchantName="STARBUCKS COFFEE #123",
        categoryCode="5462",
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
        mock_stores_list.to_list = AsyncMock(return_value=[store1, store2, store3])
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
        print("\n✓ Test Logic Executed Successfully!")
        print(f"  - Insights generated: {len(insights)}")
        if insights:
            print(f"  - Transaction ID: {insights[0].transaction_id}")
            print(f"  - Had discount: {insights[0].had_discount}")
            print(f"  - MCC code (category name): {insights[0].mcc_code}")
            print(f"  - Missed store discounts: {len(insights[0].missed_store_discont)} club(s)")
            for club_discount in insights[0].missed_store_discont:
                print(f"    - Club {club_discount.club_id}: {club_discount.store_count} store(s)")

        # Verify assertions
        assert len(insights) == 1, f"Expected 1 insight, got {len(insights)}"
        assert insights[0].transaction_id == "txn_1", "Transaction ID should match"
        assert insights[0].mcc_code == "COFFEE_&_SNACKS", "MCC code should be category name"

        # For category "COFFEE_&_SNACKS", both store1 and store2 should be found
        assert insights[0].had_discount, "Should have found deals for COFFEE_&_SNACKS"
        assert len(insights[0].missed_store_discont) > 0, "Should have found alternative stores"

        # Verify mcc_service was called to translate the numeric code
        mock_mcc_service.get_mcc_by_id.assert_called_with("5462")

        print("\n✓ All validation checks passed!")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_calculate_missed_savings())
    if result:
        print("\n" + "=" * 60)
        print("✓ INTEGRATION TEST SUCCESSFUL")
        print("=" * 60)
