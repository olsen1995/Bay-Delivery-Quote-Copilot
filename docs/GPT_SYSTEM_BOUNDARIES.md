# System Boundaries

- One pricing engine (quote_engine)
- GPT does NOT replace pricing logic
- Admin is operations only
- Customers use /quote
- GPT is internal tool only
- Jobs are the system anchor
- SQLite is source of truth

## Do NOT

- Create second pricing system
- Override repo pricing
- Expand admin into quoting
