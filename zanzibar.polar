# assigned has relation_type to resource if
# assigned has a relation which matches the
# type and resource
assigned(assigned: Assigned, relation_type, resource) if
    relation(resource, relation_type, "this") and
    rel = assigned.relation and
    rel.relation = relation_type and # rel.relation = "contributor"
    rel.namespace = resource.__tablename__ and # rel.namespace = "repositories"
    rel.key = resource.id; # rel.key = 1

# this is "computed_userset" 
assigned(assigned: Assigned, relation_type, resource) if
    relation(resource, relation_type, {relation: parent_relation}) and
    assigned(assigned, parent_relation, resource);

# this is the "tupleset_to_userset"
assigned(assigned: Assigned, relation_type, resource) if
    relation(resource, relation_type, { parent: {
        resource: parent_resource_type,
        relation: parent_resource_relation
    }, relation: relation_to_parent }) and
    parent in Z.expand(parent_resource_type, parent_resource_relation, resource) and
    assigned(assigned, relation_to_parent, parent);

relation(resource, relation_type, "this") if relation(resource, relation_type);