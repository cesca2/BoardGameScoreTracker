from api import create_app
from api.config import (
    API_HOST,
    API_PORT,
)

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host=API_HOST, port=API_PORT)
