#eval `ssh-agent -s`
#export RESOURCE_GROUP_NAME=onurctirtir_test_automation
#
#./delete-resource-group.sh

eval `ssh-agent -s`
ssh-add ~/.ssh/id_rsa

#./create-cluster.sh  
./connect.sh

