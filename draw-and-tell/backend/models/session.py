# Session schema (id, kid_id, duration, turns)
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Session(Base):
	__tablename__ = 'sessions'
	id = Column(Integer, primary_key=True)
	kid_id = Column(String)
	duration = Column(Float)
	turns = Column(Integer)
