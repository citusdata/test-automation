-- CH benchmark consists of transactional and analytical part.
-- The analytical part is a modified version of TPC-H, therefore we 
-- separate them from TPC-C to distinguish them. TPC-C tables are created
-- in hammerdb, yet these modified tables do not exist in hammerdb, so we need
-- to create them with additonal scripts.
SELECT create_reference_table('region');
SELECT create_reference_table('nation');
SELECT create_reference_table('supplier');
