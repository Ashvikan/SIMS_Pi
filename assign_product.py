from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
import pymongo

# MongoDB connection
client = pymongo.MongoClient("mongodb://192.168.8.200:27017/")
db = client["SIMS"]  # Database name
rfid_collection = db["rfid_mapping"]  # Collection for RFID-product mappings

reader = SimpleMFRC522()

try:
    print("Place your RFID card or chip near the reader to assign a product...")
    rfid_id, _ = reader.read()
    print(f"Detected RFID UID: {rfid_id}")

    product_id = input("Enter the Product ID to assign to this RFID: ")
    product_name = input("Enter the Product Name: ")

    # Save the mapping to the database
    rfid_collection.update_one(
        {"rfid_uid": str(rfid_id)},
        {"$set": {"product_id": product_id, "product_name": product_name}},
        upsert=True
    )

    print(f"Assigned Product '{product_name}' (ID: {product_id}) to RFID UID: {rfid_id}")
finally:
    GPIO.cleanup()
