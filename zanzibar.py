from sqlalchemy.sql.expression import and_
from materialized import create_mat_view
from oso import Oso
from sqlalchemy_oso import register_models

from sqlalchemy import Column, Integer, String, select, union_all
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey

from models import Base
from oso_partial_helper import partial_query


class RelationTuple(Base):
    __tablename__ = "relation_tuples"

    id = Column(Integer, primary_key=True)
    source_key = Column(String)
    source_namespace = Column(String)
    source_relation = Column(String, nullable=True)
    relation = Column(String)
    target_key = Column(String)
    target_namespace = Column(String)

    @staticmethod
    def new(source, relation, target, source_relation=None):
        assert isinstance(source, Base)
        assert isinstance(target, Base)

        source_key = str(source.id)
        source_namespace = source.__tablename__
        target_key = target.id
        target_namespace = target.__tablename__

        return RelationTuple(
            source_key=source_key,
            source_namespace=source_namespace,
            source_relation=source_relation,
            relation=relation,
            target_key=target_key,
            target_namespace=target_namespace,
        )


# class Relation(Base):
#     __tablename__ = "relations"

#     id = Column(Integer, primary_key=True)
#     namespace = Column(String)
#     key = Column(Integer, nullable=False)
#     relation = Column(String)

#     @staticmethod
#     def from_pair(relation, value):
#         return Relation(namespace=value.__tablename__, key=value.id, relation=relation)


# class Assigned(Base):
#     __tablename__ = "assigned"

#     id = Column(Integer, primary_key=True)
#     namespace = Column(String)
#     key = Column(Integer, nullable=False)
#     relation_id = Column(Integer, ForeignKey("relations.id"))
#     relation = relationship("Relation", backref="assigned", lazy=True)

#     @staticmethod
#     def from_pair(object, relation):
#         return Assigned(
#             namespace=object.__tablename__, key=object.id, relation=relation
#         )


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
            self.oso, self.session, "assigned", relation, object, tuple=RelationTuple
        )
        return filter

    def _query(self, relation, object):
        ### query to find everything with `relation` to `object`

        filter = self.gen_filter(relation, object)
        cte = (
            self.session.query(RelationTuple).filter(filter).cte("cte", recursive=True)
        )

        recursive_step = (
            # join all tuples where the sources have the relationship
            # with the target
            self.session.query(RelationTuple).join(
                cte,
                and_(
                    cte.c.source_key == RelationTuple.target_key,
                    cte.c.source_namespace == RelationTuple.target_namespace,
                    cte.c.source_relation == RelationTuple.relation,
                ),
            )
        )

        cte = cte.union(recursive_step)
        return cte

    def check(self, user, relation, object):
        return user in self.expand(user.__class__, relation, object)

    def expand(self, model, relation, object):
        cte = self._query(relation, object)

        relations = (
            self.session.query(model)
            .join(cte, model.id == cte.c.source_key)
            .filter(cte.c.source_namespace == model.__tablename__)
        )
        return relations
