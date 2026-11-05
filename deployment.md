# Deployment and local setup

## Local setup
1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:
   - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`
   - Windows: `python -m venv .venv && .venv\Scripts\activate`
3. Install packages: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Set `SECRET_KEY` to a long random value. Add `GEMINI_API_KEY` to enable Gemini text parsing.
6. Run `python app.py`.
7. Visit `http://127.0.0.1:5000`.

## Demo logins
- Retailer: username `retailer`, password `retail123`
- Order desk: username `desk`, password `desk123`

## Environment variables
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key |
| `DATABASE_URL` | SQLAlchemy database connection string |
| `GEMINI_API_KEY` | Optional Gemini API key for AI text parsing |
| `FLASK_DEBUG` | Enable local Flask debug mode |
| `PORT` | HTTP port |

Do not put secret values in this document or commit `.env`.

## Deployment notes
The app can be deployed to a Python web service that supports Flask. Configure the environment variables in the hosting provider's secret manager and use a persistent database volume or managed PostgreSQL database. Set the start command to `gunicorn app:app` after adding `gunicorn` to the requirements. Run behind HTTPS. SQLite is intended for local/demo use; use managed PostgreSQL for multi-instance production deployment.

No public deployment URL is provided in this package. Add the GitHub repository URL and live application URL to the top of the TDD after publishing/deploying.
