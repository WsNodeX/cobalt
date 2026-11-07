<div align="center">

# cobalt

### 零依赖的 Python 缓存工具包：一套统一的接口，覆盖七种淘汰策略与 W-TinyLFU

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-2DA44E)](./LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-9F1D35)](https://pypi.org/project/cobalt)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/WsNodeX/cobalt)
[![Tests](https://img.shields.io/badge/tests-71%20passing-brightgreen)](./.github/workflows/ci.yml)

**FIFO · LRU · LFU · LRU-K · SLRU · ARC · TinyLFU · W-TinyLFU — 同一套 API，可插拔切换**

</div>

---

<p align="center">
  <a href="#-为什么需要多策略缓存">✨ 为什么</a> ·
  <a href="#-特性">🚀 特性</a> ·
  <a href="#-安装">📦 安装</a> ·
  <a href="#-快速开始">⚡ 快速开始</a> ·
  <a href="#-架构">🏗️ 架构</a> ·
  <a href="#-api-速查表">🔌 API 速查表</a> ·
  <a href="#-路线图">🧭 路线图</a> ·
  <a href="#-贡献">🤝 贡献</a> ·
  <a href="#-许可证">📄 许可证</a>
</p>

---

## ✨ 为什么需要多策略缓存

缓存在后端系统里无处不在：数据库查询结果、RPC 响应、模板渲染、会话状态、限流计数……但它从来不是一个 `dict` 那么简单。真正决定缓存**有效**的，是当它满了之后**该丢掉谁**——这就是「淘汰策略（eviction policy）」。

- 只用 `dict`：内存会无限增长，最终 OOM。
- 用错策略：在「热点高度集中」的负载下用 FIFO，会把正在被反复访问的数据踢掉；在「扫描型」负载下用纯 LRU，一次全表遍历就会冲垮整个缓存。
- 盲目上重量级依赖：很多时候你只是想要一个可靠的本地缓存，却被迫引入一整套带 C 扩展的库。

`cobalt` 的出发点很直接：**把业界验证过的淘汰算法，用纯 Python 标准库实现出来，统一在同一套接口下，让你一行代码切换策略、用数据说话地选型。** 它还是一份高质量的可读源码——每个策略几百行，适合作为面试复习与算法学习的材料。

---

## 🚀 特性

- **零第三方依赖**：仅用 Python 标准库（`collections`、`functools`、`threading`、`hashlib` 等），`pip install` 之后没有任何编译或二进制负担。
- **八种策略开箱即用**：FIFO、LRU、LFU、LRU-K、SLRU、ARC、TinyLFU、W-TinyLFU。
- **统一的流畅构建器**：`CacheBuilder(...).maximum_size(n).expire_after(t).thread_safe().build()`，按策略自动注入专属参数（`k`、`window_ratio`、`protected_ratio`）。
- **可选的线程安全门面**：`ThreadSafeCache` 用可重入锁包裹任意缓存，Web 服务、worker 池里可放心当 drop-in 替换。
- **`cachetools` 风格的 `@cached` 装饰器**：把任意函数的结果自动记忆化进 cobalt 缓存。
- **容量 + TTL 双层约束**：每条写入可带过期时间，过期条目在访问时被惰性清除，绝不残留墓碑。
- **内建统计**：命中率、未命中、写入、淘汰数实时可查，策略对比一键出表。
- **可注入时钟**：测试里塞一个假时钟即可做到完全确定性，不依赖 `sleep`。
- **CLI 自带 demo 与基准**：`python -m cobalt.cli bench` 直接打印各策略在相同倾斜负载下的命中率。

---

## 📦 安装

```bash
# 从源码安装（本仓库）
pip install git+https://github.com/WsNodeX/cobalt.git

# 或者在本仓库根目录
pip install .
```

> cobalt 没有运行时依赖，Python 3.9+ 即可。

---

## ⚡ 快速开始

```python
from cobalt import CacheBuilder, Policy

# 1) 一行构建最常用的 LRU 缓存
cache = CacheBuilder(Policy.LRU).maximum_size(128).build()
cache.put("user:1", {"name": "ada"})
print(cache.get("user:1"))          # -> {'name': 'ada'}
print("user:1" in cache)            # -> True

# 2) 用 W-TinyLFU 应对「扫描型 + 热点型」混合负载
hot = CacheBuilder(Policy.W_TINY_LFU).maximum_size(1024).build()
hot.put("k", "v")

# 3) 给一个慢函数加缓存
from cobalt import cached

@cached(cache)
def expensive(i: int) -> int:
    return i * i

expensive(4)   # 第一次计算并写入
expensive(4)   # 第二次直接命中

# 4) 看统计
print(cache.stats.as_dict())
# {'hits': 1, 'misses': 0, 'puts': 1, 'evictions': 0,
#  'requests': 1, 'hit_rate': 1.0, 'miss_rate': 0.0}
```

跑内置示例与基准：

```bash
python examples/demo.py
python -m cobalt.cli bench --size 256 --requests 20000
```

---

## 🏗️ 架构

`cobalt` 采用「基类管横切、子类管排序」的分层设计：所有缓存共享容量、TTL、时钟、统计与存储原语；每个策略只关心自己的**排序结构**（OrderedDict / 频率表 / ARC 象限 / 草图）。

```text
                       ┌──────────────────────────────┐
                       │         CacheBuilder          │
                       │     (fluent, 策略感知)        │
                       └──────────────┬───────────────┘
                                      │ .build()
                                      ▼
                       ┌──────────────────────────────┐
                       │        create(policy)         │
                       │    Policy 枚举 + 注册表        │
                       └──────────────┬───────────────┘
                                      ▼
       ┌──────────────────────────────────────────────────────┐
       │                     BaseCache                         │
       │   容量 · TTL · Clock · CacheStats · 存储原语           │
       └───────┬───────────────┬──────────────┬───────────────┘
               │               │              │
   ┌───────────┴────┐ ┌────────┴───────┐ ┌────┴───────────┐
   │ FIFOCache      │ │ LRUCache       │ │ LFUCache       │
   │ LRUKCache      │ │ SLRUCache      │ │ ARCCache       │
   │ WTinyLfuCache  │ │ TinyLfu(准入)  │ │                │
   └────────────────┘ └────────────────┘ └────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │          ThreadSafeCache             │
                    │     (RLock 门面, 可选)               │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │          @cached 装饰器              │
                    └─────────────────────────────────────┘
```

**设计要点**

- `BaseCache` 持有 `_data` / `_expires` / `_stats`，提供 `_store` / `_drop` / `_ensure_fresh` / `_is_expired` 等原语；子类只覆写 `get` / `put`（建议覆写 `delete` / `clear`）。
- `LRUCache` 用 `OrderedDict` 的「移到末尾」实现 O(1) 最近最少使用。
- `LFUCache` 用「频率 → 该频率下的键集合」两层 `OrderedDict`，做到 O(1) 取最低频键。
- `WTinyLfuCache` 拆成 window / probation / protected 三段，靠 Count-Min 草图做准入判断（Caffeine 的同款思想），再用周期性 aging 抵消频率偏置。
- `Clock` 把时间源抽象出来，测试里传 `lambda: 0` 即可让 TTL 完全可控。

---

## 🔌 API 速查表

| 入口 | 签名 / 用法 | 说明 |
|---|---|---|
| `CacheBuilder` | `CacheBuilder(policy=Policy.LRU)` | 流畅构建器，链式配置 |
| `.maximum_size(n)` | `n: int \| None` | 容量上限，`None` 为无界 |
| `.expire_after(sec)` | `sec: float \| None` | 每条写入的 TTL（秒） |
| `.clock(fn)` | `fn: () -> float` | 注入时间源（测试用） |
| `.name(str)` | `name: str` | 缓存命名（统计/调试） |
| `.k(n)` | `n: int` | LRU-K 的准入引用次数 |
| `.window_ratio(r)` | `r: float` | W-TinyLFU 窗口占比 |
| `.protected_ratio(r)` | `r: float` | SLRU / W-TinyLFU 保护段占比 |
| `.thread_safe()` | 默认 `True` | 包裹 `ThreadSafeCache` |
| `.build()` | `-> BaseCache` | 产出缓存实例 |
| `Policy` | `fifo/lru/lfu/lruk/slru/arc/wtinylfu` | 策略枚举 |
| `create(policy, **kw)` | 工厂函数 | 按名字或枚举实例化 |
| `cache.get(k, d=None)` | `-> Any` | 读取，命中刷新顺序/频率 |
| `cache.put(k, v)` | `-> None` | 写入，必要时淘汰 |
| `cache.peek(k, d)` | `-> Any` | 读但不影响淘汰/TTL |
| `cache.delete(k)` | `-> bool` | 删除，返回是否存在 |
| `cache.stats` | `CacheStats` | 命中/未命中/写入/淘汰 |
| `ThreadSafeCache(cache)` | 门面 | 全操作加锁 |
| `@cached(cache, key_fn)` | 装饰器 | 函数结果记忆化 |

**异常层级**：`CobaltError` → (`InvalidConfiguration`、`KeyNotHashable`、`UnsupportedPolicy`)，分别继承 `ValueError` / `TypeError` / `KeyError`，便于精确捕获。

---

## 🧭 路线图

- [ ] `weigher` 支持：按值大小而非条目数计容量（适合缓存大对象）。
- [ ] `refresh_after_write`：后台异步刷新即将过期的条目，避免击穿。
- [ ] 软引用 / 进程级共享（mmap）后端，突破单进程内存上限。
- [ ] 把 `bench` 跑分结果落盘为可对比的 JSON 报告。
- [ ] 可选 `orjson` 加速序列化（默认仍零依赖）。

---

## 🤝 贡献

欢迎以 issue / PR 形式参与。任何新策略都请：

1. 在 `cobalt/policies/` 下新建模块，继承 `BaseCache`；
2. 在 `policies/__init__.py` 与 `policy.py` 的注册表里登记；
3. 在 `tests/` 下补齐覆盖 `get/put/淘汰/容量/统计` 的用例；
4. 本地 `python -m unittest discover -s tests` 全绿后再提交。

---

## 📄 许可证

[MIT](./LICENSE) © WsNodeX

---

<!--
=====================================================================
以下为中文技术科普长文底稿（README 已可读，本区块仅供公众号 / 博客发文复用）
=====================================================================

# 缓存淘汰策略到底怎么选？一份能直接背去面试的清单

## 一、痛点：你的缓存为什么「没用」
很多同学写缓存就是 `data = cache.get(k) or compute(k)` 然后塞进一个 `dict`。
问题在容量：dict 不会自己瘦身，热点数据和非热点数据被一视同仁，
一旦流量上来，内存涨、GC 抖、最后 OOM。缓存的「有效性」不取决于它存了多少，
而取决于它**满的时候踢掉谁**——这就是淘汰策略。

## 二、原理：八种策略一句话讲清
- FIFO（先进先出）：谁先来谁先走。实现最简单，但对访问局部性一无所知。
- LRU（最近最少使用）：把「最久没被访问」的踢掉。对局部性友好，但扛不住「一次性扫描全表」——
  一次遍历就把真正的热点全冲掉了（scan resistance 差）。
- LFU（最不经常使用）：记录访问频率，踢最低频。但新来的冷数据因为频率低，
  一进来就容易被踢，且老热点「占着茅坑」（frequency bias）。
- LRU-K：一个条目要被访问 K 次才算「热」，靠历史延迟准入，天然抗扫描。
- SLRU（分段 LRU）：试用期 + 保护期两段，热段只进不出（除非溢出），比纯 LRU 更稳。
- ARC（自适应替换）：同时维护 LRU 与 LFU 两条列表加「幽灵」记录历史命中，
  用一个自适应参数 p 在两者之间动态倾斜，scan resistance 与 hit rate 兼得。
- TinyLFU / W-TinyLFU：用 Count-Min 草图近似频率（O(1)、内存极小），
  写入前先和新进窗口项「准入比武」，打不过就不让进；Caffeine 用的就是这套思想。

## 三、实现：cobalt 是怎么把它们写清楚的
- 分层：`BaseCache` 管容量/TTL/时钟/统计/存储，子类只管排序结构，代码不重复。
- 零依赖：全部用标准库，OrderedDict 做 LRU、两层 OrderedDict 做 O(1) LFU、
  RLock 做线程安全门面，没有 C 扩展、没有编译。
- 可测：把时间抽象成 `Clock`，测试里传假时钟，TTL 行为完全确定，不靠 sleep。
- 可插拔：`CacheBuilder` + `Policy` 枚举，一行切换策略，统计实时对比命中率。

## 四、对比：什么时候用哪个（选型速记）
- 通用、访问有局部性 → LRU
- 有明显稳定热点、怕扫描 → W-TinyLFU / ARC
- 想抗一次性全表遍历 → LRU-K / SLRU / ARC
- 极简、不在乎局部性 → FIFO
- 纯频率导向、条目少 → LFU（注意它的冷启动缺陷）

跑 `python -m cobalt.cli bench` 看同一份倾斜负载下各策略的真实命中率，比拍脑袋准。

## 五、扩展：加一个新策略只要四步
继承 `BaseCache` → 在注册表登记 → 在构建器里挂专属参数 → 补测试。
接口统一，代价极低。

## 六、发布稿提示（社媒抓手）
- 标题钩子：「面试被问缓存淘汰策略？别再只背 LRU 了」
- 金句：「缓存有没有用，不看它存了多少，看它满的时候踢谁」
- 行动点：clone 下来跑 `bench`，把你业务负载套进去比一比
- 标签：#Python #后端 #缓存 #面试 #算法
-->
