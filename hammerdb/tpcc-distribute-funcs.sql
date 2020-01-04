SELECT create_distributed_function('public.dbms_random (integer, integer)');
SELECT create_distributed_function('public.delivery (integer, integer)', '$1', colocate_with := 'warehouse');
SELECT create_distributed_function('public.neword ( integer, integer, integer, integer, integer, integer)', '$1', colocate_with := 'warehouse');
SELECT create_distributed_function('public.payment ( integer, integer, integer, integer, numeric, integer, numeric, character varying, character varying, numeric)', '$1', colocate_with := 'warehouse');
SELECT create_distributed_function('public.slev ( integer, integer, integer)', '$1', colocate_with := 'warehouse');
SELECT create_distributed_function('public.ostat ( integer, integer, integer, integer, character varying)', '$1', colocate_with := 'warehouse');
