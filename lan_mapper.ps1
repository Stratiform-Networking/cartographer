# LAN Topology Mapper (Windows-friendly)

$ErrorActionPreference = "Stop"

Write-Host "=== LAN Mapper Starting (Windows) ==="
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function ConvertTo-UInt32 {
    param([string]$IpAddress)
    $bytes = [System.Net.IPAddress]::Parse($IpAddress).GetAddressBytes()
    [Array]::Reverse($bytes)
    return [BitConverter]::ToUInt32($bytes, 0)
}

function ConvertFrom-UInt32 {
    param([uint32]$Value)
    $bytes = [BitConverter]::GetBytes($Value)
    [Array]::Reverse($bytes)
    return ([System.Net.IPAddress]::new($bytes)).ToString()
}

function Get-NetworkCidr {
    param([string]$IpAddress, [int]$PrefixLength)

    $ipInt = ConvertTo-UInt32 $IpAddress
    if ($PrefixLength -le 0) {
        $mask = [uint32]0
    } else {
        $mask = [uint32]::MaxValue -shl (32 - $PrefixLength)
    }
    $netInt = $ipInt -band $mask
    $netIp = ConvertFrom-UInt32 $netInt
    return "$netIp/$PrefixLength"
}

function Get-IpList {
    param([string]$Cidr, [int]$MaxHosts = 1024)
    $parts = $Cidr.Split("/")
    $networkIp = $parts[0]
    $prefix = [int]$parts[1]

    $netInt = ConvertTo-UInt32 $networkIp
    $hostCount = [math]::Pow(2, 32 - $prefix)
    if ($hostCount -le 2) {
        return @($networkIp)
    }

    $start = $netInt + 1
    $end = $netInt + [uint32]$hostCount - 2
    $count = $end - $start + 1

    if ($count -gt $MaxHosts) {
        $end = $start + [uint32]$MaxHosts - 1
    }

    $ips = New-Object System.Collections.Generic.List[string]
    for ($i = $start; $i -le $end; $i++) {
        $ips.Add((ConvertFrom-UInt32 $i)) | Out-Null
    }
    return $ips
}

function Resolve-Hostname {
    param([string]$IpAddress)

    $hostName = $null

    try {
        $ptr = Resolve-DnsName -Name $IpAddress -Type PTR -ErrorAction Stop
        if ($ptr) {
            $hostName = $ptr.NameHost.TrimEnd(".")
        }
    } catch {
        $null = $null
    }

    if (-not $hostName) {
        try {
        $nbt = nbtstat -A $IpAddress 2>$null
        $line = $nbt | Select-String -Pattern "<00>" | Select-Object -First 1
        if ($line) {
            $hostName = ($line.Line.Trim() -split "\s+")[0]
        }
    } catch {
        $null = $null
    }
    }

    if (-not $hostName) {
        $hostName = "Unknown"
    }

    return $hostName
}

function Get-Role {
    param([string]$Name, [string]$IpAddress, [string]$GatewayIp, [string]$Mac)

    $lname = ""
    if ($Name) {
        $lname = $Name.ToLowerInvariant()
    }
    $role = "unknown"

    if ($GatewayIp -and $IpAddress -eq $GatewayIp) {
        $role = "gateway/router"
    } elseif ($lname -like "*routerboard*") {
        $role = "gateway/router"
    } elseif ($lname -match "tl-sg|tp-link|tplink|unifi|cisco|netgear") {
        $role = "switch/ap"
    } elseif ($lname -like "*firewalla*") {
        $role = "firewall"
    } elseif ($lname -match "nas|ugreen|synology|qnap") {
        $role = "nas"
    } elseif ($lname -match "jellyfin|wizarr|b2backup|postgres|onyx|n8n|grafana|prometheus") {
        $role = "service"
    } elseif ($lname -match "server|debian|ubuntu|centos|redhat|fedora|arch|manjaro|linux") {
        $role = "server"
    } elseif ($lname -match "desktop|laptop|iphone|android|windows|macbook|imac|surface") {
        $role = "client"
    }

    if ($role -eq "unknown" -and $Mac) {
        $macNorm = $Mac.ToLowerInvariant().Replace("-", ":")
        $virtualOui = @(
            "02:42:ac",
            "00:50:56",
            "00:0c:29",
            "00:05:69",
            "00:16:3e",
            "00:15:5d",
            "00:1c:42",
            "00:03:ff"
        )
        foreach ($prefix in $virtualOui) {
            if ($macNorm.StartsWith($prefix)) {
                $role = "service"
                break
            }
        }
    }

    return $role
}

Write-Host "Detecting LAN interface..."

$netConfigs = Get-NetIPConfiguration | Where-Object { $_.IPv4Address -and $_.IPv4Address.IPAddress }
$validConfigs = $netConfigs | Where-Object {
    $_.InterfaceAlias -notmatch "loopback|virtual|vethernet|hyper-v|vmware|virtualbox|docker|wsl|tailscale|vpn|bluetooth"
}
if (-not $validConfigs) {
    $validConfigs = $netConfigs
}

$lanConfig = $validConfigs | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1
if (-not $lanConfig) {
    $lanConfig = $validConfigs | Select-Object -First 1
}

if (-not $lanConfig) {
    Write-Host "ERROR: No valid LAN interface found."
    exit 1
}

$ipEntry = $lanConfig.IPv4Address | Select-Object -First 1
$hostIp = $ipEntry.IPAddress
$prefixLength = [int]$ipEntry.PrefixLength
$gateway = $null
if ($lanConfig.IPv4DefaultGateway) {
    $gateway = $lanConfig.IPv4DefaultGateway.NextHop
}

$subnet = Get-NetworkCidr $hostIp $prefixLength

Write-Host "Using LAN interface: $($lanConfig.InterfaceAlias)"
Write-Host "Host IP: $hostIp/$prefixLength"
Write-Host "Subnet: $subnet"
Write-Host "Gateway: $gateway"
Write-Host ""

$tempDir = Join-Path $ScriptDir "lanmap_tmp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$arpFile = Join-Path $tempDir "arp.txt"
$nmapFile = Join-Path $tempDir "nmap.txt"
$hostsFile = Join-Path $tempDir "hosts.txt"
$lldpFile = Join-Path $tempDir "lldp.txt"
$snmpFile = Join-Path $tempDir "snmp.txt"

$scanCidr = $subnet
if ($prefixLength -lt 24) {
    $scanCidr = Get-NetworkCidr $hostIp 24
    Write-Host "Large subnet detected; limiting sweep to $scanCidr"
}

Write-Host "Waking up devices (ping sweep)..."
$ipList = Get-IpList -Cidr $scanCidr -MaxHosts 1024

$testConnSupportsTimeout = (Get-Command Test-Connection).Parameters.ContainsKey("TimeoutSeconds")
function Test-HostUp {
    param([string]$IpAddress)
    $args = @{ ComputerName = $IpAddress; Count = 1; Quiet = $true }
    if ($testConnSupportsTimeout) {
        $args.TimeoutSeconds = 1
    }
    return Test-Connection @args
}

$aliveIps = New-Object System.Collections.Generic.List[string]
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $aliveIps = $ipList | ForEach-Object -Parallel {
        $testConnSupportsTimeout = (Get-Command Test-Connection).Parameters.ContainsKey("TimeoutSeconds")
        $args = @{ ComputerName = $_; Count = 1; Quiet = $true }
        if ($testConnSupportsTimeout) {
            $args.TimeoutSeconds = 1
        }
        if (Test-Connection @args) { $_ }
    } -ThrottleLimit 64
} else {
    foreach ($ip in $ipList) {
        try {
            if (Test-HostUp $ip) {
                $aliveIps.Add($ip) | Out-Null
            }
        } catch {
            $null = $null
        }
    }
}

Write-Host "Collecting ARP table..."
$macByIp = @{}
try {
    $neighbors = Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex $lanConfig.InterfaceIndex -ErrorAction Stop
    $neighbors | ForEach-Object {
        if ($_.IPAddress -and $_.LinkLayerAddress -and $_.LinkLayerAddress -ne "00-00-00-00-00-00") {
            $mac = $_.LinkLayerAddress.Replace("-", ":")
            $macByIp[$_.IPAddress] = $mac
        }
    }
    $neighbors | ForEach-Object {
        "$($_.IPAddress) $($_.LinkLayerAddress) $($_.State)"
    } | Set-Content $arpFile
} catch {
    $arpOutput = arp -a
    $arpOutput | Set-Content $arpFile
    foreach ($line in $arpOutput) {
        if ($line -match "^\s*([0-9\.]+)\s+([0-9a-fA-F:-]{11,})\s+") {
            $mac = $matches[2].Replace("-", ":")
            $macByIp[$matches[1]] = $mac
        }
    }
}

Write-Host "Running Nmap ping sweep..."
$hasNmap = [bool](Get-Command nmap -ErrorAction SilentlyContinue)
if ($hasNmap) {
    try {
        & nmap -sn $scanCidr -oG $nmapFile 2>$null | Out-Null
    } catch {
        $hasNmap = $false
    }
}

if (-not $hasNmap -or -not (Test-Path $nmapFile)) {
    "# Nmap scan (fallback from arp/ping)" | Set-Content $nmapFile
    $fallbackIps = @()
    $fallbackIps += $macByIp.Keys
    $fallbackIps += $aliveIps
    $fallbackIps = $fallbackIps | Sort-Object -Unique
    foreach ($ip in $fallbackIps) {
        "Host: $ip () Status: Up" | Add-Content $nmapFile
    }
}

Write-Host "Collecting hostnames..."
"" | Set-Content $hostsFile

$ipsFromNmap = @()
if (Test-Path $nmapFile) {
    foreach ($line in Get-Content $nmapFile) {
        if ($line -match "Host:\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)") {
            $ipsFromNmap += $matches[1]
        }
    }
}
$ipsFromNmap = $ipsFromNmap | Sort-Object -Unique

foreach ($ip in $ipsFromNmap) {
    $resolvedHost = Resolve-Hostname $ip
    "$ip | $resolvedHost" | Add-Content $hostsFile
}

Write-Host "Classifying hosts..."
$hostName = @{}
$hostRole = @{}
$depth = @{}

foreach ($line in Get-Content $hostsFile) {
    if (-not $line.Trim()) { continue }
    $parts = $line -split "\|", 2
    $ip = $parts[0].Trim()
    $name = if ($parts.Count -gt 1) { $parts[1].Trim() } else { "Unknown" }

    $hostName[$ip] = $name
    $mac = $null
    if ($macByIp.ContainsKey($ip)) { $mac = $macByIp[$ip] }
    $role = Get-Role -Name $name -IpAddress $ip -GatewayIp $gateway -Mac $mac
    $hostRole[$ip] = $role
    $depth[$ip] = 99
}

if ($gateway) {
    $depth[$gateway] = 0
}

foreach ($ip in $depth.Keys) {
    $role = $hostRole[$ip]
    switch ($role) {
        "gateway/router" { $depth[$ip] = 0 }
        "switch/ap" { $depth[$ip] = 1 }
        "firewall" { $depth[$ip] = 1 }
        "server" { $depth[$ip] = 2 }
        "nas" { $depth[$ip] = 2 }
        "service" { $depth[$ip] = 2 }
        "client" { $depth[$ip] = 2 }
        default { $depth[$ip] = 2 }
    }
}

$output = Join-Path $ScriptDir "network_map.txt"
"### LAN NETWORK MAP" | Set-Content $output
"Generated: $(Get-Date)" | Add-Content $output
"" | Add-Content $output
"Gateway: $gateway ($($hostName[$gateway]))" | Add-Content $output
"LAN Interface: $($lanConfig.InterfaceAlias)" | Add-Content $output
"Subnet: $subnet" | Add-Content $output
"" | Add-Content $output
"=== Devices Found ===" | Add-Content $output

foreach ($ip in $hostName.Keys | Sort-Object) {
    $name = $hostName[$ip]
    $role = $hostRole[$ip]
    $d = $depth[$ip]
    $line = "{0,-15} | {1,-35} | role={2,-15} | depth={3}" -f $ip, $name, $role, $d
    $line | Add-Content $output
}

"" | Add-Content $output
"=== LLDP Topology (raw) ===" | Add-Content $output

$lldpData = $null
if (Get-Command lldpctl -ErrorAction SilentlyContinue) {
    $lldpData = & lldpctl 2>$null
} elseif (Get-Command lldpcli -ErrorAction SilentlyContinue) {
    $lldpData = & lldpcli show neighbors 2>$null
}
if (-not $lldpData) {
    $lldpData = "LLDP data not available on this Windows host."
}
$lldpData | Set-Content $lldpFile
Get-Content $lldpFile | Add-Content $output
"" | Add-Content $output

"=== SNMP Hostnames (sysName) ===" | Add-Content $output
if (Get-Command snmpwalk -ErrorAction SilentlyContinue) {
    "" | Set-Content $snmpFile
    foreach ($line in Get-Content $hostsFile) {
        if (-not $line.Trim()) { continue }
        $ip = ($line -split "\|")[0].Trim()
        if ($ip) {
            try {
                snmpwalk -v2c -c public -t 1 -r 1 $ip 1.3.6.1.2.1.1.5.0 2>$null | Add-Content $snmpFile
            } catch {
                $null = $null
            }
        }
    }
} else {
    "SNMP utilities not installed." | Set-Content $snmpFile
}
Get-Content $snmpFile | Add-Content $output
"" | Add-Content $output

"=== Heuristic Topology Tree ===" | Add-Content $output
"" | Add-Content $output
"Gateway (depth 0):" | Add-Content $output
if ($gateway) {
    "  - $gateway ($($hostName[$gateway])) [$($hostRole[$gateway])]" | Add-Content $output
} else {
    "  - Unknown" | Add-Content $output
}
"" | Add-Content $output
"Infrastructure (depth 1: switches / AP / firewall):" | Add-Content $output
foreach ($ip in $hostRole.Keys | Sort-Object) {
    if ($hostRole[$ip] -in @("switch/ap", "firewall")) {
        "  - {0,-15} ({1}) [{2}]" -f $ip, $hostName[$ip], $hostRole[$ip] | Add-Content $output
    }
}
"" | Add-Content $output
"Servers / NAS / Services (depth 2):" | Add-Content $output
foreach ($ip in $hostRole.Keys | Sort-Object) {
    if ($hostRole[$ip] -in @("server", "nas", "service")) {
        "  - {0,-15} ({1}) [{2}]" -f $ip, $hostName[$ip], $hostRole[$ip] | Add-Content $output
    }
}
"" | Add-Content $output
"Clients (depth 2):" | Add-Content $output
foreach ($ip in $hostRole.Keys | Sort-Object) {
    if ($hostRole[$ip] -eq "client") {
        "  - {0,-15} ({1}) [{2}]" -f $ip, $hostName[$ip], $hostRole[$ip] | Add-Content $output
    }
}
"" | Add-Content $output
"Unknown-role devices (depth 2):" | Add-Content $output
foreach ($ip in $hostRole.Keys | Sort-Object) {
    if ($hostRole[$ip] -eq "unknown" -and $ip -ne $gateway) {
        "  - {0,-15} ({1}) [{2}]" -f $ip, $hostName[$ip], $hostRole[$ip] | Add-Content $output
    }
}
"" | Add-Content $output

Write-Host ""
Write-Host "Network map generated:"
Write-Host "  -> $output"
Write-Host ""
Write-Host "You can view it with:"
Write-Host "  Get-Content $output"
Write-Host ""
