# direct relation
relationship(subject, predicate, {object: object, namespace: namespace}) if
    relation(namespace, predicate, "this") and
    subject = Z._read(object: object, relation: predicate);

# computed_userset
relationship(subject, implied_predicate, object) if
    relation(object.namespace, implied_predicate, {relation: predicate}) and
    relationship(subject, predicate, object);

# tuple_to_userset
relationship(subject, implied_predicate, object) if
    relation(object.namespace, implied_predicate, { parent: {
        resource: tupleset_namespace,
        relation: object_predicate
    }, relation: subject_predicate }) and
    relationship(tupleset, object_predicate, object) and
    relationship(subject, subject_predicate, {object: tupleset, namespace: tupleset_namespace});

relation(resource, predicate, "this") if relation(resource, predicate);
