# 中文医疗 LangChain / LangGraph RAG 系统

本项目是一个面向中文医疗问答的完整学习项目，覆盖数据拉取、数据标准化、百万级关键词索引、全量语义向量索引、混合召回、医疗精排、人群过滤、证据约束生成和生成后安全校验。

## 当前技术栈：LangChain v1 生态

2026-09-08 本地迁移验证版本：LangChain **1.4.0**、langchain-core **1.6.2**、langchain-openai **1.6.0**、LangGraph **1.2.11**。具体依赖固定在 `backend/requirements-langchain.txt`；这些是本次安装解析到的稳定版本，后续更新应重新验证后再改版本。

| 原实现 | 当前实现 | 业务作用 |
|---|---|---|
| 单个 Python 方法串联问诊 | LangGraph `StateGraph` + 请求级 `TypedDict` | 显式节点、急症条件分支、最终校验 |
| 两套 urllib 模型客户端 | LangChain `init_chat_model` → `ChatOpenAI` | 统一文本、报告图片转录及兼容服务配置 |
| 手工拼装模型消息 | `SystemMessage` / `HumanMessage` + `ChatPromptTemplate` | LCEL 提示词与模型组合，保留多模态内容块 |
| 直接调用索引对象 | 自定义 `BaseRetriever` → 标准 `Document` | 复用本地 BM25 / FAISS，保留来源、权限与分数 |
| 直接调用医疗精排 | `RunnableLambda` 封装医疗 Reranker | 可组合的精排步骤，复用现有隔离模型进程 |
| 报告接口内部串联检索与生成 | 报告 LangGraph：retrieve → interpret | 提取后资料进入统一工作流 |

### 问诊图的实际执行顺序

```mermaid
flowchart TD
    START --> privacy[隐私脱敏]
    privacy --> triage[急症规则]
    triage -->|命中| emergency[返回急症提示]
    emergency --> END
    triage -->|未命中| structure[症状与人体图谱上下文]
    structure --> retrieve[LangChain BM25 / FAISS Retriever]
    retrieve --> fusion[RRF 去重混排]
    fusion --> rerank[Runnable 医疗精排]
    rerank --> filter[年龄 / 孕期 / 地区 / 版本过滤]
    filter --> generate[Prompt + ChatOpenAI]
    generate --> validate[引用 / 权限 / 数字校验]
    validate --> respond[成功或拒绝响应]
    respond --> END
```

节点在 `backend/app/pipeline.py`，状态定义在 `backend/app/graph_state.py`。`consult()` 现在调用已编译的图；没有隐藏的旧流程分支。图编译只建立执行关系，不训练模型。

检索节点内顺序调用两个独立 Retriever，保持当前 SQLite/模型进程的资源使用方式；“独立召回”不代表并行执行。RRF 与过滤仍用原有领域规则。医疗流程的步骤和分支已知，采用确定性图编排；本次未加入自主工具选择 Agent、多轮记忆或持久化 checkpoint。

### 已有项目如何升级

在项目根目录执行：

```bash
.venv-full/bin/python -m pip install -r backend/requirements.txt
pnpm dev:server
```

先停止旧后端再启动新版本。当前工作环境已安装迁移依赖；其他机器或重新创建的虚拟环境需要执行安装命令。已有前端接口、`knowledge.db`、`medical.faiss`、索引清单及模型缓存可以直接复用，**无需重新下载语料、训练 IVF-PQ 或重算 Embedding**。

保留原有 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`LLM_VISION_MODEL`。新增配置：

```dotenv
# 默认兼容供应商：用提示词约定 JSON，并在本地严格验证完整性。
LLM_STRUCTURED_METHOD=prompt
# 供应商明确支持 JSON 模式时可改为 json_mode。
# 此时使用 ChatOpenAI.with_structured_output(method="json_mode", include_raw=True)。
```

完整 `/chat/completions` 地址会规范化为 SDK 根地址；`enable_thinking` 使用 `extra_body` 传递；固定使用 Chat Completions 协议。JSON 模式只保证语法层面的结构，不代表医学正确。无论模式如何，长度截断、拒绝响应、非法 JSON 都会被拒绝，再按原业务路径回退或报错，不静默切换模型或重试付费请求。

### 索引、追踪与验证边界

- 自定义 Retriever 适配现有 `IndexIDMap2(IndexIVFPQ)` 和 SQLite rowid，没有迁移到 LangChain 默认内存 docstore，也不加载 pickle 索引。
- Transformers / PyTorch 的医疗模型、规范化编码规则和 macOS 子进程隔离保留；迁移框架不会自动提升知识库权威性或召回准确率。
- 问诊图、报告图和共享模型入口禁用 LangSmith 云端追踪，环境中设置追踪开关也不会自动上传这些请求。仍保留原有本地脱敏输入及检索日志；新模型日志只记录请求标识、阶段、模型和结束原因。
- 没有开启用户病历持久化和对话记忆。上传文件的接收及提取仍在图之前完成，原始图片字节不进入图状态；上传框架可能使用临时文件，不能据此宣称全流程绝对不落盘。
- 报告解释沿用已有业务约束与字段校验，尚不具备临床验证的影像诊断能力，也未新增与问诊完全相同的生成后医疗校验器。
- 本次运行 22 项离线局部测试，使用模拟 HTTP 验证真实 LangChain SDK，未发送真实报告或调用付费模型；未启动应用或执行前端构建。

局部回归命令：

```bash
cd backend
../.venv-full/bin/python -m unittest tests.test_langchain_migration tests.test_pipeline -v
```

官方接口依据：[LangChain v1 迁移指南](https://docs.langchain.com/oss/python/migrate/langchain-v1)、[LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)、[ChatOpenAI 集成](https://docs.langchain.com/oss/python/integrations/chat/openai)。

## 自由对话：直接 LLM + 短期记忆

新增独立菜单 **07 / 自由对话**。该入口与智能问诊、报告解读分开，不调用 BM25、FAISS、Reranker，也不自动读取其他页面的资料或生成检索引用。

技术路径：前端本轮文本 → 独立会话接口 → LangGraph `StateGraph` → LangChain `ChatPromptTemplate` / `MessagesPlaceholder` → `init_chat_model` / `ChatOpenAI` → 纯文本回答 → `InMemorySaver` 内存检查点。

这里没有检索工具或 Agent 工具循环，也不使用已被本项目安装版本标记为弃用的 `ConversationBufferMemory` / `RunnableWithMessageHistory`。每个随机会话对应独立的 `thread_id`，短期记忆通过 LangGraph 检查点读写。接口依据：[LangGraph 短期记忆与检查点](https://docs.langchain.com/oss/python/langgraph/add-memory)。

### 使用方式与记忆边界

- 复用 `backend/.env` 中现有 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`LLM_TIMEOUT_SECONDS`、`LLM_MAX_OUTPUT_TOKENS`、`LLM_ENABLE_THINKING`，不需要新密钥、额外依赖或重建向量索引。此入口返回文本，不受 `LLM_STRUCTURED_METHOD` JSON 模式控制。
- 点击“自由对话”，输入第一条消息时才创建会话。可先发送“我正在学习 Python”，再问“我刚才在学什么？”来检查连续上下文。
- 后端只保留最近 **12 轮完整问答**，同时限制历史正文总量为 **24,000 字符**。当前输入最多 4,000 字符；超限从最早问答对开始移除，不会留下孤立的助手消息。字符上限不是模型精确 Token 上限，长回答仍受供应商上下文和输出限制。
- 闲置 **30 分钟**过期，过期检查在访问时执行，后台每分钟清理内存。上限 **128 个会话**，满额拒绝新建，不挤掉其他人的历史。相关常量位于 `backend/app/services/free_chat.py`。
- 页面切换保留当前对话；刷新或关闭页面后没有历史恢复功能。浏览器不使用 localStorage/sessionStorage 保存正文或凭据；服务端重启后记忆丢失。刷新前的遗留会话会按闲置期限清理。
- 页面显示最近 40 轮记录，**可见旧消息不代表仍在模型上下文中**。页头展示当前模型和实际保留的记忆轮数。
- “清空对话与记忆”需要确认，会清除服务端检查点及最近一次重试缓存，再清空界面。会话已过期时，界面明确提示开始新对话，不静默假装模型仍记得旧内容。
- 同一会话有进行中的请求时，拒绝并发发送和清空。失败不提交输入、回答或裁剪后的历史；重试当前最后一次请求使用相同 `request_id`，避免重复追加成功的回答。
- 每轮在请求局部 `InMemorySaver` 中执行图，完整成功后才替换会话检查点。旧检查点版本随之释放，防止裁剪了消息却仍无限保留早期完整快照。

### 新增接口

| 接口 | 请求正文 | 作用 |
|---|---|---|
| `POST /api/chat/sessions` | `{}` | 创建不可预测的随机会话凭据，返回模型与记忆策略 |
| `POST /api/chat/messages` | `session_id`、`message`、UUID 格式的 `request_id` | 发送当前一条消息，历史只从服务端检查点读取 |
| `POST /api/chat/clear` | `session_id` | 真正清空该会话的服务端记忆与重试缓存 |

模型未配置返回 503；未知或过期会话返回 410；同会话忙碌返回 409；上游超时返回 504。模型失败不会以空回答或证据模板伪装成功。

### 安全与部署说明

自由对话明确显示 **RAG 未启用**，不执行智能问诊的急症规则或引用校验；系统提示只提供基本行为约束，并不是医疗安全校验保障。涉及健康的问题不能据此自行诊断、开药或改剂量。

当前会话输入和有限历史会发给你配置的模型服务商，供应商的数据留存遵循其自身政策。本地不记录聊天正文或会话凭据，也不自动上传到 LangSmith；界面通过 Vue 文本插值展示回答，不把模型 HTML 作为代码执行。

这是**单进程短期记忆**：多 worker / 多实例不能共享会话，须先接入共享存储和账号鉴权再扩展。随机会话凭据是访问能力凭据，不等于登录认证，请勿分享；公开部署前仍需在网关或应用层加身份认证、速率限制和用户配额。不要直接将匿名付费模型接口暴露到公网。

局部离线验证（不启动服务，不请求真实模型）：

```bash
cd backend
../.venv-full/bin/python -m unittest tests.test_free_chat tests.test_langchain_migration -v
```

项目当前已经完成以下全量索引：

| 产物 | 当前规模 | 用途 |
|---|---:|---|
| Huatuo 知识图谱问答 | 796,444 条 | 疾病、症状、药物关系及基础问答召回 |
| Huatuo 医疗百科问答 | 362,420 条 | 疾病与症状基础知识召回 |
| 本地安全示例 | 10 条 | 急症、安全边界和策略演示 |
| SQLite 文档与 BM25 索引 | 1,158,874 条 | 保存原文并执行全量关键词召回 |
| FAISS 医疗向量索引 | 1,158,874 条 | 执行全量中文语义召回 |

> 本系统用于技术学习和医疗信息辅助检索，不提供诊断、处方或个体化治疗建议，不能替代医生，也不能直接作为医疗器械使用。

## 1. 为什么要使用这套架构

医疗问答不能只依赖大模型自身记忆，也不能把历史问诊答案直接当作当前治疗标准。本项目把职责拆开：

- 规则负责隐私处理和急症优先阻断；
- BM25 负责精确关键词、药名和医学名词匹配；
- Embedding + FAISS 负责口语表达与规范医学表达之间的语义匹配；
- RRF 合并两种不同检索方式，避免直接比较不可比的分数；
- Cross-Encoder Reranker 阅读查询和候选全文，进行第二次相关性判断；
- 人群过滤器检查年龄、孕期、地区和指南版本；
- 生成器只能使用最终候选证据；
- 校验器阻止无引用、无权限治疗、可疑剂量、证据外数字和确定性诊断。

项目不在检索逻辑里维护类似 `QUERY_EXPANSIONS` 的问题级同义词硬编码。安全规则、急症规则和治疗意图规则仍然使用显式规则，因为它们需要稳定、可审计、优先于模型执行。

## 2. 整体业务流程

### 2.0 产品工作台

前端已重构为医疗科研智能工作台，六个一级菜单分别承担不同职责：

| 工作区 | 用户目标 | 是否调用 LLM |
|---|---|---|
| 智能问诊 | 输入症状与人群信息，获得带引用的安全辅助回答 | 证据通过过滤后调用 |
| 健康可视化 | 从人体系统和器官理解功能与症状观察线索 | 否 |
| 报告解读 | 上传病历、检验单或报告截图，获得分层释义和就医问题 | 调用，图片另需视觉模型 |
| 证据检索 | 查看 BM25、FAISS、RRF、Reranker 的真实候选和分数 | 否 |
| 知识资产 | 查看来源、可信等级、索引规模与生成权限 | 否 |
| 运行监测 | 查看索引、精排、生成模型和安全门状态 | 否 |

健康可视化是医学科普与检索导航，不接入可穿戴设备、不展示虚构个体指标，也不构成诊断。研究检索与智能问诊分离，便于独立判断召回或精排质量。

界面背景使用 Canvas 绘制抽象生命信号、细胞数据粒子、DNA 双螺旋、科研网格和数据读数。动画不代表用户真实健康指标，会随工作区切换配色；浏览器标签页进入后台时自动暂停，并尊重操作系统的“减少动态效果”偏好。

### 2.0.1 病历与检查报告解读

“报告解读”不是自动影像诊断。首版支持文字型 PDF、TXT、Markdown，以及 PNG、JPG、WebP 格式的清晰报告截图；DICOM、CT/MRI 完整序列和动态超声视频必须由专业影像工作站与合格医生处理。

```mermaid
flowchart LR
    A["选择资料类型"] --> B["遮盖身份信息并单独授权"]
    B --> C["文件头、格式和大小校验"]
    C -->|PDF/文本| D["本地提取文字"]
    C -->|报告图片| E["视觉模型只转录可见文字"]
    D --> F["常见身份字段脱敏"]
    E --> F
    F --> G["BM25 + FAISS + RRF + Reranker"]
    G --> H["LLM 结构化释义"]
    H --> I["关键发现、风险提示、问医生问题与限制"]
```

产品边界：

- 报告原文、通俗解释和模型不确定性分开展示；
- 症状描述为选填，只提供上下文，不得覆盖或篡改报告结论；
- 图片识别不到文字时直接失败，不依据单张原始影像猜测诊断；
- 不生成处方、剂量、停药或替代医生的治疗决定；
- 业务代码不主动持久保存报告，上传框架可能使用临时文件；模型日志不记录文件正文；
- 图片中的姓名、条码和二维码无法在发送给视觉模型前可靠自动遮盖，用户必须先手动处理。

人体系统图谱使用 Three.js、GLTFLoader 和本地 Draco 解码器渲染真实分层 GLB 解剖模型，支持拖拽旋转、滚轮缩放、器官拾取、系统高亮和相机复位。模型共包含外形、循环、消化、神经、泌尿、呼吸和骨骼七层；WebGL 初始化或模型加载失败时，会自动回退到二维人体图。Three.js 场景按需加载，不会进入普通问诊页面的首屏代码。

男性人体模型来自 Z-Anatomy，并派生自 BodyParts3D/DBCLS，模型文件按 CC BY-SA 4.0 保留署名和相同方式共享。模型的完整许可和来源说明位于 `frontend/public/anatomy/LICENSE` 与 `frontend/public/anatomy/NOTICE`。许可证仅约束这些第三方模型资产，不改变本项目其他代码的许可边界。

```mermaid
flowchart TD
    A["用户输入症状和基本信息"] --> B["手机号、身份证、邮箱和地址脱敏"]
    B --> C["急症危险信号规则"]
    C -->|命中危险信号| D["立即就医提示"]
    D --> E["停止检索、生成和自动治疗建议"]
    C -->|未命中| F["症状结构化与缺失信息追问"]
    F --> G["SQLite FTS5 / BM25 全量关键词召回"]
    F --> H["医疗 Embedding / FAISS 全量语义召回"]
    G --> I["按文档 ID 执行 RRF 去重混排"]
    H --> I
    I --> J["BGE Cross-Encoder 医疗精排"]
    J --> K["年龄、孕期、地区和指南版本过滤"]
    K --> L["选取最终证据"]
    L --> M["证据模板或可选大模型生成结构化答案"]
    M --> N["引用、诊断、治疗权限、剂量和数字校验"]
    N -->|失败或没有证据| O["拒绝判断并建议补充信息或就医"]
    N -->|通过| P["返回带来源的辅助信息"]
```

### 2.1 急症为什么必须在检索之前

如果用户描述严重呼吸困难、疑似卒中、胸痛伴危险表现、大量出血、意识障碍、严重过敏、自伤风险，或者三月龄以下婴儿发热等情况，系统应优先提示急救，而不是先检索“可能是什么病”。

急症规则位于 `backend/app/services/triage.py`，命中后主流程立即返回，不运行 BM25、FAISS、Reranker 和生成器。

### 2.2 结构化和追问的作用

系统会从用户输入中整理症状、身体部位、持续时间、体温、年龄、性别、孕期和地区，并根据缺失信息最多生成四个追问。

当前检索仍然使用脱敏后的原始描述，不会把人工维护的同义词偷偷加入查询。结构化结果主要用于前端解释、人群过滤和后续扩展。

## 3. 离线数据处理流程

离线流程只在准备数据、更新数据或更换 Embedding 模型时运行。完成后，日常查询直接使用已经生成的 SQLite 和 FAISS 文件。

```mermaid
flowchart LR
    A["Huatuo 远端 JSONL"] --> B["流式拉取与字段标准化"]
    B --> C["分片 JSONL.GZ"]
    C --> D["SQLite documents 表"]
    C --> E["SQLite FTS5 倒排索引"]
    D --> F["按资料类型生成向量文本"]
    F --> G["医疗 Embedding 生成 1024 维向量"]
    G --> H["10万样本训练 IVF-PQ"]
    H --> I["115万条向量分区、压缩并写入 FAISS"]
    D --> J["稳定 rowid"]
    J --> I
```

### 3.1 原始数据标准化

拉取脚本把不同上游字段统一成以下结构：

```json
{
  "id": "huatuo-encyclopedia-135902",
  "title": "饿了就胃痛怎么办",
  "question": "饿了就胃痛怎么办",
  "content": "完整回答正文",
  "source": "huatuo_encyclopedia_qa",
  "source_url": "数据来源地址",
  "source_type": "medical_qa",
  "trust_level": "secondary",
  "allow_treatment_generation": false,
  "regions": ["CN"],
  "retrieval_only": true
}
```

Huatuo 数据默认标记为：

- `trust_level=secondary`：二级参考资料；
- `retrieval_only=true`：允许参与检索；
- `allow_treatment_generation=false`：不能单独授权生成治疗方案、药品剂量或处方。

### 3.2 为什么使用 JSONL.GZ

- JSONL 每行是一条独立 JSON，可以流式读取；
- 某一行损坏时更容易定位，不必把百万条记录解析为一个巨大数组；
- Gzip 能显著减少磁盘占用；
- Python 可以直接使用 `gzip.open(..., "rt")` 读取，不需要先解压；
- 分片后可以断点下载、单独重跑或并行处理。

原始分片位于：

```text
backend/data/raw/*.jsonl.gz
backend/data/raw/manifest.json
```

### 3.3 SQLite 与 BM25 如何构建

`build_search_index.py` 会：

1. 流式读取普通 JSONL 和 `.jsonl.gz`；
2. 清理问题和回答字段；
3. 把原始资料写入 SQLite `documents` 表；
4. 对 `title + question + keywords` 生成中文单字、双字和英文数字词元；
5. 把词元写入 SQLite FTS5 虚拟表；
6. 使用同一个连续 `rowid` 关联文档表、BM25 和后续 FAISS；
7. 完成后把 `metadata.status` 更新为 `complete` 并原子发布文件。

SQLite 的主要字段：

| 字段 | 含义 |
|---|---|
| `rowid` | SQLite 和 FAISS 共用的稳定数字 ID |
| `document_id` | 数据源级稳定字符串 ID |
| `title` | 标题 |
| `question` | 用户问题或章节问题 |
| `content` | 完整回答或证据正文 |
| `source` / `source_url` | 来源名称和地址 |
| `source_type` | `medical_qa`、指南、说明书、规则等资料类型 |
| `trust_level` | 资料可信等级 |
| `allow_treatment_generation` | 是否允许参与治疗内容生成 |
| `regions` | 适用地区 |
| `minimum_age` / `maximum_age` | 适用年龄范围 |
| `pregnancy_allowed` | 是否适用于孕期 |
| `guideline_version` | 指南版本或年份 |
| `retrieval_only` | 是否仅允许检索参考 |
| `keywords` / `cautions` | 关键词和注意事项 |

## 4. 全量向量与 FAISS 流程

### 4.1 什么是 Embedding

Embedding 模型把文本转换成固定长度的数字向量。本项目默认模型输出 1024 维归一化向量。语义相近的问题在向量空间中通常距离更近，例如：

```text
饿了就肚子痛
空腹时胃痛怎么办
饥饿时上腹部疼痛
```

它们用词不完全相同，但 FAISS 仍可能把它们互相召回。

### 4.2 向量文本规则

当前规则版本是：

```text
source-aware-question-first-v1
```

不同资料使用不同向量文本：

| 资料类型 | 参与向量编码的内容 | 原因 |
|---|---|---|
| 医疗问答、问诊对话 | `question + title + keywords` | 让用户口语问题直接匹配资料问题，避免长回答稀释语义 |
| 指南、说明书、安全规则等证据文档 | `title + question + keywords + content_excerpt` | 非问答资料需要正文片段表达章节含义 |

完整回答不会丢失，仍然保存在 `knowledge.db`。FAISS 命中后通过 `rowid` 回到 SQLite 读取完整问题、回答、来源和人群条件。

### 4.3 什么是 FAISS

FAISS 是向量相似度索引，不是数据库、医疗数据或大模型。它负责从 1,158,874 个向量中快速找出与用户查询最接近的候选 ID。

当前索引结构：

```text
IndexIDMap2(IndexIVFPQ)
```

参数含义：

| 参数 | 当前值 | 作用 |
|---|---:|---|
| `dimension` | 1024 | Embedding 输出维度 |
| `nlist` | 2048 | IVF 聚类分区数量 |
| `nprobe` | 32 | 查询时探测的分区数量 |
| `pq_m` | 64 | 把向量拆为 64 个子空间压缩 |
| `pq_bits` | 8 | 每个子空间使用 8 bit 编码 |
| `code_size` | 64 字节/条 | 每条向量的 PQ 压缩码大小 |

如果保存全部原始 `float32` 向量，115万条1024维向量约需 4.7GB。当前 `medical.faiss` 经过 IVF-PQ 压缩后约 97MB。

### 4.4 为什么先训练10万条，再编码115万条

FAISS 建库分为两个阶段：

1. 从全量数据均匀采样100,000条，生成向量并训练2048个 IVF 分区和 PQ 压缩码本；
2. 对全部1,158,874条记录生成向量，确定分区，压缩后写入 FAISS，并绑定 SQLite `rowid`。

第一阶段只是学习“怎样分区和压缩”，第二阶段才是真正把全部资料写入索引。

## 5. 在线查询技术流程

```mermaid
sequenceDiagram
    participant U as 用户/前端
    participant API as FastAPI
    participant S as 安全规则
    participant B as SQLite BM25
    participant V as Embedding + FAISS
    participant R as RRF + Reranker
    participant G as 过滤/生成/校验

    U->>API: 症状、年龄、性别、孕期、地区等
    API->>S: 隐私脱敏
    S->>S: 急症危险信号检查
    alt 命中危险信号
        S-->>U: 立即就医并停止后续处理
    else 未命中
        API->>B: 全量关键词召回 Top 100
        API->>V: 查询向量化并全量语义召回 Top 100
        B-->>R: 文档及 BM25 排名
        V-->>R: rowid 及向量相似度
        R->>B: 根据 rowid 回表读取完整文档
        R->>R: RRF 去重并保留 Top 40
        R->>R: Cross-Encoder 精排
        R->>G: 人群过滤并保留最终 Top 4
        G->>G: 将最终证据发送给已配置 LLM，失败时回退证据模板
        G->>G: 引用、诊断、剂量和数字校验
        G-->>U: 结构化答案、引用、追问和流程轨迹
    end
```

### 5.1 BM25 独立召回

BM25 在全部 SQLite FTS5 文档上搜索，不依赖 FAISS 的候选集。它擅长：

- 药品名、疾病名、检查名等精确词；
- 用户问题和文档问题存在相同中文片段；
- 数字、英文缩写和特定医学术语。

默认召回 `BM25_TOP_K=100` 条。

### 5.2 FAISS 独立召回

用户查询先由与建库相同的医疗 Embedding 模型生成1024维归一化向量，再使用内积近似余弦相似度搜索全部 FAISS 索引。

FAISS 不是在 BM25 的100条结果中再次排序，而是在115万条向量上独立搜索，默认召回 `VECTOR_TOP_K=100` 条。

### 5.3 RRF 混合排序

BM25 分数与向量相似度的数值范围不同，不能直接相加。RRF 只使用每一路的排名：

```text
RRF(d) = 1 / (60 + rank_bm25) + 1 / (60 + rank_faiss)
```

同一文档同时被两路召回时会得到两次排名贡献，因此通常排得更靠前。系统按 `document_id` 去重，默认保留 `RRF_TOP_K=40` 条。

### 5.4 医疗 Reranker 精排

默认使用 `BAAI/bge-reranker-v2-m3` Cross-Encoder，把以下内容作为一对联合编码：

```text
用户查询
+
候选标题 + 问题 + 完整回答 + 关键词
```

Cross-Encoder 能看到查询和候选之间的细粒度交互，通常比只比较两个独立向量更精确。模型分数之后还会叠加可审计的来源可信度和治疗权限策略。

Reranker 只处理 RRF 的少量候选，不会在每次查询时读取全部115万条。

### 5.5 人群和版本过滤

精排后依次检查：

- 用户年龄是否处于资料允许范围；
- 孕期用户是否命中明确禁用资料；
- 用户地区是否与资料地区或 `GLOBAL` 匹配；
- 指南版本是否超过十年或无法解析。

当前 Huatuo 问答多数没有完整年龄、孕期和指南版本元数据，因此相关过滤逻辑已经实现，但只有未来接入结构化指南和说明书后才能充分发挥作用。

### 5.6 生成和校验

如果配置了 OpenAI 兼容接口，生成器要求模型：

- 只能使用提供的证据；
- 每项医学陈述带 `[S数字]` 引用；
- 不补充证据中没有的药名、剂量或诊断；
- 返回固定 JSON 结构。

未配置外部大模型或调用失败时，系统会使用完全可追溯的证据模板，不会伪装成大模型生成成功。

生成后校验包括：

- 引用标记是否存在、是否引用未知资料；
- 是否出现确定性诊断表达；
- 治疗请求是否有 `allow_treatment_generation=true` 的证据；
- 剂量是否获得高可信说明书授权；
- 输出数字是否能在候选证据中找到。

没有最终证据或任何阻断校验失败时，系统拒绝继续判断并返回原因。

## 6. 技术组件与职责

| 层级 | 技术 | 职责 |
|---|---|---|
| 前端 | Vue 3、TypeScript、TSX、Vite | 咨询表单、检索流程轨迹、证据和结果展示 |
| API | FastAPI、Pydantic | 参数校验、接口、生命周期和 CORS |
| 流程编排 | LangGraph StateGraph | 请求状态、条件分支、独立处理节点 |
| 检索协议 | LangChain BaseRetriever / Document | 统一源文档与检索调用 |
| 原文存储 | SQLite | 保存115万条问题、回答、来源和安全元数据 |
| 关键词检索 | SQLite FTS5、BM25 | 全量精确召回 |
| 文本向量化 | Transformers、PyTorch、医疗 BGE | 生成1024维归一化稠密向量 |
| 向量检索 | FAISS IVF-PQ | 全量语义召回与压缩索引 |
| 混排 | RRF | 合并两个不可直接比较的排名 |
| 精排 | RunnableLambda + BGE Reranker Cross-Encoder | 对有限候选执行深度相关性判断 |
| 生成 | LangChain ChatOpenAI、ChatPromptTemplate、证据模板 | 文本及多模态模型调用，生成带固定引用的结构化回答 |
| 安全 | 显式规则与校验器 | 急症阻断、人群过滤、治疗权限和幻觉检查 |

### 6.1 macOS 模型进程隔离

Apple Silicon 上，PyTorch/MPS 和 FAISS 可能加载不同 OpenMP 运行时。项目没有设置 `KMP_DUPLICATE_LIB_OK` 绕过冲突，而是：

- 主进程加载 SQLite 和 FAISS；
- Embedding 在独立 `spawn` 子进程中运行；
- Reranker 在另一个独立 `spawn` 子进程中运行；
- 通过进程管道传递查询、候选和向量结果。

MPS 使用 Mac 统一内存。建库时模型权重、推理中间数据和系统内存共享，因此批大小越大，内存压力越高。

## 7. 目录和文件说明

```text
medical-rag-demo/
├── backend/
│   ├── app/
│   │   ├── main.py                       FastAPI 入口
│   │   ├── config.py                     环境变量配置
│   │   ├── models.py                     API 和检索数据模型
│   │   ├── pipeline.py                   LangGraph 问诊图与独立检索
│   │   ├── graph_state.py                问诊图的请求级状态
│   │   └── services/
│   │       ├── privacy.py                隐私脱敏
│   │       ├── triage.py                 急症危险信号
│   │       ├── symptoms.py               症状结构化和追问
│   │       ├── persistent_index.py       SQLite FTS5/BM25
│   │       ├── embedding_text.py         分类型向量文本规则
│   │       ├── embedding.py              医疗 Embedding
│   │       ├── faiss_index.py            FAISS 在线查询
│   │       ├── retrieval.py              内存 BM25 和 RRF
│   │       ├── reranker.py               Cross-Encoder 精排
│   │       ├── filters.py                人群与版本过滤
│   │       ├── generator.py              证据约束生成
│   │       ├── langchain_chat.py         统一模型调用和完整 JSON 验证
│   │       ├── langchain_retrieval.py    BM25 / FAISS Retriever 适配
│   │       ├── document_graph.py         报告检索与解释图
│   │       ├── validator.py              生成后校验
│   │       └── model_workers.py           MPS/Torch 模型进程隔离
│   ├── scripts/
│   │   ├── pull_huatuo.py                拉取并规范化 Huatuo 数据
│   │   ├── build_search_index.py         构建 SQLite/BM25
│   │   ├── build_faiss_index.py          构建全量 FAISS
│   │   ├── inspect_retrieval.py          检查四阶段排名
│   │   └── evaluate_retrieval.py         计算 Recall/MRR
│   ├── tests/test_pipeline.py             后端局部回归测试
│   └── data/
│       ├── raw/                           JSONL.GZ 分片和下载清单
│       ├── processed/
│       │   ├── knowledge.db               原文和 BM25，约1.6GB
│       │   ├── medical.faiss              向量索引，约97MB
│       │   └── medical.faiss.json         FAISS 构建清单
│       └── models/                        Hugging Face 模型缓存，约4.3GB
├── frontend/
│   ├── src/api/client.ts                  后端接口封装
│   ├── src/components/                    表单、流程、证据和结果组件
│   ├── src/types.ts                       前端业务类型
│   └── vite.config.ts                     开发代理到后端8000端口
└── README.md
```

`knowledge.db-wal` 和 `knowledge.db-shm` 是 SQLite 在 WAL 模式下可能产生的运行辅助文件，不是另一份医疗数据。

## 8. 从零构建项目

### 8.1 环境要求

- Python 3.12 推荐；
- Node.js 20.19 或更高版本；
- macOS Apple Silicon 可使用 MPS；
- Linux NVIDIA 环境可使用 CUDA；
- CPU 可以运行，但百万级向量化会明显更慢。

### 8.2 创建 Python 环境

```bash
cd /Users/codesun/ai-coding/medical-rag-demo

python3.12 -m venv .venv-full
source .venv-full/bin/activate
python -m pip install -r backend/requirements-full.txt
```

### 8.3 拉取全部 Huatuo 数据

```bash
python3 backend/scripts/pull_huatuo.py \
  --sources knowledge_graph encyclopedia \
  --limit 0 \
  --shard-size 50000
```

如果下载中断：

```bash
python3 backend/scripts/pull_huatuo.py \
  --sources knowledge_graph encyclopedia \
  --limit 0 \
  --shard-size 50000 \
  --resume
```

### 8.4 构建 SQLite 与 BM25

首次构建：

```bash
PYTHONPATH=backend .venv-full/bin/python \
  backend/scripts/build_search_index.py
```

需要明确覆盖旧文件时：

```bash
PYTHONPATH=backend .venv-full/bin/python \
  backend/scripts/build_search_index.py --force
```

重建 `knowledge.db` 后，SQLite `rowid` 或文档数量可能变化，因此必须同步重建 FAISS，不能继续使用旧向量文件。

### 8.5 首次构建全量 FAISS

macOS Apple Silicon：

```bash
caffeinate -i env \
  HF_HUB_OFFLINE=1 \
  PYTHONPATH=backend \
  .venv-full/bin/python backend/scripts/build_faiss_index.py \
  --device mps \
  --batch-size 64 \
  --fetch-size 2048 \
  --checkpoint-every 25000 \
  --document-max-length 256 \
  --training-sample-size 100000 \
  --nlist 2048 \
  --pq-m 64 \
  --pq-bits 8 \
  --force
```

`HF_HUB_OFFLINE=1` 只适用于模型已经下载完成的情况。第一次下载模型时应移除该变量。

Linux NVIDIA 环境把 `--device mps` 改为 `--device cuda`。内存不足时可以把 `--batch-size 64` 改为 `32` 或 `16`。

### 8.6 中断后继续 FAISS

第一次启动使用 `--force`；发生中断后，必须把最后一个参数改成 `--resume`：

```bash
caffeinate -i env \
  HF_HUB_OFFLINE=1 \
  PYTHONPATH=backend \
  .venv-full/bin/python backend/scripts/build_faiss_index.py \
  --device mps \
  --batch-size 64 \
  --fetch-size 2048 \
  --checkpoint-every 25000 \
  --document-max-length 256 \
  --training-sample-size 100000 \
  --nlist 2048 \
  --pq-m 64 \
  --pq-bits 8 \
  --resume
```

注意：

- `--force` 会丢弃旧 FAISS 和断点，从零开始；
- `--resume` 使用 `.building` 文件继续；
- 每25,000条保存一次断点；
- 模型、模型子目录、向量文本规则、最大长度和目标文档数必须匹配；
- 构建完成后 `.building` 会原子发布为正式文件。

## 9. 查看数据和检索结果

### 9.1 查看 FAISS 清单

```bash
.venv-full/bin/python -m json.tool \
  backend/data/processed/medical.faiss.json
```

`medical.faiss` 是二进制文件，不能作为 JSON 打开。人类通常查看构建清单和实际检索结果，而不是直接阅读压缩向量。

### 9.2 查看 SQLite 中的原始问答

```bash
sqlite3 -header -column backend/data/processed/knowledge.db \
  "SELECT document_id, question, substr(content, 1, 300) AS answer
   FROM documents
   WHERE question LIKE '%饿了%'
   LIMIT 10;"
```

### 9.3 并排检查四阶段检索

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=backend \
  .venv-full/bin/python backend/scripts/inspect_retrieval.py \
  "饿了就肚子痛" --top-k 10
```

输出依次包括：

1. BM25 独立召回；
2. FAISS 独立召回；
3. RRF 混排；
4. Cross-Encoder 精排。

如果只想检查召回，不想加载约2GB的 Reranker 权重：

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=backend \
  .venv-full/bin/python backend/scripts/inspect_retrieval.py \
  "饿了就肚子痛" --top-k 10 --skip-reranker
```

## 10. 启动后端和前端

### 10.1 环境变量

后端会自动加载 `backend/.env`，同时保留系统环境变量的更高优先级。先复制示例文件：

```bash
cp backend/.env.example backend/.env
```

常用配置：

| 环境变量 | 默认值 | 含义 |
|---|---|---|
| `SEARCH_INDEX_PATH` | `backend/data/processed/knowledge.db` | SQLite/BM25 文件 |
| `FAISS_INDEX_PATH` | `backend/data/processed/medical.faiss` | FAISS 二进制文件 |
| `FAISS_MANIFEST_PATH` | `backend/data/processed/medical.faiss.json` | FAISS 构建清单 |
| `MODEL_CACHE_DIR` | `backend/data/models` | 模型缓存目录 |
| `BM25_TOP_K` | `100` | BM25 独立召回数量 |
| `VECTOR_TOP_K` | `100` | FAISS 独立召回数量 |
| `RRF_TOP_K` | `40` | RRF 保留候选数 |
| `FINAL_TOP_K` | `4` | 最终证据数量 |
| `FAISS_NPROBE` | `32` | FAISS 查询探测分区数 |
| `EMBEDDING_MODEL` | `ming0302/bge-m3-medical-cn` | 查询和建库共用模型 |
| `EMBEDDING_MODEL_SUBFOLDER` | `model` | 模型仓库内子目录 |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | Cross-Encoder 模型 |
| `MODEL_DEVICE` | `auto` | `auto`、`mps`、`cuda` 或 `cpu` |
| `LLM_BASE_URL` | 空 | OpenAI 兼容接口根地址或完整 `/chat/completions` 地址 |
| `LLM_API_KEY` | 空 | 接口密钥，禁止提交仓库 |
| `LLM_MODEL` | 空 | 兼容接口实际支持的模型名称 |
| `LLM_VISION_MODEL` | 沿用 `LLM_MODEL` | 图片报告转录模型，必须真实支持视觉输入 |
| `LLM_TIMEOUT_SECONDS` | `180` | 单次生成请求超时秒数 |
| `LLM_EVIDENCE_MAX_CHARACTERS` | `2500` | 每条最终证据发送给 LLM 的最大字符数 |
| `LLM_MAX_OUTPUT_TOKENS` | `1200` | 单次结构化回答最大输出 Token 数 |
| `LLM_STRUCTURED_METHOD` | `prompt` | prompt 兼容输出或 json_mode 服务端 JSON 输出 |
| `MEDICAL_DOCUMENT_MAX_OUTPUT_TOKENS` | `2400` | 报告转录与结构化解读最大输出 Token 数 |
| `LLM_ENABLE_THINKING` | 空 | 支持思考开关的接口可设为 `false`，其他接口留空 |
| `RETRIEVAL_LOG_TOP_K` | `10` | 每个检索阶段打印的最大候选数量 |
| `RETRIEVAL_LOG_CONTENT_CHARACTERS` | `300` | 每条检索结果打印的正文预览字符数 |
| `MEDICAL_DOCUMENT_MAX_BYTES` | `12582912` | 单个上传文件最大字节数，默认 12 MB |
| `MEDICAL_DOCUMENT_MAX_CHARACTERS` | `30000` | 单份资料最多进入模型的提取文字数 |
| `MEDICAL_DOCUMENT_MAX_PDF_PAGES` | `20` | 单份 PDF 最多读取页数 |

Embedding 查询模型必须与 `medical.faiss.json` 中的建库模型和子目录完全一致，否则服务拒绝加载向量索引。

### 10.2 启动后端

从项目根目录启动时，可以直接使用统一脚本：

```bash
pnpm dev:server
```

等价的后端命令如下；配置模块会自动读取 `backend/.env`，不需要额外传 `--env-file`：

```bash
HF_HUB_OFFLINE=1 MODEL_DEVICE=mps PYTHONPATH=backend \
  .venv-full/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000
```

启动时会预热 Reranker；Embedding 查询模型在第一次向量查询时延迟加载。

配置完整并且最终证据非空时，系统会把脱敏后的用户问题、追问、最终 Top 4 证据的标题、来源、可信等级、治疗权限和正文发送给 LLM。前端“结构化答案生成”轨迹应显示 `configured-llm`；若显示 `evidence-template`，同一行会说明缺少的配置、HTTP 状态、网络错误或响应格式错误。

### 10.3 请求、检索和 LLM 日志

后端终端会按同一个 `request_id` 输出三类中文 JSON 日志：

```text
[用户输入] {"request_id":"...","symptoms":"脱敏后的用户描述",...}
[检索结果][BM25] {"request_id":"...","total":100,"candidates":[...]}
[检索结果][FAISS] {"request_id":"...","total":100,"candidates":[...]}
[检索结果][RRF] {"request_id":"...","total":40,"candidates":[...]}
[检索结果][Reranker] {"request_id":"...","total":40,"candidates":[...]}
[检索结果][最终证据] {"request_id":"...","total":4,"candidates":[...]}
[LLM请求] request_id=... stage=consultation-generation model=... backend=langchain max_tokens=1200
[LLM响应] request_id=... stage=consultation-generation model=... finish_reason=stop
```

用户日志保留原有隐私处理后的文本和检索候选。共享 LangChain 模型日志不再打印完整提示词、图片、响应正文或密钥；格式错误也只返回安全错误类型。每次独立研究检索仍生成自己的 request_id。生产环境应控制本地调试日志访问与保留期限。

### 10.4 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://127.0.0.1:5173
```

Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 11. API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 服务状态和版本 |
| GET | `/api/knowledge/stats` | 文档数量、来源、FAISS、Reranker 和 LLM 配置状态 |
| GET | `/api/atlas/body` | 人体系统、器官科普说明和健康观察边界 |
| POST | `/api/research/search` | 不调用 LLM 的 BM25、FAISS、RRF 与 Reranker 证据检索 |
| POST | `/api/documents/interpret` | 上传单份资料，执行提取、脱敏、RAG 与结构化辅助解读 |
| POST | `/api/consult` | 执行完整医疗安全检索链路 |
| GET | `/docs` | FastAPI 交互式接口文档 |

咨询示例：

```bash
curl -X POST http://127.0.0.1:8000/api/consult \
  -H 'Content-Type: application/json' \
  -d '{
    "symptoms": "饿了就肚子痛，吃点东西会缓解",
    "age": 28,
    "sex": "male",
    "pregnant": false,
    "region": "CN",
    "duration": "一周",
    "temperature": null,
    "additional_info": null
  }'
```

响应会包含：

- `blocked` 和 `urgency`：是否被安全链路阻断；
- `summary` 和 `sections`：结构化辅助信息；
- `citations`：资料来源和摘要；
- `follow_up_questions`：需要补充的信息；
- `structured_symptoms`：结构化症状；
- `pipeline`：每个阶段的状态、说明和耗时；
- `validation_issues`：生成后校验失败原因；
- `retrieval_mode`：本次实际使用的检索和精排方式；
- `generation_mode`：`configured-llm`、`evidence-template` 或急症分支的 `not-run`；
- `generation_model`：本次成功生成答案的模型名称，回退时为空。

## 12. 降级策略

系统不会把缺失组件静默伪装成完整链路：

| 缺失或失败组件 | 实际行为 |
|---|---|
| `knowledge.db` 不存在 | 加载少量示例数据，仅运行内存 BM25 |
| `medical.faiss` 不存在或不匹配 | 保留全量 SQLite BM25，FAISS 标记为 fallback |
| Reranker 模型不可用 | 使用词元重合度和医疗证据策略排序，并标记 fallback |
| 未配置 LLM 或调用失败 | 使用证据模板生成，标记 fallback，并在流程轨迹显示安全失败原因 |
| 没有候选或校验失败 | 阻断回答，返回拒绝原因和就医建议 |

可通过以下接口确认当前是否真正启用全量 FAISS 和 Reranker：

```bash
curl http://127.0.0.1:8000/api/knowledge/stats
```

## 13. 评测检索质量

单个示例只能说明某次检索看起来合理，不能证明整体准确率。正式评测应由医生或标注人员在检索逻辑之外维护 qrels：

```json
{"query":"口语化症状描述","relevant_document_ids":["医生确认相关的文档ID"]}
```

执行：

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=backend \
  .venv-full/bin/python backend/scripts/evaluate_retrieval.py \
  --qrels /path/to/doctor-reviewed-qrels.jsonl \
  --top-k 20
```

脚本分别计算：

- BM25 Recall@K 和 MRR@K；
- FAISS Recall@K 和 MRR@K；
- RRF Recall@K 和 MRR@K；
- Reranker Recall@K 和 MRR@K。

评测查询和标准答案不能写入召回代码，否则得到的是针对样例的硬编码结果，不是真实泛化能力。

## 14. 测试

后端局部回归测试：

```bash
PYTHONPATH=backend .venv-full/bin/python \
  -m unittest discover -s backend/tests -v
```

前端类型检查：

```bash
cd frontend
npm run typecheck
```

## 15. 常见问题

### 15.1 模型加载出现 `UNEXPECTED` 是否失败

Embedding 模型仓库还包含稀疏检索和 ColBERT 相关权重，而当前项目只使用稠密向量主干给 FAISS。类似下面的提示不是本次稠密 FAISS 构建失败：

```text
colbert_linear ... UNEXPECTED
sparse_linear ... UNEXPECTED
```

最终应以是否出现 `模型已加载`、`全量 FAISS 索引完成`，以及清单中的 `status=complete` 为准。

### 15.2 为什么 FAISS 文件不能直接打开

`medical.faiss` 是经过 IVF-PQ 压缩的二进制索引，不是 JSON。应查看 `medical.faiss.json`、运行 `inspect_retrieval.py`，或者根据命中的 `document_id` 到 SQLite 查看原文。

### 15.3 为什么第一次查询较慢

Embedding 查询模型使用延迟加载，第一次 FAISS 查询需要从磁盘加载模型到 CPU、MPS 或 CUDA；后续查询会复用同一个模型进程。

### 15.4 为什么启动时内存占用较高

后端启动会预热 Reranker，第一次向量查询还会加载 Embedding。如果两者同时常驻，模型权重会占用数GB内存。学习环境可以通过 `--skip-reranker` 检查召回，正式运行则应根据机器内存调整部署方式。

### 15.5 为什么治疗问题经常被拒绝

当前115万条主体是 Huatuo 二级参考问答，默认没有治疗生成权限。它们可以帮助找到相关资料，但不能自动升级成处方或当前治疗标准。只有接入并正确标注当前指南、临床路径和药品说明书后，治疗生成才可能获得授权。

## 16. 已实现能力与仍需补充的内容

### 已实现

- 百万级 Huatuo 数据流式拉取和 Gzip JSONL 分片；
- 115万条 SQLite FTS5/BM25 全量关键词召回；
- 115万条医疗 Embedding/FAISS 全量语义召回；
- 分类型、问题优先的向量文本规则；
- RRF 去重混排和真实 Cross-Encoder 精排；
- 隐私脱敏、急症规则、症状结构化与追问；
- 年龄、孕期、地区和指南版本过滤框架；
- 证据约束生成、引用和治疗权限校验；
- 检索检查工具和外部 qrels 评测工具；
- Vue 3 前端与 FastAPI 接口。

### 仍需补充

- 国家卫健委指南、临床路径和中国药品说明书的正式采集与版本管理；
- 医生审核的急症规则和检索 qrels；
- 对体重、肝肾功能、合并用药和药物相互作用的结构化过滤；
- 更完整的许可证、更新时间和来源追溯；
- 持续的 Recall、MRR、安全召回率和错误案例评测；
- 生产环境鉴权、审计日志、限流、监控、加密和隐私合规。

## 17. 医疗和数据安全边界

- Huatuo 问答用于提高召回覆盖率，不应作为当前治疗标准答案；
- 具体治疗应引用当前有效指南、临床路径或药品说明书；
- 药物剂量必须结合地区、年龄、体重、孕期、肝肾功能和合并用药；
- 规则未命中不代表不存在急症，模型召回也不能替代专业分诊；
- 所有模型都可能漏召回、错排或生成错误，必须保留人工复核；
- 不要把真实患者姓名、联系方式、身份证、病历或密钥提交到仓库；
- 商业使用前必须重新核查每个数据集、论文和模型的许可证与原始数据权利。

## 18. 数据与模型入口

- [Huatuo-26M](https://github.com/FreedomIntelligence/Huatuo-26M)
- [Huatuo 知识图谱问答](https://huggingface.co/datasets/FreedomIntelligence/huatuo_knowledge_graph_qa)
- [Huatuo 医疗百科问答](https://huggingface.co/datasets/FreedomIntelligence/huatuo_encyclopedia_qa)
- [bge-m3-medical-cn](https://huggingface.co/ming0302/bge-m3-medical-cn)
- [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)

## 19. 部署到 Vercel

### 19.1 部署边界

本项目采用前后端分离部署。Vercel 只构建并托管 `frontend`，不能直接承载当前完整后端：本地处理后索引约 1.7GB，Embedding 和 Reranker 模型约 4.3GB，而且模型需要常驻内存、单次咨询可能运行数十秒。

```mermaid
flowchart LR
    U["用户浏览器"] --> V["Vercel / Vue 前端"]
    V -->|"VITE_API_BASE_URL / HTTPS"| B["长期运行的 FastAPI 后端"]
    B --> I["SQLite + FAISS 索引"]
    B --> M["Embedding + Reranker"]
    B --> L["OpenAI 兼容 LLM"]
```

后端可以部署到具有足够磁盘和内存的云服务器、容器服务或 GPU/CPU 实例。后端必须提供公网 HTTPS 地址，并持久化 `backend/data/processed` 与 `backend/data/models`。

### 19.2 已提供的部署文件

- `vercel.json`：从仓库根目录安装并构建 `frontend`，产物为 `frontend/dist`；
- `.github/workflows/vercel-deploy.yml`：推送 `main` 且前端相关文件变化时自动部署；
- `frontend/.env.example`：说明生产 API 地址；
- `backend/.env.example`：提供后端 CORS 配置示例。

### 19.3 创建 Vercel 项目

1. 在 Vercel 新建项目并导入当前 GitHub 仓库。
2. 项目 Root Directory 保持仓库根目录，不要选择 `frontend`，因为根目录已有 `vercel.json`。
3. 在 Vercel Project Settings → Environment Variables 添加：

```text
VITE_API_BASE_URL=https://你的后端域名
```

地址不要以 `/` 结尾，不要填写 `/api`。例如后端健康检查是 `https://api.example.com/api/health`，这里应填写 `https://api.example.com`。

### 19.4 配置后端 CORS

在后端生产环境变量中填写 Vercel 正式域名：

```dotenv
CORS_ORIGINS=https://你的项目.vercel.app
```

如果同时使用正式域名和自定义域名，以逗号分隔：

```dotenv
CORS_ORIGINS=https://你的项目.vercel.app,https://medical.example.com
```

修改后必须重启 FastAPI。不要使用 `*`，因为医疗输入属于敏感数据，应只允许明确的前端域名。

### 19.5 配置 GitHub Actions Secrets

先在本地项目根目录登录并关联一次 Vercel 项目：

```bash
pnpm add --global vercel@56.5.0
vercel login
vercel link
```

关联后，本地 `.vercel/project.json` 中可以看到 `orgId` 和 `projectId`。`.vercel` 已加入 `.gitignore`，不要提交该目录。

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 来源 |
|---|---|
| `VERCEL_TOKEN` | Vercel Account Settings → Tokens 创建 |
| `VERCEL_ORG_ID` | `.vercel/project.json` 的 `orgId` |
| `VERCEL_PROJECT_ID` | `.vercel/project.json` 的 `projectId` |

随后可以推送 `main` 触发部署，或在 GitHub Actions 页面手动运行 `Deploy Web to Vercel`。

### 19.6 验证部署

依次检查：

```text
https://你的后端域名/api/health
https://你的后端域名/api/knowledge/stats
https://你的前端域名.vercel.app
```

如果前端可以打开但显示“等待后端连接”，重点检查浏览器 Network：

- 请求仍是 Vercel 自己的 `/api`：Vercel 没有配置 `VITE_API_BASE_URL`，需要重新部署；
- CORS 拒绝：后端 `CORS_ORIGINS` 缺少当前前端域名，或域名带了错误路径；
- Mixed Content：前端是 HTTPS，但后端仍是 HTTP，必须给后端配置 HTTPS；
- 502/504：后端模型未加载完成、内存不足或反向代理超时；
- 页面显示 `evidence-template`：后端 LLM 配置缺失或调用失败，与 Vercel 前端部署无关。

### 19.7 Preview 部署说明

每个 Vercel Preview 都会产生不同域名，固定的 CORS 白名单不会自动覆盖这些域名。医疗项目建议先只开放 Production 域名；如果确实需要 Preview，应在后端实现经过校验的 Vercel Preview 域名规则，而不是直接把 CORS 改成 `*`。
