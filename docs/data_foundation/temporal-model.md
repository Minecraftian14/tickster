# Temporal Model

A record can carry several different notions of time:

- **event_time** — when the real-world event occurred
- **effective_time** — when an action became effective
- **published_at** — when information was published
- **observed_at** — when a market observation occurred
- **retrieved_at** — when our collector obtained it
- **period_start / period_end** — period described by the record

For point-in-time knowledge queries, `available_at` is derived in this order:

1. `published_at`
2. `received_at`
3. `observed_at`
4. `effective_time`
5. `retrieved_at`

This keeps late retrieval from falsely moving an information event earlier/later in historical simulation.
