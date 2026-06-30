"""
热门话题采集服务
从各平台获取实时热搜/热门话题
"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional

# 缓存
_cache: Dict[str, tuple[List[Dict], float]] = {}
CACHE_TTL = 300  # 5分钟缓存


def _get_cache(key: str) -> Optional[List[Dict]]:
    """获取缓存，过期返回None"""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None


def _set_cache(key: str, data: List[Dict]):
    _cache[key] = (data, time.time())


def fetch_weibo_hot() -> List[Dict]:
    """
    获取微博实时热搜
    返回: [{"word": "话题", "num": 热度, "label_name": "标签", "rank": 排名}]
    """
    cached = _get_cache('weibo')
    if cached:
        return cached

    try:
        resp = requests.get(
            'https://weibo.com/ajax/side/hotSearch',
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://weibo.com',
                'Accept': 'application/json',
            },
            timeout=5
        )
        data = resp.json()
        if data.get('ok') != 1:
            return []

        realtime = data.get('data', {}).get('realtime', [])
        result = []
        for item in realtime[:20]:
            result.append({
                'word': item.get('word', ''),
                'num': item.get('num', 0),
                'label_name': item.get('label_name', ''),
                'rank': item.get('rank', 0),
                'category': item.get('category', ''),
                'url': f'https://s.weibo.com/weibo?q={requests.utils.quote(item.get("word", ""))}',
            })
        _set_cache('weibo', result)
        return result
    except Exception as e:
        print(f"[hot_topics] 微博热搜获取失败: {e}")
        return []


def fetch_douyin_hot() -> List[Dict]:
    """
    获取抖音热榜
    返回: [{"word": "话题", "hot_value": 热度, "label": "标签", "rank": 排名}]
    """
    cached = _get_cache('douyin')
    if cached:
        return cached

    try:
        resp = requests.get(
            'https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=PC web&count=20&keyword_type=0',
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.douyin.com',
                'Accept': 'application/json',
            },
            timeout=5
        )
        data = resp.json()
        if data.get('status_code') != 0:
            return []

        word_list = data.get('data', {}).get('word_list', [])
        result = []
        for item in word_list[:20]:
            result.append({
                'word': item.get('word', ''),
                'hot_value': item.get('hot_value', 0),
                'label': item.get('label', ''),
                'rank': item.get('rank', 0),
                'word_type': item.get('word_type', 0),
                'url': f'https://www.douyin.com/search/{requests.utils.quote(item.get("word", ""))}',
            })
        _set_cache('douyin', result)
        return result
    except Exception as e:
        print(f"[hot_topics] 抖音热榜获取失败: {e}")
        return []


def fetch_zhihu_hot() -> List[Dict]:
    """
    获取知乎热榜
    """
    cached = _get_cache('zhihu')
    if cached:
        return cached

    try:
        resp = requests.get(
            'https://www.zhihu.com/api/v4/hot-lists/total?limit=20',
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
            },
            timeout=5
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        items = data.get('data', [])
        result = []
        for item in items[:20]:
            target = item.get('target', {})
            result.append({
                'word': item.get('title', ''),
                'click': target.get('metrics', {}).get('click', 0),
                'like': target.get('metrics', {}).get('like', 0),
                'url': target.get('url', ''),
            })
        _set_cache('zhihu', result)
        return result
    except Exception as e:
        print(f"[hot_topics] 知乎热榜获取失败: {e}")
        return []


def get_all_hot_topics() -> Dict[str, List[Dict]]:
    """获取所有平台热门话题"""
    return {
        'weibo': fetch_weibo_hot(),
        'douyin': fetch_douyin_hot(),
        'zhihu': fetch_zhihu_hot(),
    }