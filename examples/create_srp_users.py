#!/usr/bin/env python3
"""
SRP User Database Management Script
Creates and manages SRP users for EST bootstrap authentication
"""
import os
import sys
from tlslite import VerifierDB

def create_srp_database(db_path):
    """Create a new SRP database"""
    print(f"Creating SRP database: {db_path}")

    # Create certs directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Create the database
    db = VerifierDB(db_path)
    db.create()
    print(f"[OK] SRP database created successfully: {db_path}")
    return db

def add_user(db_path, username, password):
    """Add a user to the SRP database"""
    print(f"Adding user '{username}' to SRP database...")

    try:
        db = VerifierDB(db_path)
        db.open()

        # Check if user already exists
        try:
            if db[username]:
                print(f"[WARN] User '{username}' already exists in database")
                return False
        except KeyError:
            # User doesn't exist, which is what we want
            pass

        # Add the user
        db[username] = db.makeVerifier(username, password, 1024)

        print(f"[OK] User '{username}' added successfully")
        return True

    except Exception as e:
        print(f"[ERROR] Error adding user: {e}")
        return False

def list_users(db_path):
    """List all users in the SRP database"""
    try:
        # Check if database files exist (SRP database uses .dat, .dir, .bak extensions)
        db_files = [db_path + '.dat', db_path + '.dir', db_path + '.bak']
        if not any(os.path.exists(f) for f in db_files):
            print(f"[ERROR] Database not found: {db_path}")
            print("Run 'python create_srp_users.py create' first")
            return []

        db = VerifierDB(db_path)
        db.open()

        users = []
        try:
            # Handle potential encoding issues with tlslite
            for key in db.keys():
                if isinstance(key, bytes):
                    users.append(key.decode('utf-8'))
                elif isinstance(key, str):
                    users.append(key)
                else:
                    users.append(str(key))
        except Exception as key_error:
            print(f"[WARN] Error reading user keys: {key_error}")
            # Try alternative approach
            try:
                # Direct access to check if users exist
                test_users = ['testuser', 'device001', 'admin']
                for user in test_users:
                    try:
                        if db[user]:
                            users.append(user)
                    except KeyError:
                        pass
            except Exception:
                pass

        if users:
            print(f"Users in database:")
            for user in users:
                print(f"  - {user}")
        else:
            print("No users found in database")

        return users

    except Exception as e:
        print(f"[ERROR] Error listing users: {e}")
        return []

def main():
    db_path = "certs/srp_users.db"

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python create_srp_users.py create                    # Create new database")
        print("  python create_srp_users.py add <username> <password> # Add user")
        print("  python create_srp_users.py list                      # List all users")
        print("  python create_srp_users.py setup                     # Create DB and add demo users")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        create_srp_database(db_path)

    elif command == "add":
        if len(sys.argv) != 4:
            print("Usage: python create_srp_users.py add <username> <password>")
            sys.exit(1)
        username = sys.argv[2]
        password = sys.argv[3]

        # Create database if it doesn't exist
        if not os.path.exists(db_path):
            create_srp_database(db_path)

        add_user(db_path, username, password)

    elif command == "list":
        list_users(db_path)

    elif command == "setup":
        # Create database and add demo users
        create_srp_database(db_path)

        demo_users = [
            ("testuser", "testpass123"),
            ("device001", "SecureP@ss001"),
            ("admin", "AdminP@ss456")
        ]

        print("\nAdding demo users...")
        for username, password in demo_users:
            add_user(db_path, username, password)

        print(f"\n[OK] Setup complete! SRP database ready at: {db_path}")
        print("\nDemo credentials:")
        for username, password in demo_users:
            print(f"  Username: {username} | Password: {password}")

    else:
        print(f"[ERROR] Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()