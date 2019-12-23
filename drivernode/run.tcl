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
diset tpcc pg_dbase citus
diset tpcc pg_user citus
diset tpcc pg_superuser citus
diset tpcc pg_defaultdbase citus
#diset tpcc pg_pass citus
#diset tpcc pg_superuserpass citus
diset tpcc pg_storedprocs false
diset tpcc pg_num_vu 256
diset tpcc pg_count_ware 256
diset tpcc pg_total_iterations 1
diset tpcc pg_driver timed
diset tpcc pg_rampup 1
diset tpcc pg_duration 1
diset tpcc pg_timeprofile true
diset tpcc pg_allwarehouse true
diset tpcc pg_keyandthink false
loadscript
print dict
vuset vu 2
vuset timestamps 1
vuset logtotemp 1
vuset showoutput 0
vuset unique 1
vuset delay 5
vuset repeat 1
vurun
wait_to_complete
vwait forever
