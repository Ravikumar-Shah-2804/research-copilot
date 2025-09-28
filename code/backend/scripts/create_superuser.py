#!/usr/bin/env python3
"""
Script to create a superuser account with full admin privileges
"""
import sys
import os
import argparse

# Add backend directory to path so src module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models.user import User
from src.models.role import Role, Organization
from src.services.auth import get_password_hash

# Create sync engine for script
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_superuser(username: str, email: str, password: str, full_name: str = None):
    """Create a superuser account"""
    try:
        # Hash the password
        try:
            hashed_password = get_password_hash(password)
            print(f"Generated hash for password")
        except Exception as hash_error:
            print(f"❌ Error hashing password: {hash_error}")
            return False

        with SessionLocal() as session:
            # Get or create default organization
            result = session.execute(
                select(Organization).where(Organization.name == 'Default Organization')
            )
            org = result.scalar_one_or_none()
            if not org:
                print("⚠️  Default Organization not found, creating it...")
                org = Organization(
                    name='Default Organization',
                    description='Default organization for single-tenant setup',
                    domain=None,
                    subscription_tier='enterprise'
                )
                session.add(org)
                session.flush()  # Get the ID
                print("✅ Default Organization created")

            # Check if user already exists
            result = session.execute(
                select(User).where((User.username == username) | (User.email == email))
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                print(f"❌ User with username '{username}' or email '{email}' already exists")
                return False

            # Create the user
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                full_name=full_name or username,
                is_superuser=True,
                organization_id=org.id
            )
            session.add(user)
            session.flush()  # Get the user ID

            # Get or create superuser role
            result = session.execute(
                select(Role).where(Role.name == 'superuser')
            )
            superuser_role = result.scalar_one_or_none()
            if not superuser_role:
                print("⚠️  Superuser role not found, creating it...")
                superuser_role = Role(
                    name='superuser',
                    description='Superuser with full system access',
                    is_default=False,
                    is_system=True
                )
                session.add(superuser_role)
                session.flush()  # Get the ID
                print("✅ Superuser role created")

            # Assign superuser role
            user.roles.append(superuser_role)

            session.commit()

            print("✅ Superuser created successfully")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Full Name: {full_name or username}")
            print(f"   Organization: {org.name}")
            print(f"   Roles: {[role.name for role in user.roles]}")
            return True

    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Create a superuser account')
    parser.add_argument('--username', required=True, help='Username for the superuser')
    parser.add_argument('--email', required=True, help='Email for the superuser')
    parser.add_argument('--password', required=True, help='Password for the superuser')
    parser.add_argument('--full-name', help='Full name for the superuser (optional)')

    args = parser.parse_args()

    success = create_superuser(
        args.username,
        args.email,
        args.password,
        args.full_name
    )
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()