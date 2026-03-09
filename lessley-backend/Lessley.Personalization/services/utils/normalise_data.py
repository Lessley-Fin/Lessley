class NormaliseData:
    def __init__(self):
        self.id = None
        self.userId = None
        self.providerId = None
        self.accountNumber = None
        self.status = None
        self.categoryCode = None
        self.ammount = None
        self.description = None
        self.category = None
        self.type = None
        self.date = None
        self.merchantName = None
        self.merchantAddress = None
        self.createdAt = None

    def normalise_data(self, response):
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
        