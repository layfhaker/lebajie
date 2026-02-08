# API Guide

The HTTP API starts together with the bot on port `8080`.

Base URL:
- `http://localhost:8080`

## 1. Get all booking objects

`GET /api/objects`

Example:

```bash
curl http://localhost:8080/api/objects
```

Response:
- JSON array of objects.
- Fields: `id`, `name`, `category`, `capacity`, `price_weekday`, `price_weekend`, `description`.

## 2. Get object calendar

`GET /api/calendar/{object_id}?month=YYYY-MM`

Params:
- `object_id` (path): object ID.
- `month` (query, optional): month in `YYYY-MM` format.
If omitted, current month is used.

Example:

```bash
curl "http://localhost:8080/api/calendar/1?month=2026-02"
```

Response:
- JSON object in format `{ "YYYY-MM-DD": "status" }`.
- Status values:
- `available` - free day.
- `partially` - pending booking request exists.
- `booked` - confirmed booking exists.

## Errors

For `/api/calendar/{object_id}`:
- `400` + `{"error":"Invalid object_id"}`.
- `404` + `{"error":"Object not found"}`.
- `400` + `{"error":"Invalid month format. Use YYYY-MM"}`.

## CORS

API returns:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type`
