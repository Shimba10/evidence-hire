from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True)
    job_description = Column(Text, nullable=False)
    resume_text = Column(Text, nullable=False)
    candidate_name = Column(String(255), default="Candidate")
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    interviews = relationship("Interview", back_populates="assessment", cascade="all, delete-orphan")

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    current_question = Column(Text, default="")
    current_skill = Column(String(255), default="")
    question_number = Column(Integer, default=1)
    transcript_json = Column(Text, default="[]")
    report_json = Column(Text, default="")
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    assessment = relationship("Assessment", back_populates="interviews")
