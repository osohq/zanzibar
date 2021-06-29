from sqlalchemy.orm import sessionmaker

from models import *
from zanzibar import *


def test_zanzibar():
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

    issue_owner = Relation.from_pair("owner", issue)
    repo_parent = Relation.from_pair("parent", anvil)
    eng_member = Relation.from_pair("member", eng)
    org_admin = Relation.from_pair("admin", acme)
    repo_contributor = Relation.from_pair("contributor", anvil)
    session.add_all([issue_owner, repo_parent, eng_member, org_admin, repo_contributor])
    session.commit()

    session.add_all(
        [
            Assigned.from_pair(alice, issue_owner),
            Assigned.from_pair(acme, repo_parent),
            Assigned.from_pair(alice, org_admin),
            Assigned.from_pair(alice, eng_member),
            Assigned.from_pair(eng_member, repo_contributor),
            Assigned.from_pair(bob, repo_contributor),
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
