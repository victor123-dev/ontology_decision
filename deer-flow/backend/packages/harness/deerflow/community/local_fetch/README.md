# Local Web Fetch - 完全本地的网页抓取工具

## 概述

这是一个**完全本地化**的 web_fetch 实现，**不需要任何外部 API Key**。

## 工作原理

```
HTTP 请求 → 获取 HTML → Readability 提取 → Markdown 转换 → 返回结果
   ↓            ↓            ↓              ↓            ↓
 httpx      完整网页     主要内容提取    markdownify    AI 可读格式
```

## 核心特性

✅ **零 API 依赖** - 不需要任何外部服务或 API Key  
✅ **完全本地处理** - 所有内容提取都在本地完成  
✅ **智能内容提取** - 使用 Readability 去除广告和导航  
✅ **自动编码检测** - 正确处理各种字符编码  
✅ **重定向支持** - 自动处理页面重定向（最多 5 次）  
✅ **可配置超时** - 默认 15 秒超时  
✅ **浏览器级 Headers** - 模拟真实浏览器请求  

## 与其他提供商对比

| 特性 | Local Fetch | Jina AI | Firecrawl |
|------|-------------|---------|-----------|
| API Key 需求 | ❌ 不需要 | ❌ 不需要（免费额度） | ✅ 需要 |
| 处理位置 | 本地 | 远程 API | 远程 API |
| 速度 | ⚡ 快（无网络延迟） | 🐢 中等 | 🐢 中等 |
| 反爬虫能力 | ⚠️ 基础 | ✅ 中等 | ✅ 强 |
| JS 渲染支持 | ❌ 不支持 | ❌ 不支持 | ✅ 支持 |
| 适用场景 | 静态/半动态页面 | 通用场景 | 复杂/反爬网站 |

## 配置方法

### 1. 在配置文件中启用

编辑您的配置文件（如 `config.yaml`），设置 web_fetch 提供商：

```yaml
tools:
  web_fetch:
    use: "deerflow.community.local_fetch.tools:web_fetch_tool"
    timeout: 15          # 请求超时时间（秒）
    max_chars: 4096      # 返回内容最大字符数
    user_agent: ""       # 可选：自定义 User-Agent
```

### 2. 使用配置向导

运行配置向导时选择 "Local Fetch"：

```bash
cd deer-flow
openclaw configure --section web
# 或在 deer-flow 的配置流程中选择 Local Fetch
```

## 技术实现

### 核心流程

1. **HTTP 请求** (`_fetch_html`)
   - 使用 httpx.AsyncClient 发送 GET 请求
   - 模拟浏览器 Headers
   - 自动处理重定向
   - 智能编码检测

2. **内容提取** (`ReadabilityExtractor`)
   - 优先使用 Readability.js（需要 Node.js）
   - 失败时回退到纯 Python 提取
   - 去除导航、广告、侧边栏等噪音

3. **格式转换** (`Article.to_markdown`)
   - 使用 markdownify 将 HTML 转为 Markdown
   - 保留标题和主要内容
   - 处理图片链接

### 代码示例

```python
# 工具调用示例
from deerflow.community.local_fetch.tools import web_fetch_tool

# 异步调用
result = await web_fetch_tool("https://example.com/article")
print(result)  # 输出 Markdown 格式的内容
```

## 使用场景

### ✅ 适合的场景

- 技术文档抓取
- 博客文章提取
- 新闻内容获取
- 静态网页内容提取
- 需要频繁调用（无 API 限制）
- 隐私敏感场景（数据不离开本地）

### ⚠️ 不适合的场景

- 需要 JavaScript 渲染的动态页面
- 有强反爬虫机制的网站
- 需要登录才能访问的内容
- 重度依赖 AJAX 加载的内容

## 局限性

1. **不支持 JS 渲染**
   - 无法处理纯 JavaScript 渲染的内容
   - 对于这类网站，建议使用 Firecrawl 或 Browser 工具

2. **基础反爬虫**
   - 只使用标准的浏览器 Headers
   - 遇到强反爬机制可能会失败
   - 可以自定义 User-Agent 提高成功率

3. **编码问题**
   - 虽然能自动检测编码，但少数网站可能仍有乱码

## 优化建议

### 提高成功率

```yaml
tools:
  web_fetch:
    use: "deerflow.community.local_fetch.tools:web_fetch_tool"
    timeout: 20  # 增加超时时间
    user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ..."  # 使用真实浏览器 UA
```

### 处理失败情况

如果 Local Fetch 失败，可以：
1. 切换到 Jina AI（有一定的反爬能力）
2. 使用 Firecrawl（强反爬支持）
3. 使用 Browser 工具（完整浏览器渲染）

## 性能指标

- **响应时间**: 通常 1-5 秒（取决于目标网站）
- **内容提取**: < 1 秒（本地处理）
- **内存占用**: < 50MB
- **并发支持**: 受限于 httpx 异步客户端

## 故障排查

### 常见问题

**Q: 返回内容为空？**
A: 检查网页是否需要 JS 渲染，或是否被反爬机制阻止。

**Q: 返回乱码？**
A: 尝试设置 `user_agent` 或增加 `timeout`。

**Q: 403 Forbidden 错误？**
A: 网站有反爬机制，建议使用 Firecrawl 或 Browser 工具。

### 日志查看

```bash
# 查看详细日志
tail -f logs/app.log | grep "Local web fetch"
```

## 依赖项

```
httpx>=0.24.0          # HTTP 客户端
readabilipy>=0.2.0     # Readability 提取
markdownify>=0.11.0    # HTML 转 Markdown
langchain-tools        # LangChain 工具框架
```

这些依赖在 deer-flow 项目中已经包含，无需额外安装。

## 总结

Local Fetch 是一个**完全免费、无需 API Key、完全本地处理**的网页抓取方案，非常适合：
- 快速原型开发
- 静态内容抓取
- 高频调用场景
- 隐私敏感应用

对于更复杂的场景，可以与其他提供商（Jina AI、Firecrawl）配合使用。
