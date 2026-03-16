from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    id = None
    userId = None
    providerId = None
    accountNumber = None
    status = None
    categoryCode = None
    ammount = None
    description = None
    category = None
    type = None
    date = None
    merchantName = None
    merchantAddress = None
    createdAt = None

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