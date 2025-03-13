from pymongo import MongoClient

# Step 1: Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  
db = client["database"]  
collection = db["collection"]  

# Step 2: Insert Key-Value Pairs
key_value_pairs = [
    {"key": "name", "value": 35},
    {"key": "age", "value": 30},
    {"key": "city", "value": 24}
]

# Insert multiple documents
result = collection.insert_many(key_value_pairs)
print("Inserted IDs:", result.inserted_ids)

# Step 3: Query the Collection
print("Stored Documents:")
for document in collection.find():
    print(document)

# Step 4: Close the Connection
client.close()
