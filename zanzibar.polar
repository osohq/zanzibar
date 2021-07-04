# assigned has relation_type to resource if
# assigned has a relation which matches the
# type and resource
assigned(tuple: RelationTuple, relation_type, resource) if
    relation(resource, relation_type, "this") and
    tuple.relation = relation_type and # relation = "contributor"
    tuple.object_namespace = resource.__tablename__ and # object_namespace = "repositories"
    tuple.subject_relation = nil and # should not a relative relation
    tuple.object_key = resource.id; # object_key = 1

# this is "computed_userset" 
assigned(tuple: RelationTuple, relation_type, resource) if
    relation(resource, relation_type, {relation: parent_relation}) and
    assigned(tuple, parent_relation, resource);

# this is the "tupleset_to_userset"
assigned(tuple: RelationTuple, relation_type, resource) if
    relation(resource, relation_type, { parent: {
        resource: parent_resource_type,
        relation: parent_resource_relation
    }, relation: relation_to_parent }) and
    parent in Z.expand(parent_resource_type, parent_resource_relation, resource) and
    assigned(tuple, relation_to_parent, parent);

relation(resource, relation_type, "this") if relation(resource, relation_type);