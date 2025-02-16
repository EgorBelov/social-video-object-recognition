from sqlalchemy import Column, Float, Integer, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base

class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    confidence = Column(Float)
    count = Column(Integer, default=1)  # Количество встреч объекта
    video_id = Column(Integer, ForeignKey("videos.id"))

    video = relationship("Video", back_populates="objects")
