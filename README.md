# Outlook Daily Digest

A read-only Outlook productivity assistant that reads Microsoft Graph inbox and
calendar data, groups email by customer, highlights likely action items and
blockers, and generates a Markdown daily report.

## Safety Model

This project is read-only by design:

- Uses Microsoft Graph delegated scopes: `User.Read`, `Mail.Read`, `Calendars.Read`
- Rejects mutating scopes such as `Mail.Send` or `Calendars.ReadWrite`
- Implements only GET requests against Microsoft Graph
- Does not send email
- Does not create, update, or delete calendar events

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the package and dependencies:

   ```bash
   pip install -e .
   ```

3. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

4. Register an app in Microsoft Entra ID, enable public client flows for
   device-code login, and add delegated Microsoft Graph permissions for
   `User.Read`, `Mail.Read`, and `Calendars.Read`.

5. Update `.env`:

   ```dotenv
   MS_GRAPH_CLIENT_ID=your-application-client-id
   MS_GRAPH_TENANT_ID=common
   MS_GRAPH_SCOPES=User.Read Mail.Read Calendars.Read
   OUTLOOK_TIMEZONE=America/Chicago
   ```

## Generate a Report

Run the package:

```bash
outlook-daily-digest --date 2026-05-21 --output daily-report.md
```

The first run starts a Microsoft device-code login. The token cache is stored
locally at `.msal_token_cache.json`, which is ignored by Git.

## Test

```bash
python -m unittest discover
```
