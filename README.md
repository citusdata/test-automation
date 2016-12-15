# test-automation
Tools for making our tests easier to run

# Running fab

- `fab basic_testing` will setup a vanilla cluster with postgres and citus for you to play with
- `fab citus:v6.0.1 basic_testing` (you can give it any git ref) is how you override the default branch (master) which fab uses.
- `fab --list` will return a list of the tasks you can run.
