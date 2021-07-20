from oso import Oso
from polar.variable import Variable
from sqlalchemy import Column, Integer, String
from sqlalchemy.sql.expression import and_, union
from sqlalchemy.sql.schema import Index
from sqlalchemy.sql.selectable import CTE
from sqlalchemy_oso import register_models

from models import Base, User


class RelationTuple(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True)

    subject_predicate = Column(String, nullable=True)  # member
    subject_key = Column(Integer)  # 1
    subject_namespace = Column(String)  # team

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
        Index("subject_idx", subject_key, subject_namespace, subject_predicate),
        Index("object_idx", object_key, object_namespace, object_predicate),
        Index("subject_predicate_idx", subject_predicate),
        Index("object_predicate_idx", object_predicate),
    )


class Zanzibar:
    def __init__(self, session):
        self.session = session
        self.oso = Oso()
        register_models(self.oso, Base)
        self.oso.register_constant(self, "Z")
        self.oso.load_file("config.polar")
        self.oso.load_file("zanzibar.polar")
        self.cte_counter = 0

    def _read(self, object, relation=None, subject_predicate=None):
        self.cte_counter += 1
        name = ""
        if isinstance(object, Base):
            filter = RelationTuple.object_key == object.id
            filter &= RelationTuple.object_namespace == object.__tablename__
            name = f"{object.__tablename__}__{relation}{self.cte_counter}"
        else:
            # object is a cte?
            assert isinstance(object, CTE)
            filter = RelationTuple.object_key == object.c.subject_key
            filter &= RelationTuple.object_namespace == object.c.subject_namespace
            name = f"{object.name}__{relation}{self.cte_counter}"

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

    def read(self, object, relation=None, subject_predicate=None):
        return self.session.query(
            self._read(object, relation, subject_predicate)
        ).filter_by(subject_predicate=None, subject_namespace="users")

    def check(self, user, relation, object):
        query = self.expand(User, relation, object)
        return query.filter(User.id == user.id).first() is not None

    def _expand(self, model, relation, object):
        results = self.oso.query_rule(
            "relationship",
            Variable("subject"),
            relation,
            {"object": object, "namespace": object.__tablename__},
        )

        def cte_to_query(q):
            return self.session.query(
                q.c.subject_key.label("id"),
            ).filter(q.c.subject_namespace == model.__tablename__)

        return union(*[cte_to_query(res["bindings"]["subject"]) for res in results])

    def expand(self, model, relation, object):
        q = self._expand(model, relation, object)
        userset = self.session.query(model).filter(model.id.in_(q))
        return userset
