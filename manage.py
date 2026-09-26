import argparse
from getpass import getpass

from auth import hash_password
from database import Base, SessionLocal, engine
from models import User


def create_admin(database, username, email, password):
    existing_user = (
        database.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )

    if existing_user:
        raise ValueError("Username or email is already registered")

    admin = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role="admin",
    )
    database.add(admin)
    database.commit()
    database.refresh(admin)
    return admin


def main():
    parser = argparse.ArgumentParser(description="Help Desk administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser(
        "create-admin",
        help="Create an administrator account",
    )
    create_admin_parser.add_argument("--username", required=True)
    create_admin_parser.add_argument("--email", required=True)

    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)

    password = getpass("Password: ")
    password_confirmation = getpass("Confirm password: ")

    if password != password_confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters")

    database = SessionLocal()
    try:
        admin = create_admin(database, args.username, args.email, password)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    finally:
        database.close()

    print(f"Administrator '{admin.username}' created successfully")


if __name__ == "__main__":
    main()
