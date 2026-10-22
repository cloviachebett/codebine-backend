release: python -c "import models; from database import create_tables; create_tables()"
web: uvicorn main:app --host 0.0.0.0 --port $PORT
