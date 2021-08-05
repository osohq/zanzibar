allow(user, action, resource) if
    relationship(user, action, resource);

# relationship(user: User, role, org: Organization) if
#     user_role in org.user_roles and
#     user_role.role = role and
#     user_role.user = user;

# relationship(user: User, role, repo: Repository) if
#     team_role in repo.team_roles and
#     team_role.role = role and
#     team = team_role.team and
#     team_member in team.members and
#     user = team_member.user;

relationship(user: User, role, org: Organization) if
    org_role in user.org_roles and
    org_role.role = role and
    org_role.organization = org;

relationship(user: User, role, repo: Repository) if
    user_team in user.teams and
    team = user_team.team and
    repo_role in team.repo_roles and
    repo_role.role = role and
    repo_role.repository = repo;

# relationship(user: User, "issue:reporter", issue: Issue) if
#     user = issue.reporter;

# relationship(repository, "issue:parent", issue: Issue) if
#     repository = issue.repository and
#     repository matches Repository;

# relationship(organization, "repo:parent", repository: Repository) if
#     organization = repository.organization and
#     organization matches Organization;

relationship(user: User, "issue:reporter", issue) if
    issue in user.issues_created and
    issue matches Issue;

relationship(repository: Repository, "issue:parent", issue) if
    issue in repository.issues and
    issue matches Issue;

relationship(organization: Organization, "repo:parent", repository) if
    repository in organization.repositories and
    repository matches Repository;

# computed_userset
relationship(subject, implied_predicate, object) if
    relationship_implies(predicate, implied_predicate) and
    relationship(subject, predicate, object);

# tuple_to_userset
relationship(subject, implied_predicate, object) if
    relationship_on_implies(subject_predicate, object_predicate, implied_predicate) and
    relationship(tupleset, object_predicate, object) and
    relationship(subject, subject_predicate, tupleset);

relation(resource, predicate, "this") if relation(resource, predicate);
