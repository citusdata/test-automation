-- Sccsid:     @(#)dss.ddl	2.1.8.1

CREATE TABLE nation
(
    n_nationkey  INTEGER not null,
    n_name       CHAR(25) not null,
    n_regionkey  INTEGER not null,
    n_comment    VARCHAR(152)
);

select create_distributed_table('nation', 'n_nationkey', 'append');


CREATE TABLE region
(
    r_regionkey  INTEGER not null,
    r_name       CHAR(25) not null,
    r_comment    VARCHAR(152)
);

select create_distributed_table('region', 'r_regionkey', 'append');

CREATE TABLE part
(
    p_partkey     INTEGER not null,
    p_name        VARCHAR(55) not null,
    p_mfgr        CHAR(25) not null,
    p_brand       CHAR(10) not null,
    p_type        VARCHAR(25) not null,
    p_size        INTEGER not null,
    p_container   CHAR(10) not null,
    p_retailprice DOUBLE PRECISION not null,
    p_comment     VARCHAR(23) not null
);

select create_distributed_table('part', 'p_partkey', 'append');


CREATE TABLE supplier
(
    s_suppkey     INTEGER not null,
    s_name        CHAR(25) not null,
    s_address     VARCHAR(40) not null,
    s_nationkey   INTEGER not null,
    s_phone       CHAR(15) not null,
    s_acctbal     DOUBLE PRECISION not null,
    s_comment     VARCHAR(101) not null
);

select create_distributed_table('supplier', 's_suppkey', 'append');


CREATE TABLE partsupp
(
    ps_partkey     INTEGER not null,
    ps_suppkey     INTEGER not null,
    ps_availqty    INTEGER not null,
    ps_supplycost  DOUBLE PRECISION  not null,
    ps_comment     VARCHAR(199) not null
);

select create_distributed_table('partsupp', 'ps_partkey', 'append');


CREATE TABLE customer
(
    c_custkey     INTEGER not null,
    c_name        VARCHAR(25) not null,
    c_address     VARCHAR(40) not null,
    c_nationkey   INTEGER not null,
    c_phone       CHAR(15) not null,
    c_acctbal     DOUBLE PRECISION   not null,
    c_mktsegment  CHAR(10) not null,
    c_comment     VARCHAR(117) not null
);

select create_distributed_table('customer', 'c_custkey', 'append');


CREATE TABLE ORDERS
(
    o_orderkey       BIGINT not null,
    o_custkey        INTEGER not null,
    o_orderstatus    CHAR(1) not null,
    o_totalprice     DOUBLE PRECISION not null,
    o_orderdate      DATE not null,
    o_orderpriority  CHAR(15) not null,  
    o_clerk          CHAR(15) not null, 
    o_shippriority   INTEGER not null,
    o_comment        VARCHAR(79) not null
);

select create_distributed_table('ORDERS', 'o_orderkey', 'append');


CREATE TABLE LINEITEM
(
    l_orderkey    BIGINT not null,
    l_partkey     INTEGER not null,
    l_suppkey     INTEGER not null,
    l_linenumber  INTEGER not null,
    l_quantity    DOUBLE PRECISION not null,
    l_extendedprice  DOUBLE PRECISION not null,
    l_discount    DOUBLE PRECISION not null,
    l_tax         DOUBLE PRECISION not null,
    l_returnflag  CHAR(1) not null,
    l_linestatus  CHAR(1) not null,
    l_shipdate    DATE not null,
    l_commitdate  DATE not null,
    l_receiptdate DATE not null,
    l_shipinstruct CHAR(25) not null,
    l_shipmode     CHAR(10) not null,
    l_comment      VARCHAR(44) not null
);

select create_distributed_table('LINEITEM', 'l_orderkey', 'append');


