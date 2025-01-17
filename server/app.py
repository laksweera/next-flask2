from flask import Flask, jsonify
from pymongo import MongoClient
import pandas as pd
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# MongoDB Configuration
MONGO_URI = "mongodb+srv://dbUser:12345@clusterpdf.nm0zm.mongodb.net/?retryWrites=true&w=majority&appName=Clusterpdf"  # Replace with your MongoDB connection string
DATABASE_NAME = "bills_database"
COLLECTION_NAME = "bills_collection"

def get_top_10_cheapest_items():
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        # Fetch data from the collection
        cursor = collection.find({}, {"_id": 0})
        all_items = []
        for document in cursor:
            if "Purchased Items" in document:
                purchased_items = document["Purchased Items"]
                all_items.extend(purchased_items)

        # Check if items are found
        if not all_items:
            return {"success": False, "error": "No purchased items found in the database."}

        # Create a DataFrame
        df = pd.DataFrame(all_items)

        # Validate columns exist
        if not {"Item Name", "Amount (LKR)", "Qty"}.issubset(df.columns):
            return {"success": False, "error": "Required columns are missing from the data."}

        # Convert columns to numeric
        df['Amount (LKR)'] = pd.to_numeric(df['Amount (LKR)'], errors='coerce')
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce')

        # Remove rows with invalid or missing data
        df.dropna(subset=['Amount (LKR)', 'Qty'], inplace=True)
        df = df[df['Qty'] > 0]  # Remove entries with zero or negative quantity

        # Calculate Cheapness Score
        df['Cheapness Score'] = df['Amount (LKR)'] / df['Qty']

        # Aggregate data by Item Name
        df_aggregated = df.groupby('Item Name').agg(
            {'Cheapness Score': 'min', 'Qty': 'sum', 'Amount (LKR)': 'sum'}
        ).reset_index()

        # Get top 10 cheapest items
        top_10_items = df_aggregated.sort_values(by='Cheapness Score', ascending=True).head(10)

        # Close the database connection
        client.close()

        return {"success": True, "data": top_10_items.to_dict(orient='records')}

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/api/top-cheapest-items', methods=['GET'])
def top_cheapest_items():
    result = get_top_10_cheapest_items()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
