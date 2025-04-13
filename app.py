from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re
from functools import lru_cache

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins

# Cache fuzzy matching results
@lru_cache(maxsize=1000)
def cached_fuzzy_match(query, limit):
    query = query.lower()
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

    # Connect to database for each request
    conn = sqlite3.connect('medicines.db')
    suggestions = []
    seen_compositions = set()
    seen_names = set()

    # Get fuzzy matches
    matches = cached_fuzzy_match(query, limit)

    # Process fuzzy matches
    for medicine_name, score in matches:
        if score >= min_score:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM medicines WHERE name = ? AND Is_discontinued = 0",
                (medicine_name,)
            )
            row = cursor.fetchone()
            if row:
                suggestion = {
                    'id': row[0],
                    'name': row[1],
                    'price': row[2],
                    'Is_discontinued': bool(row[3]),
                    'manufacturer_name': row[4],
                    'type': row[5],
                    'pack_size_label': row[6],
                    'short_composition1': row[7],
                    'short_composition2': row[8],
                    'name_lower': row[9],
                    'match_score': score
                }
                suggestions.append(suggestion)
                seen_names.add(medicine_name)
                if row[7] and row[7] != 'None':  # short_composition1
                    seen_compositions.add(row[7])
                if row[8] and row[8] != 'None':  # short_composition2
                    seen_compositions.add(row[8])

    # Add related medicines
    related_limit = min(limit, 5)
    if seen_compositions:
        placeholders = ','.join('?' * len(seen_compositions))
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT * FROM medicines
            WHERE (short_composition1 IN ({placeholders})
                   OR short_composition2 IN ({placeholders}))
            AND name NOT IN ({','.join('?' * len(seen_names))})
            AND Is_discontinued = 0
            LIMIT ?
            """,
            list(seen_compositions) + list(seen_compositions) + list(seen_names) + [related_limit]
        )
        rows = cursor.fetchall()
        for row in rows:
            suggestion = {
                'id': row[0],
                'name': row[1],
                'price': row[2],
                'Is_discontinued': bool(row[3]),
                'manufacturer_name': row[4],
                'type': row[5],
                'pack_size_label': row[6],
                'short_composition1': row[7],
                'short_composition2': row[8],
                'name_lower': row[9],
                'match_score': 0
            }
            suggestions.append(suggestion)

    conn.close()

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
