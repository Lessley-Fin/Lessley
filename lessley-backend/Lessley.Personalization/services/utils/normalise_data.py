from dataclasses import dataclass

@dataclass
class Transaction:
    id: str | None = None
    userId: str | None = None
    providerId: str | None = None
    accountNumber: str | None = None
    status: str | None = None
    categoryCode: str | None = None
    ammount: float | None = None
    description: str | None = None
    category: str | None = None
    type: str | None = None
    date: str | None = None
    merchantName: str | None = None
    merchantAddress: str | None = None
    createdAt: str | None = None

class NormaliseData:
    
    @staticmethod
    def normalise_data(response) -> list[Transaction]:
        """
        Normalises the input data by filtering out any unnecessary transactions data
        """
        transactions = response.json().get("items", [])
        # We filter kwargs to only include keys that exist in the dataclass
        valid_keys = Transaction.__dataclass_fields__.keys()

        transactions = [Transaction(**{k: v for k, v in t.items() if k in valid_keys})
             for t in transactions]

        return transactions