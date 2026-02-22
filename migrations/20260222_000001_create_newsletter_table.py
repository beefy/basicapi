"""Create email newsletter table

Created: 2026-02-22T00:00:01
"""

from pymongo_migrate.actions import CreateIndex


def upgrade(db):
    """Apply migration changes"""
    # Create unique index for email newsletter (ensures no duplicate emails)
    db.newsletter_emails.create_index("email", unique=True)


def downgrade(db):
    """Rollback migration changes"""
    # Drop the newsletter_emails collection entirely
    try:
        db.newsletter_emails.drop()
    except Exception as e:
        print(f"Error dropping newsletter_emails collection: {e}")