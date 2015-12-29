from rest.handlers import full_query_params
from rest.query import QueryParam
from tests.test_query import Level2, Level1


def test_full_query_params():
    params = (
        QueryParam(
                model=Level2,
                attr_name=None,
                foreign_key_name='level1_pk',
                foreign_key_value=None,
        ),
        QueryParam(
                model=Level1,
                attr_name='name',
                foreign_key_name='root_pk',
                foreign_key_value=None,
        ),
    )
    _, full_params = full_query_params(params, level_0_id='root', level_1_id='level1', level_2_id='level2')
    correct_params = (
        QueryParam(
                model=Level2,
                attr_name=None,
                foreign_key_name='level1_pk',
                foreign_key_value='level1',
        ),
        QueryParam(
                model=Level1,
                attr_name='name',
                foreign_key_name='root_pk',
                foreign_key_value='root',
        ),
    )
    assert correct_params == full_params
