# -*- coding: utf-8 -*-
"""
鹭见 SiteSight · 反馈记忆 Agent（赛道 4 核心模块）

用途：用户在看完 AI 场地分析报告后给出偏好反馈（例如“以后报告要突出坡度分析”），
系统把偏好沉淀为记忆，并在后续相似报告生成时自动检索、注入提示词。

实现：纯 Python 标准库 + 本地 JSON 记忆库，零外部依赖。
"""

import json
import os
import time
import uuid

# 默认记忆存储位置（可用环境变量 SITESIGHT_MEMORY 覆盖）
DEFAULT_MEMORY_PATH = os.path.join(
    os.path.expanduser("~"), "SiteSight", "memory.json"
)

# 报告主题关键词表：用于给记忆打标签、判断与当前任务的相关性
TOPIC_KEYWORDS = {
    "坡度": ["坡度", "坡向", "slope"],
    "高差": ["高差", "高程", "地形", "elevation", "高度"],
    "面积": ["面积", "范围", "规模", "area"],
    "建设": ["建设", "布局", "适宜", "建筑", "规划", "分区", "选址"],
    "水系": ["水", "河流", "排水", "汇水", "洪"],
    "道路": ["道路", "交通", "路网", "可达"],
    "植被": ["植被", "树", "绿化", "生态"],
    "报告风格": ["报告", "格式", "简洁", "详细", "表格", "专业"],
    "导出": ["导出", "skp", "stl", "3dm", "格式"],
}


def _memory_path(path=None):
    return path or os.environ.get("SITESIGHT_MEMORY") or DEFAULT_MEMORY_PATH


def _load_memories(path=None):
    fp = _memory_path(path)
    if not os.path.isfile(fp):
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f).get("memories", [])
    except Exception:
        return []


def _save_memories(memories, path=None):
    fp = _memory_path(path)
    try:
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump({"memories": memories}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("记忆保存失败：", e)


def _extract_tags(text):
    tags = []
    low = (text or "").lower()
    for topic, words in TOPIC_KEYWORDS.items():
        if any(w.lower() in low for w in words):
            tags.append(topic)
    return tags


def add_feedback(text, path=None):
    """把一条用户反馈沉淀为记忆，返回记忆对象。"""
    text = (text or "").strip()
    if len(text) < 2:
        raise ValueError("反馈内容太短，请至少输入 2 个字")
    memories = _load_memories(path)
    # 已存在相同反馈时不重复沉淀，控制记忆成本（赛道 4 考查点）
    for m in memories:
        if (m.get("text") or "").strip() == text:
            return m
    mem = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "tags": _extract_tags(text),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "used_count": 0,
    }
    memories.append(mem)
    _save_memories(memories, path)
    return mem


def list_memories(path=None):
    """返回全部记忆（按创建时间倒序）。"""
    mems = _load_memories(path)
    return sorted(mems, key=lambda m: m.get("created_at", ""), reverse=True)


def delete_memory(mem_id, path=None):
    """删除一条记忆。"""
    memories = _load_memories(path)
    left = [m for m in memories if m.get("id") != mem_id]
    if len(left) != len(memories):
        _save_memories(left, path)
        return True
    return False


def get_relevant_memories(context_text="", path=None, max_items=5):
    """
    按主题关键词检索与当前报告最相关的记忆，供提示词注入。
    返回记忆列表，并累加 used_count（用于后续排序）。
    """
    memories = _load_memories(path)
    if not memories:
        return []
    ctx = (context_text or "").lower()
    scored = []
    for m in memories:
        score = 0
        # 记忆标签与本次报告上下文重叠越多越相关
        for t in m.get("tags", []):
            if t.lower() in ctx:
                score += 3
        # 记忆自身主题越丰富，优先级越高
        score += min(len(m.get("tags", [])), 3)
        scored.append((score, m))
    scored.sort(key=lambda x: (-x[0], -x[1].get("used_count", 0)))
    picked = [m for s, m in scored[:max_items] if s > 0]
    for m in picked:
        m["used_count"] = m.get("used_count", 0) + 1
    if picked:
        _save_memories(memories, path)
    return picked


def memory_block(memories):
    """把记忆列表拼成提示词里的『用户长期偏好』段落。"""
    if not memories:
        return ""
    lines = ["## 用户长期偏好（来自历史反馈，本次生成必须遵守）"]
    for m in memories:
        lines.append("- " + m["text"])
    return "\n".join(lines)
