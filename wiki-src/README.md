# 知识库维护说明

站点地址：<https://zain0214.github.io/dsh-workspace/wiki/>

---

## 一、它是什么

仓库里的 Markdown 笔记 → 渲染成静态网页 → 放在 `wiki/` 目录 → GitHub Pages 直接托管。

没有后端、不用构建服务器、不依赖任何付费服务。push 完等 1 分钟就生效。

```
你的笔记 .md（本地，仓库根目录 / bilibili-notes/ …，不进公开仓库）
        │
        │  python3 wiki-src/build.py   ← 自动脱敏
        ├──────────────► wiki/             生成的网页（提交）
        └──────────────► wiki-src/notes/   脱敏后的 .md 副本（提交）
```

**两个关键点：**

1. **`wiki/` 是生成物，不要手改。** 改了下次构建会被覆盖。要改内容，改源 `.md`。
2. **原始笔记不进公开仓库**（`.gitignore` 已挡住）。公开的是 `wiki/` 和 `wiki-src/notes/` 里的脱敏副本。

---

## 二、加一篇新笔记

### 第 1 步：写笔记

在仓库里任意位置新建 `.md`，正常写 Markdown。支持标题、列表、表格、引用、代码块、加粗。

### 第 2 步：登记到构建脚本

打开 `wiki-src/build.py`，找到 `NOTES` 列表，加一行：

```python
(
    "你的笔记文件.md",        # 源文件相对仓库根目录的路径
    "learning",              # 分类 id：learning / basketball / exam / english
    "my-new-note",           # URL 名（英文、短横线，会变成 wiki/learning/my-new-note.html）
    "笔记标题",               # 网页上显示的标题
    "一句话摘要，会出现在首页和搜索结果里。",
    ["标签1", "标签2"],       # 标签，也参与搜索
),
```

### 第 3 步：重新构建

```bash
python3 wiki-src/build.py
```

### 第 4 步：提交

```bash
git add wiki wiki-src
git commit -m "知识库：新增 xxx"
git push
```

---

## 三、加一个新分类

改 `build.py` 顶部的 `CATEGORIES`：

```python
CATEGORIES = [
    ("learning", "学习方法", "怎么用 AI、怎么学得更快"),
    ...
    ("newcat", "新分类名", "一句话说明"),   # ← 加这行
]
```

然后笔记的第二个字段填 `"newcat"` 就行，目录会自动建。

---

## 四、修改已有笔记

直接改源 `.md`，然后：

```bash
python3 wiki-src/build.py && git add wiki && git commit -m "更新：xxx" && git push
```

---

## 五、本地预览

```bash
python3 wiki-src/build.py
python3 -m http.server 8080 -d wiki
```

浏览器打开 <http://localhost:8080>。

> ⚠️ 必须用 `http://localhost` 打开，不要直接双击 `wiki/index.html`——双击是 `file://` 协议，首页搜索会因为浏览器安全限制加载不了索引。

---

## 六、隐私说明

仓库是**公开**的，`wiki/` 里的内容所有人都能看到。

构建脚本里有一个 `REDACT` 字典，会在渲染时替换掉敏感词：

```python
REDACT = {
    "武体大一": "体育专业大一",
    "武术专业": "体育专业",
    ...
}
```

`scrub()` 还会自动处理本机绝对路径（`/Users/你的用户名/...` → 去掉），避免泄漏用户名。

**所以：源 `.md` 可以写真实情况，公开页面和副本会自动脱敏。** 但只替换字典里列出的词，新增敏感词要自己往里加。

另外，以下内容**没有**放进知识库（留在本地）：

- `发音反馈-01.md`（个人发音问题记录）
- `发布排期.md`（含播放数据、发布计划）
- `bili-morning/`（每日刷视频流水）
- `成片/`、`素材/`、`工具/`（视频素材和剪辑脚本）
- `大一这一年-体育学硕.html` 及 PDF（已在 .gitignore）

以后想加，按上面「第 2 步」登记即可。原始笔记会一直留在本地，只有脱敏副本进仓库。

---

## 七、常见问题

**Q：push 完打开网址是 404？**
等 1–2 分钟。GitHub Pages 构建有延迟。去仓库 **Actions** 标签页看 `pages-build-deployment` 是否跑完。

**Q：页面样式全丢了？**
检查 `wiki/assets/style.css` 有没有提交。`git status` 看一眼。

**Q：搜索没反应？**
用 `http://localhost:8080` 或线上地址访问。`file://` 双击打开时 fetch 会被浏览器拦截。

**Q：想换配色/字体？**
改 `build.py` 里的 `write_assets()` 函数，CSS 变量在最上面（`--bg`、`--accent` 等），改完重新构建。

**Q：以后想换成 Quartz / VitePress？**
现在的 `wiki-src/build.py` 只依赖 Python 标准库 + `markdown` 包，源笔记是纯 Markdown，随时可以迁移到别的生成器，内容不用重写。
