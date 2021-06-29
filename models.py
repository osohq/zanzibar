from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine("sqlite:///relations.db", echo=True)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # organization_id = Column(Integer, ForeignKey("organizations.id"))
    # organization = relationship("Organization", backref="repositories", lazy=True)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # organization_id = Column(Integer, ForeignKey("organizations.id"))
    # organization = relationship("Organization", backref="teams", lazy=True)


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # repository_id = Column(Integer, ForeignKey("repositories.id"))
    # repository = relationship("Repository", backref="issues", lazy=True)
