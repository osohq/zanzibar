from typing import Tuple
from polar.variable import Variable
from sqlalchemy.sql.elements import or_
from sqlalchemy.sql.expression import and_
from oso import Oso
from sqlalchemy.sql.selectable import CTE
from sqlalchemy_oso import register_models

from sqlalchemy import Column, Integer, String, select, union_all
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Index

from models import Base
from oso_partial_helper import partial_query


class RelationTuple(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True)
    subject_predicate = Column(String, nullable=True)
    subject_key = Column(Integer)
    subject_namespace = Column(String)

    object_predicate = Column(String)
    object_key = Column(Integer)
    object_namespace = Column(String)

    @staticmethod
    def new(subject, predicate, object, subject_predicate=None):
        assert isinstance(subject, Base)
        assert isinstance(object, Base)

        subject_key = str(subject.id)
        subject_namespace = subject.__tablename__
        object_key = object.id
        object_namespace = object.__tablename__

        return RelationTuple(
            subject_key=subject_key,
            subject_namespace=subject_namespace,
            subject_predicate=subject_predicate,
            object_predicate=predicate,
            object_key=object_key,
            object_namespace=object_namespace,
        )

    # Indexes

    __table_args__ = (
        Index("subject_idx", subject_key, subject_namespace),
        Index("object_idx", object_key, object_namespace),
    )


class Tupleset:
    def __init__(self, subject_predicate=None, object_predicate=None, object=None):
        self.subject_predicate = subject_predicate
        self.object_predicate = object_predicate
        self.object = object

    def as_filter(self):
        filter = RelationTuple.object_key == self.object.id
        filter = RelationTuple.object_namespace == self.object.__tablename__
        if self.object_predicate:
            filter &= RelationTuple.object_predicate == self.object_predicate
        if self.subject_predicate:
            filter &= RelationTuple.object_predicate == self.subject_predicate
        return filter


class Zanzibar:
    def __init__(self, session):
        self.session = session
        self.oso = Oso()
        register_models(self.oso, Base)
        self.oso.register_constant(self, "Z")
        self.oso.load_file("config.polar")
        self.oso.load_file("zanzibar.polar")

    def _read_one(self, object, relation=None, subject_predicate=None):
        name = ""
        if isinstance(object, Base):
            filter = RelationTuple.object_key == object.id
            filter = RelationTuple.object_namespace == object.__tablename__
            name = f"{object.__tablename__}__{relation}"
        else:
            # object is a cte?
            assert isinstance(object, CTE)
            filter = RelationTuple.object_key == object.c.subject_key
            filter = RelationTuple.object_namespace == object.c.subject_namespace
            name = f"{object.name}__{relation}"

        # filter by relation if specified
        if relation:
            filter &= RelationTuple.object_predicate == relation

        # filter by source relation if specified
        if subject_predicate:
            filter &= RelationTuple.object_predicate == subject_predicate
        direct_tuples = self.session.query(RelationTuple).filter(filter)

        cte = direct_tuples.cte(recursive=True, name=name)
        cte = cte.union(
            self.session.query(RelationTuple).join(
                cte,
                and_(
                    cte.c.subject_key == RelationTuple.object_key,
                    cte.c.subject_namespace == RelationTuple.object_namespace,
                    cte.c.subject_predicate == RelationTuple.object_predicate,
                ),
            )
        )

        return cte

    def read_one(self, object, relation=None, subject_predicate=None):
        return self.session.query(
            self._read_one(object, relation, subject_predicate)
        ).filter_by(subject_predicate=None, subject_namespace="users")

    # def check2(self, subject, relation, object):

    # def read(self, *tuplesets):
    #     filter = and_(False)
    #     for tupleset in tuplesets:
    #         assert isinstance(tupleset, Tupleset)
    #         filter |= tupleset.as_filter()

    #     return self.session.query(RelationTuple).filter(filter)

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
                    cte.c.subject_predicate == RelationTuple.object_predicate,
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
