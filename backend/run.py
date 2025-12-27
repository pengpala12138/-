# backend/run.py
from . import create_app  # 点号代表「当前包（backend）」

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)