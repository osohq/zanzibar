from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return f"Organization<{self.name}>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return f"User<{self.name}>"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # organization_id = Column(Integer, ForeignKey("organizations.id"))
    # organization = relationship("Organization", backref="repositories", lazy=True)
    def __repr__(self):
        return f"Repository<{self.name}>"


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # organization_id = Column(Integer, ForeignKey("organizations.id"))
    # organization = relationship("Organization", backref="teams", lazy=True)

    def __repr__(self):
        return f"Team<{self.name}>"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    body = Column(Text)
    closed = Column(Boolean, default=False)

    def __repr__(self):
        return f"Issue<{self.title}>"

    # repository_id = Column(Integer, ForeignKey("repositories.id"))
    # repository = relationship("Repository", backref="issues", lazy=True)
    # reporter_id = Column(Integer, ForeignKey("users.id"))
    # reporter = relationship("User", backref="issues_created", lazy=True)
