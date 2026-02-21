#!/usr/bin/env python3
\"\"\"
Database migration management script for BasicAPI

Usage:
    python migrate.py create <migration_name>  # Create a new migration
    python migrate.py up                       # Run all pending migrations
    python migrate.py down                     # Rollback last migration
    python migrate.py status                   # Show migration status
\"\"\"

import os
import sys
from datetime import datetime
from pymongo_migrate.migrate import Migrate
from pymongo_migrate.config import Configuration
from pymongo import MongoClient

# Add the app directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings


def create_migration(name: str):
    \"\"\"Create a new migration file\"\"\"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f\"{timestamp}_{name}.py\"
    filepath = os.path.join('migrations', filename)
    
    template = f'''\"\"\"Migration: {name}

Created: {datetime.now().isoformat()}
\"\"\"

from pymongo_migrate.actions import CreateIndex, DropIndex, CreateCollection, DropCollection


def upgrade(db):
    \"\"\"Apply migration changes\"\"\"
    # Add your upgrade logic here
    pass


def downgrade(db):
    \"\"\"Rollback migration changes\"\"\"
    # Add your downgrade logic here
    pass
'''
    
    os.makedirs('migrations', exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(template)
    
    print(f\"Created migration: {filepath}\")


def run_migrations():
    \"\"\"Run all pending migrations\"\"\"
    config = Configuration()
    config.host = settings.mongodb_url.replace('mongodb://', '').split('/')[0].split(':')[0]
    config.port = int(settings.mongodb_url.replace('mongodb://', '').split('/')[0].split(':')[1]) if ':' in settings.mongodb_url.replace('mongodb://', '').split('/')[0] else 27017
    config.database = settings.database_name
    config.migrations_dir = 'migrations'
    
    migrate = Migrate(config)
    migrate.run()
    print(\"Migrations completed\")


def rollback_migration():
    \"\"\"Rollback the last migration\"\"\"
    config = Configuration()
    config.host = settings.mongodb_url.replace('mongodb://', '').split('/')[0].split(':')[0]
    config.port = int(settings.mongodb_url.replace('mongodb://', '').split('/')[0].split(':')[1]) if ':' in settings.mongodb_url.replace('mongodb://', '').split('/')[0] else 27017
    config.database = settings.database_name
    config.migrations_dir = 'migrations'
    
    migrate = Migrate(config)
    migrate.rollback()
    print(\"Rollback completed\")


def migration_status():
    \"\"\"Show migration status\"\"\"
    config = Configuration()
    config.host = settings.mongodb_url.replace('mongodb://', '').split('/')[0].split(':')[0]
    config.port = int(settings.mongodb_url.replace('mongodb://', '').split('/')[0].split(':')[1]) if ':' in settings.mongodb_url.replace('mongodb://', '').split('/')[0] else 27017
    config.database = settings.database_name
    config.migrations_dir = 'migrations'
    
    migrate = Migrate(config)
    status = migrate.status()
    
    print(\"Migration Status:\")
    for migration in status:
        print(f\"  {migration}\")


if __name__ == \"__main__\":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == \"create\":
        if len(sys.argv) < 3:
            print(\"Usage: python migrate.py create <migration_name>\")
            sys.exit(1)
        create_migration(sys.argv[2])
    elif command == \"up\":
        run_migrations()
    elif command == \"down\":
        rollback_migration()
    elif command == \"status\":
        migration_status()
    else:
        print(f\"Unknown command: {command}\")
        print(__doc__)
        sys.exit(1)
