import timeit
from random import choice, choices, randint

import pytest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

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
    eng = Team(name="eng", organization=acme)
    anvil = Repository(name="anvil", organization=acme)
    issue = Issue(title="test_issue", repository=anvil, reporter=alice)
    bob_role = UserOrgRole(user=bob, role="org:admin", organization=acme)
    eng_role = TeamRepoRole(team=eng, role="repo:maintainer", repository=anvil)
    charlie_eng = UserTeam(user=charlie, team=eng)
    session.add_all(
        [alice, bob, charlie, acme, eng, anvil, issue, bob_role, eng_role, charlie_eng]
    )
    session.commit()

    session.add_all(
        [
            RelationTuple.new(alice, "reporter", issue),
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

    issue_reporters = z._read(object=issue, relation="reporter")
    issue_parents = z._read(object=issue, relation="parent")

    repository_maintainers = z._read(object=issue_parents, relation="maintainer")
    repository_parents = z._read(object=issue_parents, relation="parent")
    organization_admins = z._read(object=repository_parents, relation="admin")

    assert set(map(lambda u: u.subject_key, session.query(issue_reporters))) == set(
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


def test_zanzibar(test_data):
    (session, alice, bob, charlie, acme, eng, anvil, issue) = test_data
    z = Zanzibar(session)

    assert z.check(alice, "reporter", issue)
    assert z.check(bob, "contributor", anvil)
    assert z.check(charlie, "contributor", anvil)
    assert set(z.expand(User, "permission:close", issue).all()) == set(
        [alice, bob, charlie]
    )

    z = OsoZanzibar(session)

    assert z.check(alice, "issue:reporter", issue)
    assert z.check(bob, "repo:contributor", anvil)
    assert z.check(charlie, "repo:contributor", anvil)
    assert set(z.expand(User, "issue:perm:close", issue).all()) == set(
        [alice, bob, charlie]
    )


PERF_DB = "postgresql://postgres:password@localhost:5432"
# PERF_DB = "sqlite:///relations.db"
PERF_SCALE = 40


# @pytest.mark.skip
def test_perf_zanzibar():
    engine = create_engine(PERF_DB, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = session.query(User).first()
    repo = session.query(Repository).first()
    org = session.query(Organization).first()
    issue = session.query(Issue).first()

    z = Zanzibar(session)
    org_member = z.expand(User, "member", org).all()
    assert len(org_member) > 0
    repo_parent = z.expand(Organization, "parent", repo).all()
    assert len(repo_parent) > 0
    user_repos = z.expand(User, "contributor", repo).all()
    assert len(user_repos) > 0
    issue_closers = z.expand(User, "permission:close", issue).all()
    assert len(issue_closers) > 0

    engine = create_engine(PERF_DB, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    z = Zanzibar(session)

    issue = session.query(Issue).get(10000 * PERF_SCALE)
    # issue_closers = z.expand(User, "permission:close", issue).all()

    def test_query():
        user = session.query(Issue).get(randint(1, 10 * PERF_SCALE))
        issue = session.query(Issue).get(randint(1, 10 * PERF_SCALE))
        return z.check(user, "permission:close", issue)

    number = 100
    time = timeit.timeit(test_query, number=number)
    print(
        f"Zanzibar Executed in : {time/number*1000} ms\n Averaged over {number} repetitions."
    )


def test_perf_regular():
    engine = create_engine(PERF_DB, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = session.query(User).first()
    repo = session.query(Repository).first()
    org = session.query(Organization).first()
    issue = session.query(Issue).first()

    z = OsoZanzibar(session)
    org_member = z.expand(User, "org:member", org).all()
    assert len(org_member) > 0
    repo_parent = z.expand(Organization, "repo:parent", repo).all()
    assert len(repo_parent) > 0
    user_repos = z.expand(User, "repo:contributor", repo).all()
    assert len(user_repos) > 0
    issue_closers = z.expand(User, "issue:perm:close", issue).all()
    assert len(issue_closers) > 0

    engine = create_engine(PERF_DB, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    z = OsoZanzibar(session)

    issue = session.query(Issue).get(10000 * PERF_SCALE)

    def test_query():
        user = session.query(Issue).get(randint(1, 10 * PERF_SCALE))
        issue = session.query(Issue).get(randint(1, 10 * PERF_SCALE))
        return z.check(user, "issue:perm:close", issue)

    number = 100
    time = timeit.timeit(test_query, number=number)
    print(
        f"Regular Executed in : {time/number*1000} ms\n Averaged over {number} repetitions."
    )


def perf_data():
    engine = create_engine(PERF_DB, echo=False)

    # We're manually indexing rows, so we need to know if we can
    # start counting at 1 or zero
    zero_idx = 1 if PERF_DB.startswith("postgresql") else 0

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
        User, iter({"name": f"user_{i + zero_idx}"} for i in range(NUM_USERS))
    )
    session.commit()
    print(f"Inserted {NUM_USERS} users")

    # Create 100 orgs
    session.bulk_insert_mappings(
        Organization, iter({"name": f"org_{i + zero_idx}"} for i in range(NUM_ORGS))
    )
    session.commit()
    print(f"Inserted {NUM_ORGS} organizations")

    # assign each repo to an org
    repo_orgs = choices(
        range(NUM_ORGS),
        [100] * (NUM_ORGS // 10) + [10] * (NUM_ORGS // 10) + [1] * (NUM_ORGS // 10) * 8,
        k=NUM_REPOS,
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": org_idx + zero_idx,
                "subject_namespace": "organizations",
                "subject_predicate": None,
                "object_predicate": "parent",
                "object_key": repo_idx + zero_idx,
                "object_namespace": "repositories",
            }
            for repo_idx, org_idx in enumerate(repo_orgs)
        ),
    )
    session.bulk_insert_mappings(
        Repository,
        iter(
            {
                "name": f"repo_{repo_idx + zero_idx}",
                "organization_id": org_idx + zero_idx,
            }
            for repo_idx, org_idx in enumerate(repo_orgs)
        ),
    )
    session.commit()
    print(f"Inserted {NUM_REPOS} repo-org relationships")

    # assign each issue to a repo
    issue_repo = choices(
        range(NUM_REPOS),
        [100] * (NUM_REPOS // 10)
        + [10] * (NUM_REPOS // 10)
        + [1] * (NUM_REPOS // 10) * 8,
        k=NUM_ISSUES,
    )
    issue_reporter = choices(
        range(NUM_USERS),
        [100] * (NUM_USERS // 10)
        + [10] * (NUM_USERS // 10)
        + [1] * (NUM_USERS // 10) * 8,
        k=NUM_ISSUES,
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": repo_idx + zero_idx,
                "subject_namespace": "repositories",
                "subject_predicate": None,
                "object_predicate": "parent",
                "object_key": issue_idx + zero_idx,
                "object_namespace": "issues",
            }
            for issue_idx, repo_idx in enumerate(issue_repo)
        ),
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": user_idx + zero_idx,
                "subject_namespace": "users",
                "subject_predicate": None,
                "object_predicate": "reporter",
                "object_key": issue_idx + zero_idx,
                "object_namespace": "issues",
            }
            for issue_idx, user_idx in enumerate(issue_reporter)
        ),
    )
    session.commit()
    # Create 20k issues
    session.bulk_insert_mappings(
        Issue,
        iter(
            {
                "title": f"issue_{issue_idx + zero_idx}",
                "repository_id": repo_idx + zero_idx,
                "reporter_id": user_idx + zero_idx,
            }
            for issue_idx, (repo_idx, user_idx) in enumerate(
                zip(issue_repo, issue_reporter)
            )
        ),
    )
    session.commit()

    # assign each user to an org
    #  each user belongs to 10-50 organizations
    user_orgs = choices(
        range(NUM_ORGS),
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
        UserOrgRole,
        iter(
            {
                "user_id": (user_idx % NUM_USERS) + zero_idx,
                "role": "org:member",
                "organization_id": org_idx + zero_idx,
            }
            for user_idx, org_idx in enumerate(user_orgs)
            if user_idx // NUM_USERS < user_org_number[user_idx % NUM_USERS]
        ),
    )
    session.bulk_insert_mappings(
        RelationTuple,
        iter(
            {
                "subject_key": (user_idx % NUM_USERS) + zero_idx,
                "subject_namespace": "users",
                "subject_predicate": None,
                "object_predicate": "member",
                "object_key": org_idx + zero_idx,
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
    # 20000 issue-user
    # ~5000 + 1500 + 1500 + 1500 + 1500 + 500 = 11500
    # Total about 31.5k
    # (on one test: 31528)


if __name__ == "__main__":
    perf_data()
