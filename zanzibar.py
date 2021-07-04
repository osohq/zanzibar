from polar.variable import Variable
from sqlalchemy.sql.expression import and_
from oso import Oso
from sqlalchemy_oso import register_models

from sqlalchemy import Column, Integer, String, select, union_all
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Index

from models import Base
from oso_partial_helper import partial_query


class RelationTuple(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True)
    subject_key = Column(Integer)
    subject_namespace = Column(String)
    subject_relation = Column(String, nullable=True)
    relation = Column(String)
    object_key = Column(Integer)
    object_namespace = Column(String)

    @staticmethod
    def new(subject, relation, object, subject_relation=None):
        assert isinstance(subject, Base)
        assert isinstance(object, Base)

        subject_key = str(subject.id)
        subject_namespace = subject.__tablename__
        object_key = object.id
        object_namespace = object.__tablename__

        return RelationTuple(
            subject_key=subject_key,
            subject_namespace=subject_namespace,
            subject_relation=subject_relation,
            relation=relation,
            object_key=object_key,
            object_namespace=object_namespace,
        )

    # Indexes

    __table_args__ = (
        Index("subject_idx", subject_key, subject_namespace),
        Index("object_idx", object_key, object_namespace),
    )


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

        if False:
            res = self.oso.query_rule("relation", object, relation, Variable("child"))
            try:
                next(res)
            except StopIteration:
                raise Exception(
                    f"There does not exist a relation defined for {relation} on {object}"
                )

        filter = self.gen_filter(relation, object)
        cte = (
            self.session.query(RelationTuple).filter(filter).cte("cte", recursive=True)
        )

        recursive_step = (
            # join all tuples where the subjects have the relationship
            # with the object
            self.session.query(RelationTuple).join(
                cte,
                and_(
                    cte.c.subject_key == RelationTuple.object_key,
                    cte.c.subject_namespace == RelationTuple.object_namespace,
                    cte.c.subject_relation == RelationTuple.relation,
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
            .join(cte, model.id == cte.c.subject_key)
            .filter(cte.c.subject_namespace == model.__tablename__)
        )
        return relations
