In order to generate a sql file that contains random procedures and calls, use `generate_procedure.py`. 
This will generate `init.sql` and `query.sql`. `init.sql` contains table definitions, settings, procedures etc. `query.sql` contains producedure calls.

The generated procedures are pushed down to workers.