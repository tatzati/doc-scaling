FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi 'prometheus-client>=0.21,<1.0' 'pydantic-settings>=2.6,<3.0' \
    'sqlalchemy>=2.0,<3.0' 'psycopg[binary]>=3.2,<4.0' 'uvicorn[standard]>=0.34,<1.0'

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
