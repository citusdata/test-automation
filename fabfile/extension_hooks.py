import os.path

import utils
import config

def after_citus_create(c):
    # it exposes a function which is normally not exposed by citus. It is only expected to be used in tests by design.
    # it hides citus objects from showing up in pg meta queries. e.g. 'select * from pg_class;'
    with c.cd(config.PG_LATEST):
        # write file content
        is_citus_depended_obj_func = ("CREATE OR REPLACE FUNCTION pg_catalog.is_citus_depended_object(oid,oid) "
                                      "RETURNS bool LANGUAGE C AS 'citus', "
                                      "$$is_citus_depended_object$$;")
        func_file_name = 'is_citus_depended_obj_func.sql'
        func_file_path = os.path.join(config.PG_LATEST, func_file_name)
        with open(func_file_path, 'w') as f:
            f.write(is_citus_depended_obj_func)

        # run psql command with file option
        utils.psql(c, '', func_file_path)
