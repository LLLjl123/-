# WebRTC 原理、泄露机制与防护深度解析

WebRTC（Web Real-Time Communication）是一项旨在实现浏览器间点对点（P2P）实时音视频与数据传输的技术。然而，在高风控跨境应用（如访问 Claude、OpenAI）时，WebRTC 是最容易导致用户真实地理位置暴露的元凶之一。

---

## 1. 为什么 WebRTC 会绕过系统代理？

传统的浏览器网络请求（HTTP/HTTPS/WebSocket）遵循系统的代理设置（如 WinINet、PAC 脚本或 SOCKS5 代理）。
然而，WebRTC 是为 **超低延迟媒体传输** 设计的，它采用 **ICE（Interactive Connectivity Establishment）** 框架来打通两台设备之间的连接：

1. **收集本地候选（Host Candidates）**：
   浏览器直接调用操作系统底层网卡 API，枚举当前设备连接的所有网卡 IP（例如家庭路由器的 `192.168.1.100`、Hyper-V 虚拟网卡的 `172.21.96.1`、TUN 虚拟网卡的 `198.18.0.1`）。
2. **STUN 协议探测公网候选（Server Reflexive Candidates - `srflx`）**：
   浏览器直接通过 UDP 协议向公网的 STUN 服务器（如 Google 的 `stun.l.google.com:19302` 或 Cloudflare 的 `stun.cloudflare.com:3478`）发送轻量探测包（Binding Request）。
   STUN 服务器收到 UDP 数据包后，在回包中告诉浏览器：“我看到的你的外网 IP 和端口是 X.X.X.X”。
   **问题所在**：由于这个 UDP 请求通常不走普通的 HTTP/SOCKS 代理隧道，如果代理软件或节点不支持 UDP 转发，这个数据包就会**直接从你本机的物理宽带网卡发出去**，从而把国内运营商的真实 IP（如 `111.26.x.x`）暴露在 SDP 会话中！

---

## 2. 区分两种泄露：公网 IP 泄露 vs 局域网私网 IP 暴露

在使用第三方检测工具（如 `browserleaks.com/webrtc`）时，必须正确区分两类警告：

| 提示类型 | 示例数据 | 风险等级 | 是否会导致封号 | 解释 |
| :--- | :--- | :--- | :--- | :--- |
| **Public IP Leak** (公网 IP 泄露) | `111.26.x.x` (中国移动) | 🔴 **致命** | **是** | 网站直接拿到了你的国内真实地理位置，代理彻底失效。 |
| **Local IP Exposed** (局域网内网 IP) | `192.168.1.100`, `172.21.96.1` | 🟡 **无害** | **否** | 这是 RFC 1918 私网保留地址，全世界数亿家庭都在用，不可在公网路由，不含任何地理位置。 |

> [!NOTE]
> 只要检测网站显示 **`✓ No Public IP Leak`** 且 **`Public IP Address: -`**（或者等于你的代理出口 IP），就代表没有任何公网地理位置泄露，环境是安全的！

---

## 3. 为什么 Edge / Chrome 会暴露局域网 IP（mDNS 与媒体权限的关系）

在现代 Chromium 内核中，Google 引入了 **mDNS（多播 DNS）混淆机制**：
* 默认情况下，浏览器会将 `192.168.1.100` 替换为一个随机 UUID，例如：`e53b497f-1d42-498c-8594-5d9b626d7b5b.local`。
* **但是**，根据 W3C WebRTC 规范：**一旦用户给某个网站授权了“麦克风”或“摄像头”权限**（例如在 BrowserLeaks 上永久授权了麦克风），浏览器就会判定“用户正在进行实时音视频通话”。为了确保通话质量和最低延迟，浏览器会**主动关闭 mDNS 混淆**，列出本机网卡的局域网真实 IP 进行 P2P 直连。
* **解决办法**：收回该站点的麦克风/摄像头权限，刷新页面后 mDNS 即刻恢复。

---

## 4. 最佳加固方案对比

### 方案 A：指纹浏览器（EasyBR / AdsPower 等）—— 拔掉插头法
* **原理**：直接将 WebRTC 选项设为 **`禁用 (Disabled)`**。
* **效果**：浏览器内核根本不提供 `RTCPeerConnection` API，任何网页无法调用 WebRTC，**0 泄露，100% 绝对安全**。

### 方案 B：主流浏览器（Microsoft Edge / Google Chrome）—— 策略锁定法
* **原理**：配置 Chromium 官方企业级策略：
  ```json
  "webrtc": {
      "ip_handling_policy": "disable_non_proxied_udp"
  }
  ```
  并附加启动参数：
  ```cmd
  --force-webrtc-ip-handling-policy=disable_non_proxied_udp
  ```
* **效果**：WebRTC 将被严格禁止使用任何非代理接口发送 UDP。如果无法通过代理建立 TURN 中继，WebRTC 连接将直接放弃，绝不会裸连物理网卡。
