# pyrefly: ignore [missing-import]
from app.main import app
for route in app.routes:
    print(route.path, getattr(route, 'methods', ''))
