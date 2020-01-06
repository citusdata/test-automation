#!/bin/tclsh
puts "SETTING CONFIGURATION"
global complete
proc wait_to_complete {} {
global complete
set complete [vucomplete]
if {!$complete} { after 5000 wait_to_complete } else { exit }
}
dbset db pg
loadscript
diset connection pg_host replace_with_ip_address
diset tpcc pg_dbase pguser
diset tpcc pg_user pguser
diset tpcc pg_superuser pguser
diset tpcc pg_defaultdbase pguser
#diset tpcc pg_pass yourpasswordhere
#diset tpcc pg_superuserpass yourpasswordhere
diset tpcc pg_storedprocs true
diset tpcc pg_num_vu 150
diset tpcc pg_count_ware 750
diset tpcc pg_total_iterations 1000000
diset tpcc pg_driver timed
diset tpcc pg_rampup 3
diset tpcc pg_duration 10
diset tpcc pg_timeprofile false
diset tpcc pg_allwarehouse false
diset tpcc pg_keyandthink false
loadscript
print dict
buildschema
wait_to_complete
vwait forever