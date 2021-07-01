import pytest
import timeit
from random import choices
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from models import *
from zanzibar import *


def test_zanzibar():
    engine = create_engine("sqlite:///:memory:", echo=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    alice = User(name="alice")
    bob = User(name="bob")
    acme = Organization(name="acme")
    eng = Team(name="eng")
    anvil = Repository(name="anvil")
    issue = Issue(name="test_issue")
    session.add_all([alice, bob, acme, eng, anvil, issue])
    session.commit()

    session.add_all(
        [
            RelationTuple.new(alice, "owner", issue),
            RelationTuple.new(acme, "parent", anvil),
            RelationTuple.new(alice, "admin", acme),
            RelationTuple.new(alice, "member", eng),
            RelationTuple.new(eng, "contributor", anvil, source_relation="member"),
            RelationTuple.new(bob, "contributor", anvil),
        ]
    )
    session.commit()

    z = Zanzibar(session)

    # what organizations are parents of Anvil
    assert set([acme]) == set(z.expand(Organization, "parent", anvil))

    # what users are members of Anvil
    assert set([alice, bob]) == set(z.expand(User, "contributor", anvil))

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


@pytest.mark.skip
def test_perf():
    engine = create_engine("sqlite:///relations.db", echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    z = Zanzibar(session)

    user = session.query(User).first()
    repo = session.query(Repository).first()
    org = session.query(Organization).first()
    issue = session.query(Repository).first()

    org_member = z.expand(User, "member", org).all()
    assert len(org_member) > 0
    repo_owner = z.expand(Organization, "parent", repo).all()
    assert len(repo_owner) > 0
    user_repos = z.expand(User, "contributor", repo).all()
    assert len(user_repos) > 0
    # issue_closers = z.expand(User, "permission:close", issue).all()
    # assert len(issue_closers) > 0

    def test_query():
        engine = create_engine("sqlite:///relations.db", echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        z = Zanzibar(session)
        return z.check(user, "contributor", repo)

    number = 100
    time = timeit.timeit(test_query, number=number)
    print(f"Executed in : {time/number*1000} ms\n Averaged over {number} repetitions.")


def perf_data():
    engine = create_engine("sqlite:///relations.db", echo=False)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create 5k users
    users = [User(name=f"user_{i}") for i in range(5000)]
    session.add_all(users)
    session.commit()

    # Create 100 orgs
    orgs = [Organization(name=f"org_{i}") for i in range(100)]
    session.add_all(orgs)
    session.commit()
    org_members = [Relation.from_pair("member", orgs[i]) for i in range(100)]
    session.add_all(org_members)
    session.commit()

    # Create 1k repositories
    repos = [Repository(name=f"repo_{i}") for i in range(1000)]
    session.add_all(repos)
    session.commit()

    # Create 20k issues
    issues = [Issue(name=f"issue_{i}") for i in range(20000)]
    session.add_all(issues)
    session.commit()

    # assign each repo to an org
    repo_orgs = choices(orgs, [100] * 10 + [10] * 10 + [1] * 80, k=1000)
    for repo_idx, org in enumerate(repo_orgs):
        repo_parent = Relation.from_pair("parent", repos[repo_idx])
        session.add(repo_parent)
        session.add(Assigned.from_pair(org, repo_parent))
    session.commit()

    # assign each issue to a repo
    issue_repo = choices(repos, [100] * 100 + [10] * 100 + [1] * 800, k=20000)
    for issue_idx, repo in enumerate(issue_repo):
        issue_parent = Relation.from_pair("parent", issues[issue_idx])
        session.add(issue_parent)
        session.add(Assigned.from_pair(repo, issue_parent))
    session.commit()

    # assign each user to an org
    #  each user belongs to 1-5 organizations
    user_orgs = choices(org_members, [100] * 10 + [10] * 10 + [1] * 80, k=25000)
    # half the users belong to just 1 org
    # 5% belong to 5 orgs
    user_org_number = choices([10, 20, 30, 40, 50], [10, 3, 3, 3, 1], k=5000)
    for user_idx, org_member in enumerate(user_orgs):
        user_id = user_idx % 5000
        org_num = user_idx // 5000
        if org_num >= user_org_number[user_id]:
            continue
        session.add(Assigned.from_pair(users[user_id], org_member))
    session.commit()

    #### Total relationships:
    # 1000 repo-org
    # 20000 issue-repository
    # ~5000 + 1500 + 1500 + 1500 + 1500 + 500 = 11500
    # Total about 31.5k
    # (on one test: 31528)


if __name__ == "__main__":
    perf_data()
