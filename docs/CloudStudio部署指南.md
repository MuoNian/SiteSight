# 鹭见 SiteSight · Cloud Studio 在线部署指南

> 目标：把「网页版 + AI 场地分析报告 + 官方演示」部署成公网可访问的在线演示站。
> 说明：云端演示版不做实时建模（OpenDroneMap 太重）；现场建模请用本地完整版。“加载官方演示 / 打开已有成果 + AI 报告 + 反馈记忆”在云端完整可用。

## 一、准备工作

1. 一个腾讯云 Cloud Studio 账号（用微信/QQ 登录即可）：https://cloudstudio.net
2. 代码仓库：https://github.com/MuoNian/SiteSight（公开，可直接导入）
3. 大模型 API Key（可选，配置后 AI 报告调用真实大模型；不配置则用内置模板）

## 二、创建云端工作空间（约 5 分钟）

1. 打开 Cloud Studio，点击「新建工作空间 / New Workspace」
2. 来源选择 **Git 仓库**，粘贴：
   ```
   https://github.com/MuoNian/SiteSight.git
   ```
3. 环境模板选择 **Python 3**（或默认 Ubuntu 环境）
4. 点击创建，等待环境就绪（首次 1–3 分钟）

## 三、配置大模型 API（可选但推荐）

在 Cloud Studio 左侧文件树打开 `app/config.example.json`，参考它新建 `app/config.json`，填入你的 Key：

```json
{
  "providers": [
    {
      "name": "我的供应商",
      "base_url": "https://api.qnaigc.com/v1",
      "api_key": "在这里填你的Key",
      "model": "z-ai/glm-5.2",
      "max_tokens": 8192
    }
  ]
}
```

> `app/config.json` 已被 `.gitignore` 排除，不会被提交到仓库。

## 四、启动服务（约 1 分钟）

在 Cloud Studio 内置终端里执行。**先看一眼仓库文件在哪里**：

```bash
ls
```

- 如果直接看到 `app/` 文件夹（仓库被检入工作区根目录，最常见）：执行
  ```bash
  cd app
  SITESIGHT_NO_BROWSER=1 python server.py
  ```
- 如果看到的是 `SiteSight/` 文件夹：执行
  ```bash
  cd SiteSight/app
  SITESIGHT_NO_BROWSER=1 python server.py
  ```

> 提示：如果 `python` 不可用，改用 `python3`；`SITESIGHT_NO_BROWSER=1` 是关闭自动打开浏览器（云端没有桌面）。

看到 `鹭见 SiteSight 已启动` 即成功。

## 五、打开公网访问

1. Cloud Studio 会自动检测运行中的端口，找到 **8765** 端口
2. 点击端口旁的「公网访问 / Public」或「预览」，Cloud Studio 会生成一个公网 URL（形如 `https://xxxx.cloudstudio.work`）
3. 把这个 URL 发给任何人即可访问

> 不同版本的 Cloud Studio 按钮位置略有差异，一般在「端口 Ports」面板；若没有公网按钮，使用「预览 Preview」也能得到临时演示链接。

## 六、演示路径（照这个走最顺）

1. 打开首页，点「**加载官方演示**」→ 自动加载内置真实成果（60 张照片场地）
2. 看 AI 场地分析报告（秒开，已缓存）
3. 在“告诉我你的偏好”里写“以后报告要突出坡度分析”→ 记住 → 重新生成 → 看到报告变化
4. 下载「处理报告 PDF」验证下载链路

## 七、常见问题

**Q：点“开始处理”报“当前环境未配置建模引擎”？**
A：正常。云端演示版不做现场建模；请用“加载官方演示 / 加载已有成果”，或在本地运行完整版。

**Q：AI 报告是模板版本？**
A：检查 `app/config.json` 是否创建、Key 是否正确；未配置时自动用内置模板（离线可用）。

**Q：如何上传自己的成果到云端？**
A：Cloud Studio 文件树支持拖拽上传。把整个成果文件夹拖进工作区，然后在网页“从已有成果开始”粘贴云端路径（形如 `/workspace/xxx/project_...`）。建议成果目录保留英文名。

**Q：公网链接能一直用吗？**
A：Cloud Studio 工作空间休眠或关闭后链接会失效，演示前先唤醒。正式提交如需长期在线，建议赛后再用云服务器 + 备案域名。

**Q：云端能跑真实建模吗？**
A：理论上可在云端装 Docker + ODM（需要较大磁盘和内存），但演示等待时间长、成本高。当前版本刻意把“演示体验”和“重计算”分开：云端负责展示与 AI，本地负责建模。

## 八、安全提示

- `app/config.json` 里有真实 API Key，只在 Cloud Studio 工作空间内使用，**不要上传到 GitHub**
- 公网链接任何拿到的人都能访问，演示期结束后及时关闭端口
- 若担心滥用，可在 Cloud Studio 里用「访问密码」功能保护页面
