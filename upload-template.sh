#!/bin/bash

aws s3 cp citus.json s3://citus-tests/
aws s3api put-object-acl --bucket citus-tests --key citus.json --acl public-read
