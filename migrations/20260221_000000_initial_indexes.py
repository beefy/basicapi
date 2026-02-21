"""Initial migration: Create indexes for better performance

Created: 2026-02-21T00:00:00
\"\"\"

from pymongo_migrate.actions import CreateIndex


def upgrade(db):
    \"\"\"Apply migration changes\"\"\"
    # Create indexes for status_updates
    db.status_updates.create_index(\"agent_name\")
    db.status_updates.create_index(\"timestamp\")
    
    # Create indexes for responses
    db.responses.create_index(\"agent_name\")
    db.responses.create_index(\"received_ts\")
    
    # Create indexes for system_info
    db.system_info.create_index(\"agent_name\")
    db.system_info.create_index(\"ts\")
    
    # Create unique index for heartbeat (ensures only one heartbeat per agent)
    db.heartbeat.create_index(\"agent_name\", unique=True)


def downgrade(db):
    \"\"\"Rollback migration changes\"\"\"
    # Drop indexes
    try:
        db.status_updates.drop_index(\"agent_name_1\")
        db.status_updates.drop_index(\"timestamp_1\")
        db.responses.drop_index(\"agent_name_1\")
        db.responses.drop_index(\"received_ts_1\")
        db.system_info.drop_index(\"agent_name_1\")
        db.system_info.drop_index(\"ts_1\")
        db.heartbeat.drop_index(\"agent_name_1\")
    except Exception as e:
        print(f\"Error dropping indexes: {e}\")
