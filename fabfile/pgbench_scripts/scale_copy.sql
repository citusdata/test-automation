\set afile `echo "${HOME}/scale_test_data.csv"`
COPY test_table FROM :'afile';

