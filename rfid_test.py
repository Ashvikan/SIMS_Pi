import paho.mqtt.client as mqtt
import time
from mfrc522 import SimpleMFRC522
from pymongo import MongoClient

# Configuration
MQTT_BROKER = "192.168.1.245"  # Update with your actual IP
MQTT_PORT = 1883
MQTT_TOPIC = "rfid/scan"
MONGO_URI = "mongodb://192.168.1.245:27017/"  # Update with your MongoDB URI
DATABASE_NAME = "SIMS"

# Initialize RFID Reader
reader = SimpleMFRC522()

# Initialize MQTT Client
mqtt_client = mqtt.Client()

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
rfid_mapping_collection = db.rfid_mapping
products_collection = db.products
audit_logs_collection = db.audit_logs  # New collection for audit logging

def publish_to_mqtt(rfid_uid, product_name):
    payload = {
        "rfid_uid": rfid_uid,
        "product_name": product_name,
        "timestamp": time.time()
    }
    mqtt_client.publish(MQTT_TOPIC, str(payload))
    print(f"Published to MQTT: {payload}")

def log_audit(rfid_uid, product_name, action, stock_level=None):
    log_entry = {
        "rfid_uid": rfid_uid,
        "product_name": product_name,
        "action": action,
        "stock_level": stock_level,
        "timestamp": time.time()
    }
    audit_logs_collection.insert_one(log_entry)
    print(f"Audit Log: {log_entry}")

def scan_rfid():
    try:
        print("Place your card near the reader...")
        rfid_uid, _ = reader.read()
        print(f"Card ID: {rfid_uid}")

        # Query MongoDB for RFID mapping
        mapping = rfid_mapping_collection.find_one({"rfid_uid": str(rfid_uid)})
        if mapping:
            product_id = mapping.get("product_id")
            product_name = mapping.get("product_name")
            print(f"RFID Mapped to Product: {product_name}")

            # Update stock level in products collection
            product = products_collection.find_one({"productId": int(product_id)})
            if product:
                if product["stockLevel"] > 0:
                    new_stock_level = product["stockLevel"] - 1
                    products_collection.update_one(
                        {"productId": int(product_id)},
                        {"$set": {"stockLevel": new_stock_level}}
                    )
                    print(f"Updated Stock Level: {new_stock_level} for Product: {product_name}")

                    # Publish to MQTT
                    publish_to_mqtt(rfid_uid, product_name)

                    # Log audit
                    log_audit(rfid_uid, product_name, "stock_decrement", new_stock_level)
                else:
                    print(f"Stock level is zero for Product: {product_name}. Cannot scan.")
                    # Log failed scan due to zero stock
                    log_audit(rfid_uid, product_name, "failed_scan", product["stockLevel"])
            else:
                print("Product not found in database.")
                # Log failed scan due to missing product
                log_audit(rfid_uid, None, "failed_scan")
        else:
            print("RFID not mapped to any product.")
            # Log failed scan due to missing mapping
            log_audit(rfid_uid, None, "failed_scan")

    except Exception as e:
        print(f"Error: {e}")
        log_audit(None, None, "error", str(e))

if __name__ == "__main__":
    try:
        # Connect to MQTT broker
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"Connected to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")

        while True:
            scan_rfid()
            time.sleep(1)

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        mongo_client.close()
