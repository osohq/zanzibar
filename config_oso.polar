
relationship_implies("org:admin", "org:member");
relationship_on_implies("org:admin", "repo:parent", "repo:maintainer");
relationship_on_implies("org:member", "repo:parent", "repo:contributor");

relationship_implies("repo:maintainer", "repo:contributor");
relationship_on_implies("repo:contributor", "issue:parent", "issue:perm:close");

relationship_on_implies("repo:contributor", "issue:parent", "issue:perm:close");
relationship_implies( "issue:reporter",  "issue:perm:close");
