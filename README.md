# Gmail Subscription Cleanup

A read-only Gmail inbox analyzer that scans recent email for recurring
newsletters and subscription senders, groups cleanup candidates, inspects
unsubscribe metadata, and generates a Markdown cleanup report.

## Safety Model

This project is read-only by design:

- Uses Gmail OAuth with the `https://www.googleapis.com/auth/gmail.readonly` scope
- Rejects unneeded or mutating Gmail scopes such as `gmail.modify` or `gmail.send`
- Reads message metadata through the Gmail API
- Does not send email
- Does not archive, label, move, delete, or otherwise modify mailbox messages

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

4. Create a Google Cloud OAuth client for a desktop app and download the client
   secret JSON file as `credentials.json` in the repo root.

5. Enable the Gmail API for the Google Cloud project.

6. Update `.env`:

   ```dotenv
   GMAIL_CREDENTIALS_FILE=credentials.json
   GMAIL_TOKEN_FILE=token.json
   GMAIL_USER_ID=me
   GMAIL_QUERY=newer_than:90d
   GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
   ```

`token.json` is created after the first OAuth login and is ignored by Git.

## Generate a Cleanup Report

Run the package:

```bash
gmail-subscription-cleanup --messages 250 --output cleanup-report.md
```

## Gmail Smoke Test

Use the read-only test script to authenticate, print latest inbox emails, and
print a cleanup report preview:

```bash
python scripts/test_gmail_readonly.py
```

The report groups candidates into:

- `Unsubscribe`
- `Keep but organize`
- `Needs human review`

Senders are only recommended for unsubscribe when unsubscribe metadata is
present. Transactional or operational messages, such as receipts, invoices,
security notices, support tickets, and account alerts, are routed to human
review instead of being treated as disposable.

## Test

```bash
python -m unittest discover
```
