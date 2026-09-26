from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, verify_password
from database import Base, engine, get_db
from dependencies import get_current_user
from models import Comment, Ticket, User
from schemas import (
    CommentCreate,
    CommentResponse,
    LoginRequest,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
)

app = FastAPI(title="Help Desk Issue Tracker")


# Create all database tables when the API starts.
Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"message": "Help Desk Issue Tracker API is running"}


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user_data: UserCreate, database: Annotated[Session, Depends(get_db)]):
    existing_user = (
        database.query(User)
        .filter(
            or_(
                User.username == user_data.username,
                User.email == user_data.email,
            )
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered",
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role="employee",
    )

    database.add(new_user)
    database.commit()
    database.refresh(new_user)

    return new_user


@app.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    database: Annotated[Session, Depends(get_db)],
):
    user = database.query(User).filter(User.username == login_data.username).first()

    if user is None or not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@app.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    ticket_data: TicketCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    new_ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        created_by_id=current_user.id,
    )

    database.add(new_ticket)
    database.commit()
    database.refresh(new_ticket)

    return new_ticket


@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    ticket_query = database.query(Ticket)

    if current_user.role != "admin":
        ticket_query = ticket_query.filter(
            or_(
                Ticket.created_by_id == current_user.id,
                Ticket.assigned_to_id == current_user.id,
            )
        )

    return ticket_query.order_by(Ticket.id.desc()).all()


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    ticket = database.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    has_access = (
        current_user.role == "admin"
        or ticket.created_by_id == current_user.id
        or ticket.assigned_to_id == current_user.id
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this ticket",
        )

    return ticket


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    ticket = database.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    has_access = (
        current_user.role == "admin"
        or ticket.created_by_id == current_user.id
        or ticket.assigned_to_id == current_user.id
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this ticket",
        )

    updates = ticket_data.model_dump(exclude_unset=True)

    if current_user.role != "admin" and "assigned_to_id" in updates:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign tickets",
        )

    for field, value in updates.items():
        setattr(ticket, field, value)

    database.commit()
    database.refresh(ticket)

    return ticket


@app.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete tickets",
        )

    ticket = database.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    database.delete(ticket)
    database.commit()


@app.post(
    "/tickets/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    ticket_id: int,
    comment_data: CommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    ticket = database.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    has_access = (
        current_user.role == "admin"
        or ticket.created_by_id == current_user.id
        or ticket.assigned_to_id == current_user.id
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this ticket",
        )

    new_comment = Comment(
        body=comment_data.body,
        ticket_id=ticket_id,
        author_id=current_user.id,
    )

    database.add(new_comment)
    database.commit()
    database.refresh(new_comment)

    return new_comment


@app.get(
    "/tickets/{ticket_id}/comments",
    response_model=list[CommentResponse],
)
def list_comments(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
):
    ticket = database.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    has_access = (
        current_user.role == "admin"
        or ticket.created_by_id == current_user.id
        or ticket.assigned_to_id == current_user.id
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this ticket",
        )

    return (
        database.query(Comment)
        .filter(Comment.ticket_id == ticket_id)
        .order_by(Comment.id.asc())
        .all()
    )
