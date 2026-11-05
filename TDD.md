# VyapaarFlow — Technical Design Document

**GitHub repository:** Add the public repository URL after publishing.  
**Live application:** Add the deployed URL if available.  
**Product statement:** Ordering that understands your business.

## 1. Context and objective
The proposed product addresses manual FMCG retailer ordering, where order information may arrive as informal messages and must be converted into structured order lines. This MVP focuses on the retailer catalogue, case-based ordering, text order capture, deterministic scheme calculation and order-desk review.

## 2. Scope and assumptions
The supplied client brief describes a distributor serving kirana retailers, with catalogue, stock, retailer pricing/schemes, credit, AI-assisted order capture, order-desk review and Tally handoff needs.

**MVP assumptions**
- The demo uses fictional products, prices, stock, retailer and credentials.
- Catalogue price is represented as a per-pack-unit dealer price; case value is calculated as pack price multiplied by units per case. Retailer order quantity is entered in cases.
- The demo contains one retailer and one order-desk account.
- Authentication is implemented as seeded username/password demo access, not OTP.
- The AI integration is Gemini 2.0 Flash when an API key is configured; otherwise a clearly labelled deterministic phrase-matching fallback is used.
- All AI-generated lines require retailer review; unclear quantities are not auto-submitted.
- The CSV export is a generic Tally handoff template, not a verified import specification.

## 3. Architecture
- **Presentation:** Flask-rendered Jinja templates, CSS and browser JavaScript.
- **Application layer:** Flask routes implement login, role checks, catalogue, order creation, AI capture, desk status updates and CSV export.
- **AI adapter:** Gemini API call for structured extraction; local fallback when unavailable.
- **Business rules:** Python scheme calculator and server-side stock/quantity checks.
- **Persistence:** SQLAlchemy ORM with SQLite by default.

Request flow: Browser → Flask route → validation/business rules → SQLAlchemy → SQLite. AI capture adds a server-side call to Gemini when configured; its structured output is shown for human review before order submission.

## 4. Data model
- **User:** username, password hash, role, retailer name, credit limit and credit used.
- **Product:** SKU, name, category, pack size, units per case, price, stock cases and scheme parameters.
- **Order:** retailer, creation timestamp, status, total and notes.
- **OrderItem:** order, product, case quantity, unit price and free-case quantity.

Relationships: one retailer can create many orders; each order has many order items; each order item references one product.

## 5. Main workflows
### Retailer catalogue and order
1. Retailer signs in.
2. Catalogue displays product pack, price, stock and active scheme.
3. Retailer selects case quantities.
4. Server validates positive quantities, quantity bounds and stock.
5. Server calculates applicable schemes and creates a pending order.
6. If the order exceeds available credit, its status becomes `Credit hold`.

### AI-assisted text capture
1. Retailer pastes a natural-language order message.
2. Gemini is asked to return catalogue-constrained SKU candidates, quantities, confidence and clarification flags.
3. If the API is unavailable or fails, the local phrase matcher is used and identified in the UI.
4. Retailer reviews matched lines and quantities.
5. Unclear lines are excluded until resolved; the retailer must confirm before an order is created.
6. Server validates stock and applies the same scheme rules as catalogue orders.

### Order desk and Tally handoff
1. Desk user views the order queue.
2. Desk can set status to pending review, approved, credit hold or rejected.
3. Desk exports order line data as CSV for mapping to the distributor's Tally process.

## 6. Scheme engine
Scheme calculations are deterministic and independent of the AI model:
- Buy X get Y: for the glucose biscuit example, each 10 purchased cases qualify for 1 free case.
- Slab discount: detergent/dishwash orders of 5 or more cases receive a 3% line discount.
- No scheme: no benefit is applied.
The current schema stores one simple scheme per product. Production schemes require validity dates, retailer eligibility, priority/stacking rules, tax treatment and a full audit trail.

## 7. AI behaviour and uncertainty
The AI is constrained to known catalogue SKUs. The expected output contains SKU, quantity, original text, confidence, alternatives and clarification status. The application does not automatically place an AI-generated order. When the model is unavailable, the app switches to a limited local phrase matcher and labels that mode. The fallback is not equivalent to a language model and may miss spelling, context or complex Hindi phrasing. Human review remains mandatory.

## 8. UI/UX decisions
- Mobile-first responsive layout for retailer use.
- Large touch targets and simple product cards.
- Price, pack size, stock and scheme appear together.
- A sticky cart summary reduces navigation.
- AI capture separates message entry from review and confirmation.
- Desktop order desk uses a compact queue table and clear status labels.
- The visual system uses a restrained green/neutral palette and high-contrast text.

## 9. Security and validation
- Passwords are stored as Werkzeug password hashes.
- Session-based role checks protect retailer and desk routes.
- Order creation validates product existence, integer quantity bounds and available stock on the server.
- Secrets are environment variables; `.env` is ignored by Git.
- Production requires OTP/identity provider, CSRF protection, rate limiting, HTTPS, managed secrets, audit logs and database backups.

## 10. Tests
The included pytest suite checks health endpoint, retailer login/catalogue access, buy-get scheme calculation, order creation and role protection. Run `pytest -q`. Record the actual result from the environment used for final submission; do not claim tests passed unless they were executed successfully.

## 11. Deliberate cuts and future work
**Not implemented in this MVP:** OTP delivery, photo OCR, voice transcription, salesman offline mode/sync, learned retailer aliases, multi-brand admin, Tally API integration, GST e-invoicing, van loading, delivery tracking, payment collection and automated 14-day no-order alerts.

**Next steps:** production identity and OTP, robust Hindi/English parsing with evaluation set, OCR/ASR pipelines, retailer-specific aliases with desk correction feedback, scheme validity/stacking engine, inventory reservation and concurrency control, credit ledger, Tally integration, offline sync, analytics and monitoring.

## 12. Demo data
The seeded catalogue and accounts are fictional. The retailer account has a ₹50,000 credit limit and ₹12,500 used credit. The products include glucose biscuits, detergent powder, tea leaves, snack mix and dishwash liquid. Tea is seeded with zero available cases to demonstrate out-of-stock handling.
