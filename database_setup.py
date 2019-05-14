import os
import sys
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(256), nullable = False)
    picture = Column(String)

    @property
    def serialize(self):
        """Return object data in easily serializeable format."""
        return {
            'id'           : self.id,
            'name'         : self.name,
            'email'        : self.email,
            'picture'      : self.picture
        }


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    user_id = Column(Integer, ForeignKey("user.id"), nullable = False)
    user = relationship("User")

    @property
    def serialize(self):
        """Return object data in easily serializable format."""
        return {
            'id'            : self.id,
            'name'          : self.name,
            'user_id'       : self.user_id
        }


class Item(Base):
    __tablename__ = 'item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    image = Column(String)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)

    created = Column(DateTime, default = datetime.utcnow)
    updated = Column(DateTime, default = datetime.utcnow, onupdate = datetime.utcnow)

    user_id = Column(Integer, ForeignKey("user.id"), nullable = False)
    user = relationship("User")

    # We added this serialize function to be able to send JSON objects in a
    # serializable format
    @property
    def serialize(self):
        """Return object data in easily serializeable format."""
        return {
            'id'            : self.id,
            'name'          : self.name,
            'description'   : self.description,
            'image'         : self.image,
            'category_id'   : self.category_id,
            'user_id'       : self.user_id
        }


engine = create_engine('sqlite:///itemcatalog.db')

Base.metadata.create_all(engine)
