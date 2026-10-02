# Domain contracts

The public application should depend on these domain-level operations rather than provider-specific APIs.

## Instruments

- `find_instruments(query)`
- `get_instrument(instrument_id)`
- `map_identifiers(symbol, isin, provider_key)`
- `list_active_equities()`

## Market

- `get_daily_bars(instrument, start, end, sources=...)`
- `get_intraday_bars(instrument, start, end, interval, sources=...)`
- `get_eod_statistics(date, sources=...)`

## Corporate actions

- `get_corporate_actions(instrument, start, end, sources=...)`

## Fundamentals

- `get_company_profile(instrument, sources=...)`
- `get_income_statements(instrument, frequency=..., statement_type=..., sources=...)`
- `get_balance_sheets(...)`
- `get_cash_flows(...)`
- `get_key_ratios(...)`

## Shareholding

- `get_shareholding_history(instrument, sources=...)`

## Company events / filings

- `get_announcements(instrument, start, end, sources=...)`
- `get_board_meetings(instrument, start, end, sources=...)`
- `get_filings(instrument, start, end, sources=...)`
- `get_document(document_id)`

## News

- `get_news(instruments, start, end, sources=...)`

## Macro

- `get_macro_series(series_id, start, end, sources=...)`

Every operation returns a domain result containing canonical records, raw evidence, and errors.
