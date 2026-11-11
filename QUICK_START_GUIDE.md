# Quick verification guide

Use this checklist after starting StockLeague.

## Public pages

- Open `/` and confirm the home page loads.
- Open `/register` and create a test account.
- Sign in through `/login`.

## Authenticated pages

- Open `/dashboard` and confirm the portfolio loads.
- Open `/trade` and look up a symbol such as `AAPL`.
- Open `/news` and confirm article cards render.
- Open `/leagues` and confirm the league list loads.

## Navigation

- Confirm the brand link returns to `/home`.
- Confirm the dashboard icon opens `/dashboard`.
- Open the Trade and Community menus.
- Resize the browser below 992 pixels and confirm the mobile menu opens.
- Resize a laptop-width browser and confirm the navbar stays within the viewport.

## Troubleshooting

Restart the server after Python or template changes. Use `Ctrl+Shift+R` for a hard browser refresh. For dependency or database problems, see [DEV_SETUP.md](DEV_SETUP.md).
