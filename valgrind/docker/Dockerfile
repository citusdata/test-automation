FROM ubuntu:24.04

RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/theory/pgenv

WORKDIR /pgenv
RUN git fetch && git checkout v1.3.6b

RUN apt-get update && apt-get install -y make curl
RUN ./bin/pgenv config init
RUN sed -i 's/^PGENV_CONFIGURE_OPTIONS=.*/PGENV_CONFIGURE_OPTIONS=([0]="--enable-debug" [1]="--enable-depend" [2]="--enable-cassert" [3]="CFLAGS=-ggdb -Og -fno-omit-frame-pointer -DUSE_VALGRIND")/' ./config/default.conf
RUN sed -i "s/^PGENV_MAKE_OPTIONS=.*/PGENV_MAKE_OPTIONS=([0]='-sj$(nproc)')/" ./config/default.conf

RUN apt-get update && apt-get install -y bzip2 build-essential libicu-dev pkg-config flex bison liblz4-dev libreadline-dev libzstd-dev libxslt1-dev zlib1g-dev zlib1g-dev libxml2-utils docbook-xsl xsltproc valgrind
ARG PG_VERSION
RUN ./bin/pgenv build $PG_VERSION && ./bin/pgenv switch $PG_VERSION
WORKDIR /

RUN git clone https://github.com/citusdata/citus
WORKDIR /citus
ARG CITUS_VERSION
RUN git fetch && git checkout $CITUS_VERSION
RUN PATH=/pgenv/pgsql/bin/:$PATH && ./configure --without-libcurl && make -sj$(nproc) install-all
WORKDIR /

# install python3 as it's required by Citus test suite
RUN apt-get update && apt-get install -y python3

# create a non-root user that we can use to run the tests
RUN useradd -ms /bin/bash nonrootuser
RUN chown -R nonrootuser:nonrootuser /citus /pgenv/pgsql/bin

# copy run_valgrind_test.sh to the container
COPY run_valgrind_test.sh /run_valgrind_test.sh
RUN chmod +x /run_valgrind_test.sh

USER nonrootuser
