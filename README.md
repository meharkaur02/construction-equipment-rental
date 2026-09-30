# Construction Equipment Rental

## Backend setup
1. Install PostgreSQL and create a database: `construction_equipment_rental`
2. `cd backend` (or wherever main.py lives)
3. `python -m venv venv && venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. Update the connection string in `app/database.py` with your Postgres credentials
6. Run the schema setup: `python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(engine)"`
7. `uvicorn main:app --reload`
8. Visit http://127.0.0.1:8000/docs

## Frontend setup
1. `cd frontend`
2. `npm install`
3. `npm run dev`
4. Visit http://localhost:5173

## Running tests
1. Create a second database: `construction_equipment_test`
2. `pytest -v`
