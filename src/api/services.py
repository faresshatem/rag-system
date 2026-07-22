from sqlalchemy.orm import Session
from src.api.repository import UserRepository
from src.api.schemas import UserCreate
from src.api.auth import hash_password, verify_password, create_access_token

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def register_user(self, db: Session, user_in: UserCreate):
        """Handle user registration logic."""
        existing_user = self.user_repo.get_user_by_username(db, user_in.username)
        if existing_user:
            return None  # Indicates the username is already taken
            
        # Automatically assign all domains if the user is an Admin
        final_domains = "HR,IT" if user_in.role == "Admin" else user_in.allowed_domains

        user_data = {
            "username": user_in.username,
            "hashed_password": hash_password(user_in.password),
            "role": user_in.role,
            "allowed_domains": final_domains
        }
        return self.user_repo.create_user(db, user_data)

    def authenticate_user(self, db: Session, username: str, password: str):
        """Handle user authentication and token generation."""
        user = self.user_repo.get_user_by_username(db, username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        token_data = {"sub": user.username, "role": user.role, "allowed_domains": user.allowed_domains or ""}
        token = create_access_token(data=token_data)
        return token
