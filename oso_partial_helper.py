from polar.partial import TypeConstraint
from polar.variable import Variable
from sqlalchemy import sql
from sqlalchemy_oso.partial import partial_to_filter


def partial_query(oso, session, rule_name, *args, prefix=True, **partial_types):
    if len(partial_types) != 1:
        raise Exception("require exactly one partial variable argument")

    k, v = next(iter(partial_types.items()))
    var = Variable(k)
    model = v
    bindings = {var: TypeConstraint(var, model.__name__)}
    if prefix:
        args = (var, *args)
    else:
        args = (*args, var)

    results = oso.query_rule(
        rule_name,
        *args,
        bindings=bindings,
        accept_expression=True,
    )

    combined_filter = None
    has_result = False
    for result in results:
        has_result = True

        resource_partial = result["bindings"][k]
        # print(resource_partial)
        (filter, _) = partial_to_filter(
            resource_partial,
            session,
            model,
            get_model=oso.get_class,
        )
        # print(filter)
        if combined_filter is None:
            combined_filter = filter
        else:
            combined_filter = combined_filter | filter

    if not has_result:
        return sql.false()

    return combined_filter
