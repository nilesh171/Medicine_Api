from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import sqlite3
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re
from functools import lru_cache

app = Flask(__name__)
CORS(app)  # Enable CORS for website integration

# Load the dataset from SQLite
try:
    conn = sqlite3.connect('medicines.db')
    df = pd.read_sql('SELECT * FROM medicines', conn)
    conn.close()
    print("Dataset loaded from SQLite successfully")
except Exception as e:
    print(f"Error loading dataset: {e}")
    df = pd.DataFrame()

# Helper function to convert dataframe row to dict
def row_to_dict(row):
    result = row.to_dict()
    return result

# Cache fuzzy matching results
@lru_cache(maxsize=1000)
def cached_fuzzy_match(query, limit):
    query = query.lower()
    # Pre-filter: match names starting with first 3 chars
    conn = sqlite3.connect('medicines.db')
    if len(query) >= 3:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM medicines WHERE name_lower LIKE ?",
            (f"{query[:3]}%",)
        )
        candidates = [row[0] for row in cursor.fetchall()]
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM medicines")
        candidates = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Fuzzy matching with faster scorer
    matches = process.extract(
        query,
        candidates,
        scorer=fuzz.partial_ratio,
        limit=limit
    )
    return matches

# Endpoint: Suggest medicines with related medicines
@app.route('/api/medicines/suggest', methods=['GET'])
def suggest_medicines():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    limit = request.args.get('limit', 10, type=int)
    min_score = 60

    if 'name' not in df.columns:
        return jsonify({'error': 'Dataset missing name column'}), 500

    # Get fuzzy matches
    matches = cached_fuzzy_match(query, limit)

    # Collect suggestions
    suggestions = []
    seen_compositions = set()
    seen_names = set()

    # Process fuzzy matches
    conn = sqlite3.connect('medicines.db')
    for medicine_name, score in matches:
        if score >= min_score:
            query_df = pd.read_sql(
                "SELECT * FROM medicines WHERE name = ? AND Is_discontinued = 0",
                conn,
                params=(medicine_name,)
            )
            if not query_df.empty:
                medicine_row = query_df.iloc[0]
                suggestion = row_to_dict(medicine_row)
                suggestion['match_score'] = score
                suggestions.append(suggestion)
                seen_names.add(medicine_name)
                if pd.notna(medicine_row['short_composition1']):
                    seen_compositions.add(medicine_row['short_composition1'])
                if pd.notna(medicine_row['short_composition2']):
                    seen_compositions.add(medicine_row['short_composition2'])

    # Add related medicines
    related_limit = min(limit, 5)
    if seen_compositions:
        placeholders = ','.join('?' * len(seen_compositions))
        related_df = pd.read_sql(
            f"""
            SELECT * FROM medicines
            WHERE (short_composition1 IN ({placeholders})
                   OR short_composition2 IN ({placeholders}))
            AND name NOT IN ({','.join('?' * len(seen_names))})
            AND Is_discontinued = 0
            LIMIT ?
            """,
            conn,
            params=list(seen_compositions) + list(seen_compositions) + list(seen_names) + [related_limit]
        )
        for _, row in related_df.iterrows():
            suggestion = row_to_dict(row)
            suggestion['match_score'] = 0
            suggestions.append(suggestion)

    conn.close()

    # Prepare response
    response = {
        'query': query,
        'suggestions': suggestions[:limit],
        'total': len(suggestions)
    }
    if not suggestions:
        response['message'] = 'No medicines found. Try a different keyword.'

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)