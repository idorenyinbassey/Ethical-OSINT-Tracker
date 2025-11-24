Alembic migrations directory.

Generate initial migration after setting DB_URL env:

```
alembic revision --autogenerate -m "init"
alembic upgrade head
```

Ensure virtual env activated and models imported in env.py.
