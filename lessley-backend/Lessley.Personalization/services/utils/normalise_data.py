from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    id: Optional[str] = None
    userId: Optional[str] = None
    providerId: Optional[str] = None
    accountNumber: Optional[str] = None
    status: Optional[str] = None
    categoryCode: Optional[str] = None
    ammount: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    date: Optional[str] = None
    merchantName: Optional[str] = None
    merchantAddress: Optional[str] = None
    createdAt: Optional[str] = None

class NormaliseData:
    
    @staticmethod
    def normalise_data(response) -> list[Transaction]:
        """
        Normalises the input data by filtering out any unnecessary transactions data
        """
        transactions = response.json().get("items", [])
        simplified_transactions = [
            Transaction(
                id = transaction.get("id"),
                userId = transaction.get("userId"),
                providerId = transaction.get("providerId"),
                accountNumber = transaction.get("accountNumber"),
                status = transaction.get("status"),
                categoryCode = transaction.get("categoryCode"),
                ammount = transaction.get("ammount"),
                description = transaction.get("description"),
                category = transaction.get("category"),
                type = transaction.get("type"),
                date = transaction.get("date"),
                merchantName = transaction.get("merchantName"),
                merchantAddress = transaction.get("merchantAddress"),
                createdAt = transaction.get("createdAt"),
            )
            for transaction in transactions
        ]
        return simplified_transactions