import timeit
from random import choices

import pytest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.util import aliased
from sqlalchemy.sql.elements import literal, or_
from sqlalchemy.sql.expression import case, union

from models import *
from zanzibar import *


@pytest.fixture
def test_data():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    alice = User(name="alice")
    bob = User(name="bob")
    charlie = User(name="charlie")
    acme = Organization(name="acme")
    eng = Team(name="eng")
    anvil = Repository(name="anvil")
    issue = Issue(title="test_issue")
    session.add_all([alice, bob, charlie, acme, eng, anvil, issue])
    session.commit()

    session.add_all(
        [
            RelationTuple.new(alice, "owner", issue),
            RelationTuple.new(acme, "parent", anvil),
            RelationTuple.new(anvil, "parent", issue),
            RelationTuple.new(bob, "admin", acme),
            RelationTuple.new(eng, "maintainer", anvil, subject_predicate="member"),
            RelationTuple.new(charlie, "member", eng),
        ]
    )
    session.commit()
    return (session, alice, bob, charlie, acme, eng, anvil, issue)


def test_api(test_data):
    (session, alice, bob, charlie, acme, eng, anvil, issue) = test_data
    z = Zanzibar(session)

    tuples = z.read(object=acme, relation="admin").all()
    assert len(tuples) == 1
    assert tuples[0].subject_key == bob.id
    assert tuples[0].subject_namespace == bob.__tablename__

    issue_owners = z._read(object=issue, relation="owner")
    issue_parents = z._read(object=issue, relation="parent")

    repository_maintainers = z._read(object=issue_parents, relation="maintainer")
    repository_parents = z._read(object=issue_parents, relation="parent")
    organization_admins = z._read(object=repository_parents, relation="admin")

    assert set(map(lambda u: u.subject_key, session.query(issue_owners))) == set(
        [alice.id]
    )
    assert (
        set(
            map(
                lambda u: u.subject_key,
                session.query(repository_maintainers).filter_by(
                    subject_namespace="users"
                ),
            )
        )
        == set([charlie.id])
    )

    assert set(map(lambda u: u.subject_key, session.query(organization_admins))) == set(
        [bob.id]
    )

    assert z.check(alice, "permission:close", issue)
    users = z.expand(User, "permission:close", issue)
    assert set(users) == set([alice, bob, charlie])


@pytest.mark.skip(reason="old test")
def test_zanzibar(test_data):
    (session, alice, bob, charlie, acme, eng, anvil, issue) = test_data
    z = Zanzibar(session)

    # what organizations are parents of Anvil
    assert set([acme]) == set(z.expand(Organization, "parent", anvil))

    # what users are members of Anvil
    assert set([bob, charlie]) == set(z.expand(User, "contributor", anvil))

    # alice has the org admin relation (to acme)
    assert z.check(alice, "admin", acme)
    # alice is a member of the eng team, eng team is a contributor of the acme repo
    assert z.check(alice, "contributor", anvil)

    # alice is a member of Acme since Alice is an admin of Acme
    assert z.check(alice, "member", acme)
    # alice is a member of Acme since Alice is an admin of Acme
    assert not z.check(bob, "member", acme)

    # alice is actually a maintainer of anvil too, since she is an
    # admin if Acme
    assert z.check(alice, "contributor", anvil)

    assert z.check(bob, "permission:close", issue)


PERF_DB = "postgresql://postgres:password@localhost:5432"
# PERF_DB = "sqlite:///relations.db"
PERF_SCALE = 10


# @pytest.mark.skip
def test_perf():
    engine = create_engine(PERF_DB, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    z = Zanzibar(session)

    user = session.query(User).first()
    repo = session.query(Repository).first()
    org = session.query(Organization).first()
    issue = session.query(Issue).first()

    org_member = z.expand(User, "member", org).all()
    assert len(org_member) > 0
    repo_owner = z.expand(Organization, "parent", repo).all()
    assert len(repo_owner) > 0
    user_repos = z.expand(User, "contributor", repo).all()
    assert len(user_repos) > 0
    issue_closers = z.expand(User, "permission:close", issue).all()
    assert len(issue_closers) > 0

    engine = create_engine(PERF_DB, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    z = Zanzibar(session)

    issue = session.query(Issue).get(10000 * PERF_SCALE)
    issue_closer = z.expand(User, "permission:close", issue).first()

    def test_query():
        return z.check(issue_closer, "permission:close", issue)

    number = 100
    time = timeit.timeit(test_query, number=number)
    print(f"Executed in : {time/number*1000} ms\n Averaged over {number} repetitions.")


def perf_data():
    engine = create_engine(PERF_DB, echo=False)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    NUM_ORGS = 100 * PERF_SCALE
    REPOS_PER_ORG = 10
    ISSUES_PER_REPO = 200
    USERS_PER_ORG = 50
    NUM_REPOS = NUM_ORGS * REPOS_PER_ORG
    NUM_ISSUES = NUM_REPOS * ISSUES_PER_REPO
    NUM_USERS = NUM_ORGS * USERS_PER_ORG

    # Create 5k users
    session.bulk_insert_mappings(
        User, iter({"name": f"user_{i}"} for i in range(1, NUM_USERS + 1))
    )
    session.commit()
    print(f"Inserted {NUM_USERS} users")

    # Create 100 orgs
    session.bulk_insert_mappings(
        Organization, iter({"name": f"org_{i}"} for i in range(1, NUM_ORGS + 1))
    )
    session.commit()
    print(f"Inserted {NUM_ORGS} organizations")

    # Create 1k repositories
    session.bulk_insert_mappings(
        Repository, iter({"name": f"repo_{i}"} for i in range(1, NUM_REPOS + 1))
    )
    session.commit()
    print(f"Inserted {NUM_REPOS} repositories")

    # Create 20k issues
    session.bulk_insert_mappings(
        Issue, iter({"title": f"issue_{i}"} for i in range(1, NUM_ISSUES + 1))
    )
    session.commit()
    print(f"Inserted {NUM_ISSUES} issues")

    # assign each repo to an org
    repo_orgs = choices(
        range(1, NUM_ORGS + 1),
        [100] * (NUM_ORGS // 10) + [10] * (NUM_ORGS // 10) + [1] * (NUM_ORGS // 10) * 8,
        k=NUM_REPOS,
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": org_idx,
                "subject_namespace": "organizations",
                "subject_predicate": None,
                "object_predicate": "parent",
                "object_key": repo_idx,
                "object_namespace": "repositories",
            }
            for repo_idx, org_idx in enumerate(repo_orgs)
        ),
    )
    session.commit()
    print(f"Inserted {NUM_REPOS} repo-org relationships")

    # assign each issue to a repo
    issue_repo = choices(
        range(1, NUM_REPOS + 1),
        [100] * (NUM_REPOS // 10)
        + [10] * (NUM_REPOS // 10)
        + [1] * (NUM_REPOS // 10) * 8,
        k=NUM_ISSUES,
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": repo_idx,
                "subject_namespace": "repositories",
                "subject_predicate": None,
                "object_predicate": "parent",
                "object_key": issue_idx,
                "object_namespace": "issues",
            }
            for issue_idx, repo_idx in enumerate(issue_repo)
        ),
    )
    session.commit()

    # assign each user to an org
    #  each user belongs to 10-50 organizations
    user_orgs = choices(
        range(1, NUM_ORGS + 1),
        [100] * (NUM_ORGS // 10) + [10] * (NUM_ORGS // 10) + [1] * (NUM_ORGS // 10) * 8,
        k=NUM_USERS * 5,
    )
    # half the users belong to just 1 org
    # 5% belong to 5 orgs
    user_org_number = choices(
        [
            1 * PERF_SCALE,
            2 * PERF_SCALE,
            3 * PERF_SCALE,
            4 * PERF_SCALE,
            5 * PERF_SCALE,
        ],
        [10, 3, 3, 3, 1],
        k=NUM_USERS * 5,
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": user_idx % NUM_USERS,
                "subject_namespace": "users",
                "subject_predicate": None,
                "object_predicate": "member",
                "object_key": org_idx,
                "object_namespace": "organizations",
            }
            for user_idx, org_idx in enumerate(user_orgs)
            if user_idx // NUM_USERS < user_org_number[user_idx % NUM_USERS]
        ),
    )
    session.commit()
    print(f"Inserted ~{2 * NUM_USERS * 5 * PERF_SCALE} user-org relationships")

    #### Total relationships:
    # 1000 repo-org
    # 20000 issue-repository
    # ~5000 + 1500 + 1500 + 1500 + 1500 + 500 = 11500
    # Total about 31.5k
    # (on one test: 31528)


if __name__ == "__main__":
    perf_data()
