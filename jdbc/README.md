Run following in this directory:

```bash
./run_jdbc_tests.sh <coordinator_port> <jdbc_driver_path>
```

where,  

coordinator_port: Provide an available port for the coordinator instance of the temporary citus cluster to perform jdbc tests
jdbc_driver_path: Provide path to jdbc driver for PostgreSQL, (see https://jdbc.postgresql.org/ to download it).

Dependencies:
* citus_dev
* java jdk
* jdbc driver for PostgreSQL (see https://jdbc.postgresql.org/)

Compare resulting output files from 6 combinations that script executes the tests [(hash, append) x (real-time, task-tracker, adaptive)].
Resulting counts should all match each other.
