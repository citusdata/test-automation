function remove_string_quotations()
{
    # https://tecadmin.net/bash-remove-double-quote-string/#:~:text=A%20single%20line%20sed%20command%20can%20remove%20quotes,will%20remove%20the%20ending%20quote%20from%20the%20string.
    # https://stackoverflow.com/a/35512655
    sed -e 's/^"//' -e 's/"$//' <<<"${1:-$(</dev/stdin)}"
}

function install_pg_version()
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

    PG_EXECUTABLES="$current_dir/postgres/bin"
    PG_CONFIG="$PG_EXECUTABLES/pg_config"
    export PATH=$PATH:$PG_EXECUTABLES
}

function create_test_cluster()
{
    current_dir=$(realpath .)
    git clone https://github.com/citusdata/tools

    PG_USER=$1
    cd tools/citus_dev

    useradd $PG_USER

    apt-get install -y python3-pip
    pip3 install -r requirements.txt

    CITUS_DEV=$current_dir/tools/citus_dev/citus_dev

    apt-get install -y sudo
    echo '${PG_USER}     ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers
    
    sudo -u $PG_USER PATH="$PATH" "$CITUS_DEV" make citus-cluster

    COOR_PORT=9700
}