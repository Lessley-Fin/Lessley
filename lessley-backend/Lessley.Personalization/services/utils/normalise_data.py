from dataclasses import dataclass

@dataclass
class NormaliseData:
    id: str =  None
    userId: str = None
    providerId: str = None
    accountNumber: str = None
    status: str = None
    categoryCode: str = None
    ammount: float = None
    description: str = None
    category: str = None
    type: str = None
    date: str = None
    merchantName: str = None
    merchantAddress: str = None
    createdAt: str = None

    def normalise_data(self, response) -> list[dict]:
        """
        Normalises the input data by filtering out any unnecessary transactions data
        """
        transactions = response.json().get("items", [])
        simplified_transactions = [
            {
                "id": transaction.get("id"),
                "userId": transaction.get("userId"),
                "providerId": transaction.get("providerId"),
                "accountNumber": transaction.get("accountNumber"),
                "status": transaction.get("status"),
                "categoryCode": transaction.get("categoryCode"),
                "ammount": transaction.get("ammount"),
                "description": transaction.get("description"),
                "category": transaction.get("category"),
                "type": transaction.get("type"),
                "date": transaction.get("date"),
                "merchantName": transaction.get("merchantName"),
                "merchantAddress": transaction.get("merchantAddress"),
                "createdAt": transaction.get("createdAt"),
            }
            for transaction in transactions
        ]
        return simplified_transactions
        