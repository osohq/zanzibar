with recursive issue_parents as (
    select
        *
    from
        relations
    where
        object_namespace = "issues"
        and object_key = 1
        and object_predicate = "parent"
    UNION
    select
        r.*
    from
        relations r,
        issue_parents cte
    where
        (
            r.object_namespace = cte.subject_namespace
            and r.object_key = cte.subject_key
            and r.object_predicate = cte.subject_predicate
        )
        or (
            r.id == cte.id
            and r.subject_predicate is null
        )
),
repository_parents as (
    select
        r.*
    from
        relations r,
        issue_parents
    where
        r.object_namespace = issue_parents.subject_namespace
        and r.object_key = issue_parents.subject_key
        and r.object_predicate = "parent"
    UNION
    select
        r.*
    from
        relations r,
        repository_parents cte
    where
        (
            r.object_key = cte.subject_key
            and r.object_namespace = cte.subject_namespace
            and r.object_predicate = cte.subject_predicate
        )
        or (
            r.id == cte.id
            and r.subject_predicate is null
        )
),
org_admins as (
    select
        r.*
    from
        relations r,
        repository_parents
    where
        r.object_namespace = repository_parents.subject_namespace
        and r.object_key = repository_parents.subject_key
        and r.object_predicate = "member"
    UNION
    select
        r.*
    from
        relations r,
        org_admins cte
    where
        (
            r.object_key = cte.subject_key
            and r.object_namespace = cte.subject_namespace
            and r.object_predicate = cte.subject_predicate
        )
        or (
            r.id == cte.id
            and r.subject_predicate is null
        )
)
select
    *
from
    issue_parents
union
select
    *
from
    repository_parents
union
select
    *
from
    org_admins