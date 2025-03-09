from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from infrastructure.database import Base

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    url = Column(String)
    platform = Column(String, index=True)
    timestamp = Column(DateTime)
    hash = Column(String)  # Поле для хэш-суммы
    objects = relationship("Object", back_populates="video")
