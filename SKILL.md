---
name: network-leak-shield
description: 面向全新 Windows 电脑的七层全链路网络隐私与防泄露一键加固方案（系统定位关闭、时区/Intl区域对齐、IPv6阻断、DNS防泄露与动态看门狗、代理配置国内DNS净化、WinINet/PAC残留清理、Edge与Chrome WebRTC/DoH加固）；用于为 AI 工具（Claude/OpenAI）、指纹浏览器、主流浏览器一键搭建零泄露安全环境。
---

# Network Leak Shield (全链路网络防泄漏一键加固技能)

本技能面向**一台什么都没有做过的全新 Windows 10/11 电脑**，提供从操作系统底层到应用浏览器的**七层一键防泄露加固与自愈流程**，专门消除访问高风控海外服务（Claude、OpenAI、Google 等）时的 IP、DNS、WebRTC、IPv6 及物理定位暴露隐患，并完整支持**安全备份与一键回滚**。

---

## 核心防御模型：七层全链路防护架构

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Layer 7: 应用与指纹层 (Fingerprints & Isolation)                            │
│  • 高风控场景(注册/敏感AI账号): 指纹浏览器(EasyBR/AdsPower)禁用WebRTC+伪装硬件 │
│  • 日常高速场景(查资料/开发): 加固后的 Edge / Chrome (企业组策略锁死)         │
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 6: 主流浏览器防泄露层 (Edge + Chrome Enterprise Policy & Prefs)       │
│  • WebRtcIPHandlingPolicy = disable_non_proxied_udp (彻底禁非代理 UDP)      │
│  • DnsOverHttpsMode = secure (强制 Cloudflare 1.1.1.1 加密 DoH)            │
│  • DefaultGeolocationSetting = 2 (禁网页地理定位) / 禁网络预测预解析         │
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 5: 系统代理与 WinINet 协议栈 (Ghost PAC & Dead Proxy Cleanup)         │
│  • 清理游戏加速器/工具箱残留的死代理与 PAC 脚本 (127.0.0.1:26561/pac 等)     │
│  • 重置注册表 Connections 二进制直连结构 + Win32 API 广播刷新 + 清 Steam 缓存│
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 4: 代理内核纯净化层 (FlClash / Clash Verge / Mihomo Party)            │
│  • 扫描并清除订阅配置及 FlClash 内部 patchClashConfig 中暗藏的国内 DNS       │
│    (腾讯 doh.pub / 阿里 223.5.5.5 / DNSPod / 114)，统一替换为 Cloudflare DoH│
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 3: 动态自适应 DNS 看门狗层 (Zero-Dependency C# Daemon)                │
│  • 自动识别活跃物理网卡(Wi-Fi/有线)，无需硬编码网卡名                        │
│  • 代理/TUN 开启时自动锁定 1.1.1.1 / 1.0.0.1；关闭代理时自动恢复 DHCP        │
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Windows 底层网络协议层 (IPv6 / Smart DNS / LLMNR)                  │
│  • 全面解除所有物理与虚拟网卡 IPv6 (ms_tcpip6) 绑定，阻断双栈旁路泄露        │
│  • DisableSmartNameResolution = 1 (杜绝跨网卡并发解析泄露运营商 DNS)         │
│  • EnableMulticast = 0 (关闭 LLMNR 局域网广播解析)                          │
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Windows 系统隐私与区域对齐层 (Location / Telemetry / Intl)         │
│  • 彻底关闭系统定位服务 (HKLM/HKCU=Deny + 组策略 + 停用 lfsvc 防止Wi-Fi定位) │
│  • 关闭广告 ID、诊断定制体验与输入法追踪                                     │
│  • 对齐代理目标地区的时区、国家与区域格式(en-US)，严格保留简体中文显示界面！  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 一键执行工作流（面向全新电脑）

当用户要求为一台新电脑或现有电脑一键搭建防泄露网络环境时，按以下标准流程执行：

### 1. 先做只读体检（了解现状，不做任何修改）
```bash
python scripts/one_click_harden.py --audit
```

### 2. 确认目标代理地区后，以管理员身份一键全链路加固
```bash
# 例如代理出口在美国西部（洛杉矶/加州）：
python scripts/one_click_harden.py --apply --region us-west

# 支持的地区预设：us-west | us-east | jp | sg | uk | skip（skip 表示不改动系统时区和区域）
```
* 执行前脚本会自动备份原始系统时区、国家与区域格式至 `%LOCALAPPDATA%\NetworkLeakShield\os_backup.json`。
* 如用户不想安装常驻计划任务看门狗，可附加 `--skip-guard`。

### 3. 一键无损回滚（任何时候均可恢复默认）
```bash
python scripts/one_click_harden.py --rollback
```

---

## 自动化工具集一览

| 脚本文件 | 对应层级 | 核心功能 | 推荐权限 |
| :--- | :--- | :--- | :--- |
| `scripts/one_click_harden.py` | **总控引擎** | 一键串联执行 `--audit` / `--apply` / `--rollback` | 管理员 |
| `scripts/audit_environment.py` | **全层体检** | 七层全面检测：定位、隐私、时区、IPv6、DNS 实测、WinINet、Clash、浏览器 | 普通用户 |
| `scripts/harden_windows_privacy.py` | **Layer 1 & 2** | 关定位服务(`lfsvc`)/广告ID/追踪、禁多宿主DNS/LLMNR、关全网卡IPv6、对齐时区区域 | 管理员 |
| `scripts/dns_guard.cs` | **Layer 3** | 零依赖 C# 动态看门狗源码（自动适配物理网卡，TUN开锁CF、TUN关恢复DHCP） | 编译使用 |
| `scripts/deploy_dns_guard.py` | **Layer 3** | 调用系统内置 `csc.exe` 编译看门狗并注册/卸载开机自启守护任务 | 管理员 |
| `scripts/purge_clash_chinese_dns.py` | **Layer 4** | 净化 FlClash / Clash Verge Rev / Nyanpasu / Mihomo Party 配置与补丁中的国内 DNS | 普通用户 |
| `scripts/clean_proxy_residue.py` | **Layer 5** | 清除加速器/旧代理残留的 WinINet 死代理与幽灵 PAC，修复 Steam/应用断网 | 普通用户 |
| `scripts/harden_browsers.py` | **Layer 6** | 同时加固 Edge & Chrome（管理员写企业组策略锁死；普通用户写 Preferences + 快捷方式） | 管理员最佳 |

---

## 指纹浏览器与代理软件人工核对清单

脚本无法直接替用户填写代理订阅或第三方指纹浏览器 UI，执行完一键脚本后，引导用户完成以下 3 项快速确认：

1. **代理软件（FlClash / Clash Verge Rev）**：
   * 开启 **TUN 模式（虚拟网卡）** 与 **全局/规则分流**，确认代理软件内 **IPv6 开关为关闭**，并在执行 `purge_clash_chinese_dns.py` 后**重载配置**。
2. **指纹浏览器（EasyBR / AdsPower 等，用于高风控账号）**：
   * 代理填本地混合端口（如 `SOCKS5 127.0.0.1:7890`）；
   * **WebRTC 设为 `禁用`**（本地代理环境下用“替换”容易探针失败报错）；
   * 时区对齐代理出口（如 `America/Los_Angeles`），语言显式设为 `en-US`（不要选“基于 IP 自动生成”，因 `127.0.0.1` 无法识别）；
   * 字体设为关闭或噪点，不开启第三方 Cookie。
3. **在线权威验收测试**：
   * **DNS 泄露检测**：`https://browserleaks.com/dns`（全海外 Cloudflare/Google，无国内运营商）
   * **WebRTC 穿透检测**：`https://browserleaks.com/webrtc`（确认显示 `✓ No Public IP Leak` 且 `Public IP Address: -`）
   * **IP 纯净度与属性**：`https://ippure.com`（确认原生住宅 IP、低纯净度系数、高真人流量比）
   * **浏览器中国化信号检测**：`https://fuckclaude.com`（低风险）

---

## 深度技术参考文档

遇到特定疑问或需要向用户解释原理时，按需阅读 `references/` 下的专题文档：
* `references/WINDOWS_PRIVACY_CHECKLIST.md` — Windows 定位服务、广告 ID、保留中文 UI 对齐 Intl 区域、LLMNR 与 Smart DNS 详解
* `references/WEBRTC_MECHANICS.md` — WebRTC STUN 穿透原理、公网泄露 vs 局域网私网 IP 误报辨析、媒体权限与 mDNS 关系
* `references/GEOIP_DISCREPANCIES.md` — 同一 IP 跨库城市不一致（如加州尔湾 vs 芝加哥）的原因与 Cloudflare 判定权重
* `references/FINGERPRINT_VS_EDGE.md` — 网络传输层防泄露 vs 硬件设备指纹对抗的边界与分工建议
