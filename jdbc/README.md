To trigger the test push a branch called `jdbc/{whatever-you-want}`
To configure the citus branch or the jdbc version change the appropriate properties
in [JDBC Config](./jdbc_config.json)

Dependencies:
* [citus_dev](https://github.com/citusdata/tools/tree/develop/citus_dev)
* java jdk (most recent version is install by apt-get)
* jdbc driver for PostgreSQL (see https://jdbc.postgresql.org/)

Compare resulting output files from 6 combinations that script executes the tests [(hash, append) x (real-time, task-tracker, adaptive)].
Resulting counts should all match each other.
