from passlib.context import CryptContext

# Use bcrypt_sha256 to avoid 72-byte bcrypt limit
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password string using bcrypt_sha256."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)
