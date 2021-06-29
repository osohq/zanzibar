from materialized import create_mat_view
from oso import Oso
from sqlalchemy_oso import register_models

from sqlalchemy import Column, Integer, String, select, union_all
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey

from models import Base
from oso_partial_helper import partial_query


class Relation(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True)
    namespace = Column(String)
    key = Column(Integer, nullable=True)
    relation = Column(String)

    @staticmethod
    def from_pair(relation, value):
        return Relation(namespace=value.__tablename__, key=value.id, relation=relation)


class Assigned(Base):
    __tablename__ = "assigned"

    id = Column(Integer, primary_key=True)
    namespace = Column(String)
    key = Column(Integer, nullable=True)
    relation_id = Column(Integer, ForeignKey("relations.id"))
    relation = relationship("Relation", backref="assigned", lazy=True)

    @staticmethod
    def from_pair(object, relation):
        return Assigned(
            namespace=object.__tablename__, key=object.id, relation=relation
        )


RELATIONS = []


def add_relation(**relation):
    RELATIONS.add({**relation})


def _zanzibar_query(relation, object):
    ### query to find everything with `relation` to `object`

    # filter = self.gen_filter(relation, object)
    cte = select([Assigned.__table__]).join(Relation).cte("cte", recursive=True)

    recursive_step = (
        self.session.query(Assigned)
        .join(cte, Assigned.relation_id == cte.c.key)
        .filter(cte.c.namespace == "relations")
    )

    cte = cte.union(recursive_step)
    return cte


class Zanzibar:
    def __init__(self, session):
        self.session = session
        self.oso = Oso()
        register_models(self.oso, Base)
        self.oso.register_constant(self, "Z")
        self.oso.load_file("config.polar")
        self.oso.load_file("zanzibar.polar")

    def gen_filter(self, relation, object):
        filter = partial_query(
            self.oso, self.session, "assigned", relation, object, assigned=Assigned
        )
        return filter

    def _query(self, relation, object):
        ### query to find everything with `relation` to `object`

        filter = self.gen_filter(relation, object)
        cte = (
            self.session.query(Assigned)
            .join(Relation)
            .filter(filter)
            .cte("cte", recursive=True)
        )

        recursive_step = (
            self.session.query(Assigned)
            .join(cte, Assigned.relation_id == cte.c.key)
            .filter(cte.c.namespace == "relations")
        )

        cte = cte.union(recursive_step)
        return cte

    def check(self, user, relation, object):
        return user in self.expand(user.__class__, relation, object)

    def expand(self, model, relation, object):
        cte = self._query(relation, object)

        relations = (
            self.session.query(model)
            .join(cte, model.id == cte.c.key)
            .filter(cte.c.namespace == model.__tablename__)
        )
        return relations
