# Windows 系统级隐私与网络安全加固清单

为了让一台全新、未做过任何调整的 Windows 10/11 电脑从操作系统底层消除地理位置和网络身份泄露隐患，除了代理与浏览器配置外，还必须系统性地处理以下 **Windows 原生隐私与网络设置**。

本清单中的全部项目均已集成在 `scripts/harden_windows_privacy.py` 与 `scripts/one_click_harden.py` 中，支持一键应用与一键回滚。

---

## 1. 彻底关闭 Windows 系统定位服务 (Location Services)

* **为什么必须关闭？**
  Windows 定位服务（`lfsvc`）并不依赖 GPS，而是会扫描周围的 **Wi-Fi 路由器 MAC 地址（BSSID）** 并上报给微软定位库，从而在 **毫秒级精度** 下直接定位到你在中国的具体街道！任何桌面应用（如 Claude Desktop、Edge/Chrome 网页授权后）一旦调用 Windows Location API，都会瞬间暴露真实物理位置，绕过一切 VPN 代理。
* **加固配置项**：
  * 系统级权限：`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location` → `Value = "Deny"`
  * 用户级权限：`HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location` → `Value = "Deny"`
  * 组策略强锁：`HKLM\SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors` → `DisableLocation = 1`
  * 服务层停用：`Stop-Service lfsvc` + `Set-Service lfsvc -StartupType Disabled`
* **手动核验路径**：`Windows 设置 → 隐私和安全性 → 位置 → 位置服务（关）`

---

## 2. 时区、国家与 Intl 区域格式对齐（关键：绝不破坏中文界面！）

* **为什么必须对齐？**
  高敏风控站点（如 Claude、OpenAI、Stripe）会通过 JavaScript 的 `Intl.DateTimeFormat().resolvedOptions()` 检查你的浏览器时区与区域格式。如果你的代理 IP 在美国洛杉矶，但系统时区是 `Asia/Shanghai (UTC+8)`、区域格式是 `zh-CN`，就会直接命中高风险异常信号。
* **核心技巧（保留中文 UI，不乱码）**：
  * ✅ **修改系统时区**：对齐代理出口城市（例如美西设为 `Pacific Standard Time` / `UTC-08:00`）。
  * ✅ **修改国家或地区**：`Set-WinHomeLocation -GeoId 244`（美国）。
  * ✅ **修改区域格式 (Culture)**：`Set-Culture en-US`（直接修正浏览器的 `Intl` 区域检测！）。
  * ⛔ **严格保留不动**：`Windows 显示语言`（保持简体中文）与 `非 Unicode 程序的语言`（保持简体中文），这样你的桌面、设置菜单和所有国产软件完全不会变成英文或出现乱码！
* **手动核验路径**：`Windows 设置 → 时间和语言 → 语言和区域` & `日期和时间`

---

## 3. 关闭广告 ID、诊断定制体验与输入追踪

* **为什么建议关闭？**
  减少系统后台遥测和跨应用广告标识关联，降低系统背景噪音。
* **加固配置项**：
  * 广告 ID：`HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo` → `Enabled = 0`
  * 诊断定制体验：`HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy` → `TailoredExperiencesWithDiagnosticDataEnabled = 0`
  * 输入与墨迹收集：`HKCU\SOFTWARE\Microsoft\InputPersonalization` → `RestrictImplicitInkCollection = 1`、`RestrictImplicitTextCollection = 1`
* **手动核验路径**：`Windows 设置 → 隐私和安全性 → 常规` & `诊断和反馈`

---

## 4. 封堵 Windows 底层 DNS 与局域网广播漏洞

### 4.1 禁用智能多宿主名称解析 (Smart Multi-Homed Name Resolution)
* **原理**：Windows 8/10/11 为了加快上网速度，会同时向所有网卡（包括物理 WLAN 和虚拟代理 TUN）并发发送 DNS 请求，谁回得快就用谁。由于物理网卡连着国内宽带运营商，极易抢跑返回结果，造成经典的 **运营商 DNS 泄露**。
* **加固配置**：`HKLM\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient` → `DisableSmartNameResolution = 1`

### 4.2 禁用 LLMNR 链路本地多播名称解析
* **原理**：当 DNS 查询失败时，Windows 默认会向整个局域网广播 LLMNR 数据包询问主机名，容易造成局域网信息暴露或被嗅探。
* **加固配置**：`HKLM\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient` → `EnableMulticast = 0`

---

## 5. 全网卡彻底禁用 IPv6 协议栈

* **原理**：如果本地宽带分配了公网 IPv6，而代理节点仅转发 IPv4，系统会直接走原生 IPv6 访问支持双栈的网站（如 Google、Cloudflare），导致真实国内 IP 直接暴露。此外，部分严格的环境检测脚本会扫描所有网卡（含虚拟网卡），只要有任何一块网卡勾选了 `ms_tcpip6` 就会报错。
* **加固命令（管理员）**：
  ```powershell
  Get-NetAdapterBinding -ComponentID ms_tcpip6 | Disable-NetAdapterBinding -Confirm:$false
  ```

---

## 6. 物理网卡动态 DNS 看门狗 (Auto-Adapting DNS Guard)

* **为什么不能简单把物理网卡永久写死为 `1.1.1.1`？**
  如果你把 Wi-Fi 的 DNS 永久写死为 `1.1.1.1`，当你关闭代理去连酒店/机场/校园网 Wi-Fi（需要 Captive Portal 弹窗认证）或正常国内上网时，可能会打不开认证页或解析极慢。
* **最佳实践**：使用本项目内置的零依赖 C# 看门狗 (`scripts/dns_guard.cs`)：
  * 自动识别当前活跃的物理网卡（无论是有线以太网还是无线 Wi-Fi）；
  * 检测到代理 TUN 网卡启动时，自动把活跃物理网卡 DNS 锁定为 Cloudflare (`1.1.1.1` / `1.0.0.1`)；
  * 检测到代理关闭时，自动恢复物理网卡为 DHCP 自动获取，做到**代理时零泄露、关代理不抽风**。
