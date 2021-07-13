relation("organizations", "admin");
relation("organizations", "member", child) if
    child in [
        "this",
        { relation: "admin" }
    ];

relation("repositories", "parent");
relation("repositories", "maintainer",  child) if
    child in [
        "this",
        { parent: { resource: "organizations", relation: "parent" }, relation: "admin"}
    ];
relation("repositories", "contributor", child) if
    child in [
        "this",
        { relation: "maintainer" },
        { 
            parent: { resource: "organizations", relation: "parent" },
            relation: "member"
        }
    ];

relation("issues", "owner");
relation("issues", "parent");
relation("issues", "permission:close", child) if 
    child in [
        { relation: "owner"},
        {
            parent: { resource: "repositories", relation: "parent" },
            relation: "contributor"
        }
    ];
