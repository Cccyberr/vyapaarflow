# VyapaarFlow
**Ordering that understands your business.**

VyapaarFlow is a responsive FMCG retailer ordering MVP. Retailers can browse a seeded catalogue, view stock and schemes, build case-based orders, and convert a text message into an editable draft. An order-desk user can review order status and export line items as CSV for a Tally handoff.

## Features
- Role-based demo sign-in: retailer and order desk.
- Retailer catalogue with SKU, case pack, price, available stock and scheme.
- Server-side stock and quantity validation.
- Deterministic scheme engine: buy-10-get-1 and 3% slab discount at 5+ cases.
- AI-assisted text order capture through Gemini 2.0 Flash when `GEMINI_API_KEY` is configured.
- Transparent local phrase-matching fallback when no AI key is configured or the AI call fails. The interface identifies the parser source.
- Human review before AI-assisted order submission.
- Order desk status management and CSV export.
- SQLite persistence, seeded demo data, pytest tests.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Open http://127.0.0.1:5000.

Demo credentials:
- Retailer: `retailer` / `retail123`
- Order desk: `desk` / `desk123`

To enable the Gemini parser, add a valid `GEMINI_API_KEY` to `.env` and install dependencies. Without the key, the app uses the explicitly labelled local fallback.

## Test
```bash
pytest -q
```

## Important demo limitations
- Demo credentials are seeded and not suitable for production.
- OTP delivery, password reset and production identity management are not implemented.
- The AI input is text-only; photo OCR, voice transcription, and offline salesman sync are not implemented.
- The local fallback is a small phrase matcher, not a language model. It is clearly labelled.
- Retailer-specific learned aliases, Tally API integration, GST invoice generation, van loading, messaging integrations and delivery tracking are outside this MVP.
- Product pricing, stock, schemes and users are fictional sample data.
- Prices are displayed per pack unit with the calculated case value; order quantities are cases.
- Credit is shown to the retailer, and a credit hold is applied to orders exceeding available credit. This demo does not maintain a full credit ledger or automatically decrement stock.
- CSV is a Tally handoff template, not a verified Tally import format. Confirm mapping with the customer's Tally configuration.

## Security notes
Use a strong `SECRET_KEY`, HTTPS, managed secrets, real OTP/identity provider, CSRF protection, rate limiting, audit logging and database backups before production. Never commit `.env` or real customer information.
