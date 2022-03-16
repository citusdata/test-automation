# Self-elevate the script if required
if (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')) {
    if ([int](Get-CimInstance -Class Win32_OperatingSystem | Select-Object -ExpandProperty BuildNumber) -ge 6000) {
    $CommandLine = "-File `"" + $MyInvocation.MyCommand.Path + "`" " + $MyInvocation.UnboundArguments
    Start-Process -FilePath PowerShell.exe -Verb Runas -ArgumentList $CommandLine
    Exit
    }
}

$python_script = @"
from urllib.request import Request, urlopen
import re
import json
import ipaddress
import subprocess


req = Request(
    "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519",
    headers={"User-Agent": "Mozilla/5.0"},
)

with urlopen(req) as response:
    response_content = response.read().decode("utf-8")
    ips_url = re.search(
        '"(https://[^"]*ServiceTags_Public[^"]*)"', response_content
    ).group(1)

req = Request(
    ips_url,
    headers={"User-Agent": "Mozilla/5.0"},
)
with urlopen(req) as response:
    data = json.load(response)

for ip_info in data["values"]:
    if ip_info["name"] == "AzureCloud":
        all_cidrs = ip_info["properties"]["addressPrefixes"]
        break
else:
    raise Exception("Could not find ip info for AzureCloud")

for cidr in all_cidrs:
    network = ipaddress.ip_network(cidr)
    if network.version == 4:
        subprocess.run(
            [
                "route",
                "add",
                str(network.network_address),
                "mask",
                str(network.netmask),
                "100.64.108.75",
                "metric",
                "311",
            ],
            check=True,
        )
    else:
        # TODO: do something similar for IPv6
        ...
"@
echo $python_script | python

Read-Host "Press Enter to continue..."