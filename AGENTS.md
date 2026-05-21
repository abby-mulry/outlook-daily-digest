# Gmail Subscription Cleanup

Build a read-only Gmail subscription cleanup assistant.

Goals:
- Read Gmail inbox
- Scan recent email for recurring newsletters and subscription senders
- Group candidates into Unsubscribe, Keep but organize, and Needs human review
- Inspect unsubscribe metadata before recommending unsubscribe
- Avoid classifying transactional or operational mail as disposable
- Output a markdown cleanup report

Constraints:
- Read-only
- No sending emails
- No mailbox modifications
