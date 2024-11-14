from datetime import datetime
import math
from models import Receipt


class ReceiptProcessor:
    @staticmethod
    def calculate_points(receipt: Receipt) -> int:
        points = 0

        # Rule 1: One point for every alphanumeric character in the retailer name
        points += sum(1 for char in receipt.retailer if char.isalnum())

        # Rule 2: 50 points if the total is a round dollar amount with no cents
        total_float = float(receipt.total)
        if total_float.is_integer():
            points += 50

        # Rule 3: 25 points if the total is a multiple of 0.25
        if total_float % 0.25 == 0:
            points += 25

        # Rule 4: 5 points for every two items on the receipt
        points += (len(receipt.items) // 2) * 5

        # Rule 5: If the trimmed length of the item description is a multiple of 3,
        # multiply the price by 0.2 and round up to the nearest integer
        for item in receipt.items:
            trimmed_length = len(item.shortDescription.strip())
            if trimmed_length % 3 == 0:
                points += math.ceil(float(item.price) * 0.2)

        # Rule 6: 6 points if the day in the purchase date is odd
        purchase_date = datetime.strptime(receipt.purchaseDate, "%Y-%m-%d")
        if purchase_date.day % 2 == 1:
            points += 6

        # Rule 7: 10 points if the time of purchase is between 2:00pm and 4:00pm
        purchase_time = datetime.strptime(receipt.purchaseTime, "%H:%M")
        if 14 <= purchase_time.hour < 16:  # Changed to exclude 4:00pm
            points += 10

        return points
