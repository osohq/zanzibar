relation(_: Organization, "admin");
relation(_: Organization, "member", child) if
    child in [
        "this",
        { relation: "admin" }
    ];

relation(_: Repository, "parent");
relation(_: Repository, "maintainer", child) if
    child in [
        "this",
        { parent: { resource: Organization, relation: "parent" }, relation: "admin"}
    ];

relation(_: Repository, "contributor", child) if
    child in [
        "this",
        { relation: "maintainer" },
        { 
            parent: { resource: Organization, relation: "parent" },
            relation: "member"
        }
    ];