# Corporate Actions and Company Events

Corporate actions and company events are separate canonical domains.

## CorporateAction

Examples:

- dividends
- bonuses
- splits
- rights issues
- demergers
- other exchange-published actions

Sources currently wired:

- Upstox `.../fundamentals/:isin/corporate-actions`
- NSE archive `corp_actions`

Upstox documents dividend/bonus/split/rights events with announcement, ex and record dates plus amount/ratio details. The NSE corporate-action report exposes purpose, ex-date, record date and book-closure fields. Keep raw source fields even when the canonical model does not yet promote a field.

## CompanyEvent

This is broader than corporate actions. Current collection targets:

- NSE corporate announcements
- NSE board meetings

Future event types can be added without changing the provider interface:

- financial results
- management changes
- acquisitions/mergers
- governance events
- insider disclosures
- regulatory events
- rating changes

The canonical event keeps a stable `event_id`, subject/description, optional URL, raw details, and provenance.
