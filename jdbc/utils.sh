function remove_string_quotations()
{
    if [ "$#" != 1 ]; then
        echo "Expected one quoted string argument"
        exit 1
    fi

    # https://tecadmin.net/bash-remove-double-quote-string/#:~:text=A%20single%20line%20sed%20command%20can%20remove%20quotes,will%20remove%20the%20ending%20quote%20from%20the%20string.
    # https://stackoverflow.com/a/35512655
    sed -e 's/^"//' -e 's/"$//' <<<"${1:-$(</dev/stdin)}"
}

function install_pg_version()
{
    if [ "$#" < 1 ]; then
        echo "Expected at least one version argument"
        exit 1
    fi

    pg_version=$1
    pg_name=""postgresql-$pg_version""
    install_flags=${2:-""}
    
    wget -O "$pg_name.tar.gz" "https://ftp.postgresql.org/pub/source/v$pg_version/$pg_name.tar.gz"
    tar -xvzf "$pg_name.tar.gz"
    cd $pg_name

    ./configure --prefix=$pg_version $install_flags
    make -sj $(nproc) install

    cd contrib
    make -s install    

    # reset to starting dir
    cd ../..
}