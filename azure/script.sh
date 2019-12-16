export RESOURCE_GROUP_NAME=onurctirtir_test_automation

eval `ssh-agent -s`
ssh-add ~/.ssh/id_rsa
./delete-resource-group.sh

eval `ssh-agent -s`
ssh-add ~/.ssh/id_rsa
./create-cluster.sh  

eval `ssh-agent -s`
ssh-add ~/.ssh/id_rsa
./connect.sh

