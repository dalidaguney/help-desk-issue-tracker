import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import verify_password
from database import Base
from manage import create_admin
from models import User


def test_create_admin_account():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    database = testing_session()

    try:
        admin = create_admin(
            database,
            username="admin",
            email="admin@example.com",
            password="SecureAdminPassword123!",
        )

        assert admin.role == "admin"
        assert verify_password("SecureAdminPassword123!", admin.password_hash)
        assert database.query(User).count() == 1

        with pytest.raises(ValueError, match="already registered"):
            create_admin(
                database,
                username="admin",
                email="another@example.com",
                password="AnotherSecurePassword123!",
            )
    finally:
        database.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
