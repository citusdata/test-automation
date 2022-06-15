function remove_string_quotations()
{
    # https://tecadmin.net/bash-remove-double-quote-string/#:~:text=A%20single%20line%20sed%20command%20can%20remove%20quotes,will%20remove%20the%20ending%20quote%20from%20the%20string.
    # https://stackoverflow.com/a/35512655
    sed -e 's/^"//' -e 's/"$//' <<<"${1:-$(</dev/stdin)}"
}

# compiles a pg version from code in the directory where it is called
# declares a PG_BIN_DIR variable in the shell and appends it to the $PATH
# variable
function install_pg_with_version()
{
    current_dir=$(realpath .)

    pg_version=$1
    pg_name=""postgresql-$pg_version""
    install_flags=${2:-""}
    
    wget -O "$pg_name.tar.gz" "https://ftp.postgresql.org/pub/source/v$pg_version/$pg_name.tar.gz"
    tar -xvzf "$pg_name.tar.gz"
    cd $pg_name

    ./configure --prefix=$current_dir/postgres $install_flags
    make -sj $(nproc) install

    cd contrib
    make -s install    

    # reset to starting dir
    cd ../..

    PG_BIN_DIR="$current_dir/postgres/bin"
    export PATH=$PATH:$PG_BIN_DIR
}

# creates a default cluster with citus dev
# declares a CITUS_DEV variable poiting to the citus_dev executable and
# a COOR_PORT variable with the port of the coordinator of the newly created
# cluster
function create_test_cluster()
{
    current_dir=$(realpath .)
    git clone https://github.com/citusdata/tools

    PG_USER=$1
    cd tools/citus_dev

    apt-get install -y python3-pip
    pip3 install -r requirements.txt

    CITUS_DEV=$current_dir/tools/citus_dev/citus_dev
    
    su - $PG_USER -c "cd $current_dir && PATH=$PATH $CITUS_DEV make citus-cluster"

    COOR_PORT=9700
}
