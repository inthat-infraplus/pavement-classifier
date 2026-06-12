from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(String) # 'L1' or 'L2'
    hashed_password = Column(String)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    assigner_id = Column(Integer, ForeignKey("users.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"))
    folder_path = Column(String)
    status = Column(String, default="pending") # 'pending', 'completed'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assigner = relationship("User", foreign_keys=[assigner_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    images = relationship("Image", back_populates="task")

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    filename = Column(String)
    label = Column(String, nullable=True) # null, 'pavement', 'normal'
    
    task = relationship("Task", back_populates="images")
