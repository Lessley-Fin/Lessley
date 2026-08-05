from datetime import date, datetime
from pydantic import BaseModel, field_validator


class AmountDetail(BaseModel):
    amount: float | None = None
    currency: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        # Convert empty string to None
        if v == "" or v is None:
            return None
        # Convert to float if it's a valid number
        return float(v)


class TransactionAmount(BaseModel):
    originalAmount: AmountDetail | None = None
    chargedAmount: AmountDetail | None = None


class TransactionDescription(BaseModel):
    initialClean: str | None = None
    fixedText: str | None = None
    description: str | None = None


class TransactionCategory(BaseModel):
    categorizedBy: str | None = None
    sub: str | None = None
    main: str | None = None


class TransactionDates(BaseModel):
    valueDate: date | None = None
    bookingDate: date | None = None
    transactionDate: date | None = None


class MerchantAddress(BaseModel):
    country: str | None = None
    townName: str | None = None


class Transaction(BaseModel):
    id: str | None = None
    userId: str | None = None
    providerId: str | None = None
    accountId: str | None = None
    accountNumber: str | None = None
    status: str | None = None
    categoryCode: str | None = None

    # Use the nested models here
    amount: TransactionAmount | None = None
    description: TransactionDescription | None = None
    category: TransactionCategory | None = None

    type: str | None = None
    date: TransactionDates | None = None

    merchantName: str | None = None
    merchantAddress: MerchantAddress | None = None
    createdAt: datetime | None = None


class PaginatedTransactionsResponse(BaseModel):
    items: list[Transaction] = []
    nextPage: str | None = None

    def deserialize(response) -> "PaginatedTransactionsResponse":
        """Factory method to create an empty PaginatedTransactionsResponse."""
        json_data = response.json()
        return PaginatedTransactionsResponse.model_validate(json_data)

    @staticmethod
    def normalize_data(response) -> list["Transaction"]:
        """
        Extracts the data array and converts it into Transaction objects.
        """
        if (isinstance(response, dict)) and ("items" in response):
            raw_transactions = response["items"]
        else:
            raw_transactions = PaginatedTransactionsResponse.deserialize(response).items
        transactions = [Transaction.model_validate(t) for t in raw_transactions]

        return transactions
