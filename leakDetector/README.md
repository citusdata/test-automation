In order to generate a sql file that contains fast path router queries, use `generate_tables_queries.py`. 
This will generate `init.sql` and `query.sql`. `init.sql` contains table definitions, settings, procedures etc. `query.sql` contains producedure calls.

`leak_detector.py` can be used to monitor the memory usage while running a sql file.
In order run it:

```bash
./leak_detector.py <coordinator port> <worker_port> <init.sql> <query.sql>
```

Example:

```bash
./leak_detector.py 9700 9701 ./init.sql ./query.sql
```

`init.sql` will be run once on the `coordinator_port`. `query.sql` will be run on the `worker_port` and the memory usage will be saved to a file named `memory_<pid>.out` peroodically. **Worker session creates another process to run the queries therefore the monitored pid is currently not correct, use `ps -aux` to monitor it manually for now**.
