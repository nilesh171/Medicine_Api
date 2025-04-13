# Medicine API Deployment

This is a Flask-based API for suggesting medicines from the "A-Z Medicine Dataset of India" (Kaggle), deployed using Render. It provides fuzzy matching and related medicine suggestions.

## Usage
- Endpoint: `/api/medicines/suggest?query=<keyword>&limit=<number>`
- Example: `https://your-api.onrender.com/api/medicines/suggest?query=paracetamol&limit=5`

## Setup
1. Run `convert_to_sqlite.py` to create `medicines.db` from `A-Z_Dataset.csv`.
2. Deploy to Render using the provided files.

## License
MIT