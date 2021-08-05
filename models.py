from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import ForeignKey

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
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", backref="repositories", lazy=True)

    def __repr__(self):
        return f"Repository<{self.name}>"


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", backref="teams", lazy=True)

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

    repository_id = Column(Integer, ForeignKey("repositories.id"))
    repository = relationship("Repository", backref="issues", lazy=True)
    reporter_id = Column(Integer, ForeignKey("users.id"))
    reporter = relationship("User", backref="issues_created", lazy=True)


class UserOrgRole(Base):
    __tablename__ = "user_org_roles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship(User, backref="org_roles", lazy=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship(Organization, backref="user_roles", lazy=True)

    role = Column(String)


class UserTeam(Base):
    __tablename__ = "user_teams"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship(User, backref="teams", lazy=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    team = relationship(Team, backref="members", lazy=True)

    role = Column(String, default="member")


class TeamRepoRole(Base):
    __tablename__ = "team_repo_roles"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    team = relationship(Team, backref="repo_roles", lazy=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    repository = relationship(Repository, backref="team_roles", lazy=True)

    role = Column(String)
