from .db import engine, Base, SessionLocal
from .models import User
from .auth import get_password_hash

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if users exist
        l1_user = db.query(User).filter(User.username == "admin").first()
        if not l1_user:
            l1 = User(username="admin", role="L1", hashed_password=get_password_hash("123456"))
            db.add(l1)
            print("Created default L1 user (username: admin, password: 123456)")
        
        l2_user = db.query(User).filter(User.username == "l2").first()
        if not l2_user:
            l2 = User(username="l2", role="L2", hashed_password=get_password_hash("password"))
            db.add(l2)
            print("Created default L2 user (username: l2, password: password)")
            
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
