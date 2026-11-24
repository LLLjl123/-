using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net.NetworkInformation;
using System.Threading;

namespace NetworkLeakShield
{
    class DnsGuard
    {
        private static readonly string[] VpnKeywords = new[]
        {
            "tun0", "meta", "flclash", "sing-tun", "wintun", "clash", "mihomo", "wireguard", "tailscale"
        };

        private static readonly string[] VirtualIgnoreKeywords = new[]
        {
            "virtual", "hyper-v", "vethernet", "vmware", "virtualbox", "bluetooth", "loopback",
            "tun0", "meta", "flclash", "sing-tun", "wintun", "clash", "mihomo", "wireguard", "tap-"
        };

        static void Main(string[] args)
        {
            bool createdNew;
            using (var mutex = new Mutex(true, "NetworkLeakShield_DNS_Guard_Mutex", out createdNew))
            {
                if (!createdNew)
                {
                    return;
                }

                bool wasVpnOn = CheckIsVpnOn();
                if (wasVpnOn)
                {
                    ApplyCloudflareDns();
                }

                while (true)
                {
                    bool isVpnOn = CheckIsVpnOn();

                    if (isVpnOn && !wasVpnOn)
                    {
                        ApplyCloudflareDns();
                        wasVpnOn = true;
                    }
                    else if (!isVpnOn && wasVpnOn)
                    {
                        RestoreDhcpDns();
                        wasVpnOn = false;
                    }

                    Thread.Sleep(2500);
                }
            }
        }

        static bool ContainsAny(string text, string[] keywords)
        {
            if (string.IsNullOrEmpty(text)) return false;
            foreach (var kw in keywords)
            {
                if (text.IndexOf(kw, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }
            return false;
        }

        static bool CheckIsVpnOn()
        {
            try
            {
                foreach (NetworkInterface nic in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (nic.OperationalStatus != OperationalStatus.Up) continue;
                    if (ContainsAny(nic.Name, VpnKeywords) || ContainsAny(nic.Description, VpnKeywords))
                    {
                        return true;
                    }
                }
            }
            catch { }
            return false;
        }

        static List<string> GetActivePhysicalAdapters()
        {
            var result = new List<string>();
            try
            {
                foreach (NetworkInterface nic in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (nic.OperationalStatus != OperationalStatus.Up) continue;
                    if (nic.NetworkInterfaceType != NetworkInterfaceType.Wireless80211 &&
                        nic.NetworkInterfaceType != NetworkInterfaceType.Ethernet)
                    {
                        continue;
                    }
                    if (ContainsAny(nic.Name, VirtualIgnoreKeywords) ||
                        ContainsAny(nic.Description, VirtualIgnoreKeywords))
                    {
                        continue;
                    }
                    result.Add(nic.Name);
                }
            }
            catch { }
            return result;
        }

        static void ApplyCloudflareDns()
        {
            foreach (var name in GetActivePhysicalAdapters())
            {
                RunCmd("netsh interface ip set dns name=\"" + name + "\" static 1.1.1.1");
                RunCmd("netsh interface ip add dns name=\"" + name + "\" 1.0.0.1 index=2");
            }
            RunCmd("reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows NT\\DNSClient\" /v DisableSmartNameResolution /t REG_DWORD /d 1 /f");
            RunCmd("ipconfig /flushdns");
        }

        static void RestoreDhcpDns()
        {
            foreach (var name in GetActivePhysicalAdapters())
            {
                RunCmd("netsh interface ip set dns name=\"" + name + "\" dhcp");
            }
            RunCmd("ipconfig /flushdns");
        }

        static void RunCmd(string cmd)
        {
            try
            {
                var psi = new ProcessStartInfo("cmd.exe", "/c " + cmd)
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                using (var p = Process.Start(psi))
                {
                    if (p != null) p.WaitForExit(5000);
                }
            }
            catch { }
        }
    }
}
