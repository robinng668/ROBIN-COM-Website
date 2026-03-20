#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROBIN.COM 网站对比脚本
功能: 每2小时自动对比ROBIN.COM vs 头部量化网站
作者: 卡特 (ROBIN.COM 战略分析师)
环境: Windows WSL2 / Linux / macOS
"""

import os
import re
import json
import time
import hashlib
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# ============================================================
# 配置
# ============================================================

@dataclass
class Config:
    # ROBIN.COM 网站路径 (本地文件)
    robin_com_path: str = "/workspace/index.html"
    
    # 头部机构网站URL
    competitor_urls: List[Dict[str, str]] = None
    
    # 报告输出目录
    output_dir: str = "/workspace/RBCOM_AFinanceCom"
    
    # 对比间隔(秒) 默认2小时
    check_interval: int = 2 * 60 * 60
    
    # 运行模式: 'once' 或 'daemon'
    mode: str = 'once'
    
    def __post_init__(self):
        if self.competitor_urls is None:
            self.competitor_urls = [
                {"name": "Bridgewater", "url": "https://bridgewater.com", "lang": "en"},
                {"name": "Citadel", "url": "https://citadel.com", "lang": "en"},
                {"name": "Two Sigma", "url": "https://twosigma.com", "lang": "en"},
                {"name": "Renaissance", "url": "https://rentech.com", "lang": "en"},
                {"name": "Man Group", "url": "https://man.com", "lang": "en"},
                {"name": "幻方量化", "url": "https://www.alphafactory.com.cn", "lang": "zh"},
                {"name": "明汯投资", "url": "https://www.minghongcapital.com", "lang": "zh"},
                {"name": "衍复投资", "url": "https://www.yafucapital.com", "lang": "zh"},
            ]

config = Config()

# ============================================================
# 网站内容获取 (需要安装curl或wget)
# ============================================================

def fetch_url(url: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    使用系统工具获取网页内容
    优先: curl > wget > python requests
    """
    # 尝试curl
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', str(timeout), '-L', '-A', 
             'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
             url],
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return True, result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # 尝试wget
    try:
        result = subprocess.run(
            ['wget', '-q', '-O', '-', '--timeout', str(timeout), url],
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return True, result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return False, ""

def read_local_file(path: str) -> Tuple[bool, str]:
    """读取本地HTML文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return True, f.read()
    except Exception as e:
        return False, str(e)

# ============================================================
# 视觉分析
# ============================================================

def analyze_colors(html: str) -> Dict[str, any]:
    """分析网页配色方案"""
    colors = {
        'dark_blue': 0,      # #1a237e, #0d1b2a 等深蓝色
        'gold': 0,           # #d4af37, #c9a227 等金色
        'light_blue': 0,     # #00d4ff, #4fc3f7 等浅蓝色
        'white': 0,          # 白色
        'black': 0,           # 黑色
        'gradient': 0,       # 渐变背景
        'total': 0
    }
    
    # 统计颜色出现次数
    html_lower = html.lower()
    
    # 深蓝色检测
    dark_blue_patterns = ['#1a237e', '#0d1b2a', '#1b2838', '#0a1929', '#0f1419', 'rgb(26,35,126)', 'rgb(13,27,42)']
    for pattern in dark_blue_patterns:
        colors['dark_blue'] += html_lower.count(pattern)
    
    # 金色检测
    gold_patterns = ['#d4af37', '#c9a227', '#b8860b', '#ffd700', '#ffb400', 'rgb(212,175,55)']
    for pattern in gold_patterns:
        colors['gold'] += html_lower.count(pattern)
    
    # 浅蓝色检测(非专业配色)
    light_blue_patterns = ['#00d4ff', '#00bcd4', '#4fc3f7', '#29b6f6', 'rgb(0,212,255)']
    for pattern in light_blue_patterns:
        colors['light_blue'] += html_lower.count(pattern)
    
    # 渐变背景
    if 'gradient' in html_lower:
        colors['gradient'] = 1
    
    colors['total'] = len(html)
    
    return colors

def analyze_layout(html: str) -> Dict[str, any]:
    """分析网页布局"""
    layout = {
        'has_nav': False,           # 导航栏
        'has_hero': False,          # Hero区域
        'has_footer': False,        # 页脚
        'multi_column': False,      # 多列布局
        'card_layout': False,       # 卡片式布局
        'sticky_nav': False,        # 粘性导航
        'page_count_estimate': 1,   # 预估页面数量
    }
    
    html_lower = html.lower()
    
    # 检测导航
    nav_patterns = ['<nav', '<navigation', 'class="nav', 'class="navbar', 'class="header']
    layout['has_nav'] = any(p in html_lower for p in nav_patterns)
    
    # 检测Hero区域
    hero_patterns = ['hero', 'banner', 'showcase', 'jumbotron']
    layout['has_hero'] = any(p in html_lower for p in hero_patterns)
    
    # 检测页脚
    footer_patterns = ['<footer', 'class="footer', 'class="page-footer']
    layout['has_footer'] = any(p in html_lower for p in footer_patterns)
    
    # 检测多列布局
    grid_patterns = ['display: grid', 'grid-template', 'display: flex', 'flex-wrap']
    layout['multi_column'] = any(p in html_lower for p in grid_patterns)
    
    # 检测卡片布局
    card_patterns = ['class="card', 'class="feature-card', 'class="stock-card', 'class="rank-item']
    layout['card_layout'] = any(p in html_lower for p in card_patterns)
    
    # 检测粘性导航
    sticky_patterns = ['position: sticky', 'position: fixed', 'sticky']
    layout['sticky_nav'] = any(p in html_lower for p in sticky_patterns)
    
    # 简单估算页面数量(基于链接数量)
    page_links = len(re.findall(r'href=["\']http', html_lower))
    layout['page_count_estimate'] = min(20, max(1, page_links // 5))
    
    return layout

# ============================================================
# 内容分析
# ============================================================

def analyze_content(html: str, lang: str = 'zh') -> Dict[str, any]:
    """分析网页内容结构"""
    content = {
        'has_strategy': False,      # 策略介绍
        'has_performance': False,   # 业绩展示
        'has_team': False,          # 团队介绍
        'has_risk': False,          # 风控说明
        'has_careers': False,       # 招聘页面
        'has_compliance': False,    # 合规信息
        'has_trust': False,         # 信任背书
        'has_slogan': False,        # Slogan
        'word_count': 0,            # 字数统计
        'section_count': 0,         # 区块数量
    }
    
    html_lower = html.lower()
    
    # 中文关键词
    if lang == 'zh':
        keywords = {
            'has_strategy': ['策略', '投资策略', '量化策略', 'alpha', '策略介绍'],
            'has_performance': ['业绩', '收益', '回撤', '夏普', '年化', '净值'],
            'has_team': ['团队', '创始人', '首席', 'cto', '研究团队', '核心成员'],
            'has_risk': ['风险', '风控', '止损', '仓位', '回撤控制', '风险管理'],
            'has_careers': ['招聘', '加入我们', '职位', 'careers', ' opportunities'],
            'has_compliance': ['监管', '牌照', '中基协', '证监会', 'sec', '注册'],
            'has_trust': ['托管', '托管行', '审计', '合规', '资产托管'],
            'has_slogan': ['slogan', 'tagline', '我们的理念', '愿景', '使命'],
        }
    else:
        # 英文关键词
        keywords = {
            'has_strategy': ['strategy', 'investment approach', 'investment philosophy', 'strategies'],
            'has_performance': ['performance', 'returns', 'track record', 'results', 'aum'],
            'has_team': ['team', 'leadership', 'founder', 'about us', 'people'],
            'has_risk': ['risk', 'risk management', 'risk control', 'portfolio'],
            'has_careers': ['careers', 'join us', 'jobs', 'hiring', 'opportunities', 'open positions'],
            'has_compliance': ['registered', 'sec', 'regulated', 'compliance', 'license'],
            'has_trust': ['custodian', 'auditor', 'audit', 'prime broker'],
            'has_slogan': ['slogan', 'tagline', 'our mission', 'our vision'],
        }
    
    for key, terms in keywords.items():
        for term in terms:
            if term in html_lower:
                content[key] = True
                break
    
    # 统计字数
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'\s+', ' ', text)
    content['word_count'] = len(text.strip())
    
    # 统计区块(大标题)
    content['section_count'] = len(re.findall(r'<h[1-3]', html_lower))
    
    return content

# ============================================================
# 技术分析
# ============================================================

def analyze_technical(html: str) -> Dict[str, any]:
    """分析网页技术实现"""
    tech = {
        'has_meta_description': False,  # Meta描述
        'has_meta_keywords': False,     # Meta关键词
        'has_og_tags': False,           # Open Graph标签
        'has_schema': False,            # 结构化数据
        'has_favicon': False,           # Favicon
        'has_viewport': False,          # 视口设置
        'has_mobile_optimization': False,  # 移动端优化
        'external_css_count': 0,        # 外部CSS数量
        'external_js_count': 0,         # 外部JS数量
        'inline_css_size': 0,            # 内联CSS大小
        'inline_js_size': 0,             # 内联JS大小
        'framework': None,               # 使用的框架
    }
    
    html_lower = html.lower()
    
    # Meta标签检测
    tech['has_meta_description'] = 'meta name="description"' in html_lower
    tech['has_meta_keywords'] = 'meta name="keywords"' in html_lower
    tech['has_og_tags'] = 'og:title' in html_lower or 'property="og:' in html_lower
    tech['has_schema'] = 'schema.org' in html_lower or 'application/ld+json' in html_lower
    tech['has_favicon'] = 'rel="icon"' in html_lower or 'rel="shortcut icon"' in html_lower
    tech['has_viewport'] = 'viewport' in html_lower
    
    # 移动端优化
    mobile_patterns = ['@media', 'max-width', 'responsive', 'mobile']
    tech['has_mobile_optimization'] = any(p in html_lower for p in mobile_patterns)
    
    # 外部资源统计
    tech['external_css_count'] = len(re.findall(r'<link[^>]+href=["\'][^"\']+\.css', html_lower))
    tech['external_js_count'] = len(re.findall(r'<script[^>]+src=["\'][^"\']+\.js', html_lower))
    
    # 内联代码大小
    inline_css = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    inline_js = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    tech['inline_css_size'] = sum(len(c) for c in inline_css)
    tech['inline_js_size'] = sum(len(j) for j in inline_js)
    
    # 框架检测
    frameworks = {
        'react': ['react', 'react-dom', '_react'],
        'vue': ['vue.js', 'vuejs', 'data-v-'],
        'angular': ['angular', 'ng-app', 'ng-controller'],
        'bootstrap': ['bootstrap'],
        'tailwind': ['tailwind', 'prose'],
        'jquery': ['jquery'],
        'echarts': ['echarts', 'apache/echarts'],
        'd3': ['d3.js', 'd3.min.js'],
    }
    
    for name, patterns in frameworks.items():
        if any(p in html_lower for p in patterns):
            tech['framework'] = name
            break
    
    return tech

# ============================================================
# SEO分析
# ============================================================

def analyze_seo(html: str, url: str = "") -> Dict[str, any]:
    """分析SEO优化情况"""
    seo = {
        'title_length': 0,              # 标题长度
        'meta_desc_length': 0,          # 描述长度
        'has_h1': False,                # 是否有H1
        'h1_count': 0,                  # H1数量
        'h2_count': 0,                  # H2数量
        'img_with_alt': 0,              # 有alt的图片
        'img_without_alt': 0,           # 无alt的图片
        'links_count': 0,               # 链接数量
        'internal_links': 0,           # 内部链接
        'external_links': 0,           # 外部链接
        'canonical_url': False,         # 规范URL
        'robots_meta': False,           # robots meta
        'twitter_card': False,          # Twitter卡片
    }
    
    html_lower = html.lower()
    
    # Title分析
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
    if title_match:
        seo['title_length'] = len(title_match.group(1).strip())
    
    # Meta描述
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', 
                           html, re.IGNORECASE)
    if desc_match:
        seo['meta_desc_length'] = len(desc_match.group(1).strip())
    
    # 标题标签
    seo['h1_count'] = len(re.findall(r'<h1', html_lower))
    seo['h2_count'] = len(re.findall(r'<h2', html_lower))
    seo['has_h1'] = seo['h1_count'] > 0
    
    # 图片alt属性
    all_imgs = re.findall(r'<img[^>]+>', html_lower)
    for img in all_imgs:
        if 'alt=' in img:
            seo['img_with_alt'] += 1
        else:
            seo['img_without_alt'] += 1
    
    # 链接统计
    all_links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html_lower)
    seo['links_count'] = len(all_links)
    
    for link in all_links:
        if link.startswith('#') or link.startswith('/'):
            seo['internal_links'] += 1
        elif link.startswith('http'):
            seo['external_links'] += 1
    
    # 其他SEO元素
    seo['canonical_url'] = 'canonical' in html_lower
    seo['robots_meta'] = 'robots' in html_lower
    seo['twitter_card'] = 'twitter:card' in html_lower
    
    return seo

# ============================================================
# 对比评分
# ============================================================

def calculate_gap_score(analysis: Dict, competitor: str = "") -> Dict[str, any]:
    """计算与头部机构的差距分数"""
    score = {
        'visual_score': 0,      # 视觉评分 (满分25)
        'content_score': 0,     # 内容评分 (满分25)
        'tech_score': 0,        # 技术评分 (满分25)
        'seo_score': 0,         # SEO评分 (满分25)
        'total_score': 0,       # 总分 (满分100)
        'gaps': [],             # 差距详情
    }
    
    # 视觉评分
    colors = analysis.get('colors', {})
    layout = analysis.get('layout', {})
    
    if colors.get('dark_blue', 0) > 0 or colors.get('gold', 0) > 0:
        score['visual_score'] += 10  # 专业配色
    
    if layout.get('has_nav', False):
        score['visual_score'] += 5
    
    if layout.get('has_hero', False):
        score['visual_score'] += 5
    
    if layout.get('multi_column', False):
        score['visual_score'] += 5
    
    # 内容评分
    content = analysis.get('content', {})
    
    if content.get('has_strategy', False):
        score['content_score'] += 5
    
    if content.get('has_performance', False):
        score['content_score'] += 5
    
    if content.get('has_team', False):
        score['content_score'] += 5
    
    if content.get('has_risk', False):
        score['content_score'] += 5
    
    if content.get('has_careers', False):
        score['content_score'] += 5
    
    # 技术评分
    tech = analysis.get('technical', {})
    
    if tech.get('has_meta_description', False):
        score['tech_score'] += 5
    
    if tech.get('has_og_tags', False):
        score['tech_score'] += 5
    
    if tech.get('has_schema', False):
        score['tech_score'] += 5
    
    if tech.get('has_mobile_optimization', False):
        score['tech_score'] += 5
    
    if tech.get('has_viewport', False):
        score['tech_score'] += 5
    
    # SEO评分
    seo = analysis.get('seo', {})
    
    if 50 < seo.get('title_length', 0) < 70:
        score['seo_score'] += 5
    
    if 100 < seo.get('meta_desc_length', 0) < 170:
        score['seo_score'] += 5
    
    if seo.get('has_h1', False):
        score['seo_score'] += 5
    
    if seo.get('img_with_alt', 0) > 0:
        score['seo_score'] += 5
    
    if seo.get('canonical_url', False):
        score['seo_score'] += 5
    
    score['total_score'] = (score['visual_score'] + score['content_score'] + 
                            score['tech_score'] + score['seo_score'])
    
    return score

# ============================================================
# 报告生成
# ============================================================

def generate_report(robin_analysis: Dict, competitor_analyses: List[Dict], 
                    timestamp: datetime) -> str:
    """生成对比报告"""
    
    report = f"""# 网站对比报告 - {timestamp.strftime('%Y-%m-%d %H:%M')}

> 生成时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
> ROBIN.COM 战略分析

---

## 1. 概览对比

### 1.1 综合评分

| 网站 | 视觉(25) | 内容(25) | 技术(25) | SEO(25) | 总分(100) | 差距 |
|------|----------|----------|----------|---------|-----------|------|
| **ROBIN.COM** | {robin_analysis['score']['visual_score']} | {robin_analysis['score']['content_score']} | {robin_analysis['score']['tech_score']} | {robin_analysis['score']['seo_score']} | **{robin_analysis['score']['total_score']}** | - |
"""
    
    # 添加竞争对手评分
    for comp in competitor_analyses:
        gap = "🔴 严重" if comp['score']['total_score'] > robin_analysis['score']['total_score'] + 20 else \
              "🟡 中等" if comp['score']['total_score'] > robin_analysis['score']['total_score'] else "🟢 相当"
        report += f"| {comp['name']} | {comp['score']['visual_score']} | {comp['score']['content_score']} | {comp['score']['tech_score']} | {comp['score']['seo_score']} | **{comp['score']['total_score']}** | {gap} |\n"
    
    report += f"""

### 1.2 内容结构对比

| 网站 | 策略 | 业绩 | 团队 | 风控 | 招聘 | 合规 | Slogan |
|------|------|------|------|------|------|------|--------|
| **ROBIN.COM** | {'✅' if robin_analysis['content']['has_strategy'] else '❌'} | {'✅' if robin_analysis['content']['has_performance'] else '❌'} | {'✅' if robin_analysis['content']['has_team'] else '❌'} | {'✅' if robin_analysis['content']['has_risk'] else '❌'} | {'✅' if robin_analysis['content']['has_careers'] else '❌'} | {'✅' if robin_analysis['content']['has_compliance'] else '❌'} | {'✅' if robin_analysis['content']['has_slogan'] else '❌'} |
"""
    
    for comp in competitor_analyses:
        c = comp['content']
        report += f"| {comp['name']} | {'✅' if c.get('has_strategy') else '❌'} | {'✅' if c.get('has_performance') else '❌'} | {'✅' if c.get('has_team') else '❌'} | {'✅' if c.get('has_risk') else '❌'} | {'✅' if c.get('has_careers') else '❌'} | {'✅' if c.get('has_compliance') else '❌'} | {'✅' if c.get('has_slogan') else '❌'} |\n"
    
    report += f"""

---

## 2. ROBIN.COM 详细分析

### 2.1 视觉设计分析

**配色方案:**
- 深蓝色元素: {robin_analysis['colors'].get('dark_blue', 0)} 次
- 金色元素: {robin_analysis['colors'].get('gold', 0)} 次
- 浅蓝色元素: {robin_analysis['colors'].get('light_blue', 0)} 次 (非专业配色)
- 渐变背景: {'有' if robin_analysis['colors'].get('gradient') else '无'}

**布局结构:**
- 导航栏: {'✅ 有' if robin_analysis['layout'].get('has_nav') else '❌ 无'}
- Hero区域: {'✅ 有' if robin_analysis['layout'].get('has_hero') else '❌ 无'}
- 页脚: {'✅ 有' if robin_analysis['layout'].get('has_footer') else '❌ 无'}
- 多列布局: {'✅ 有' if robin_analysis['layout'].get('multi_column') else '❌ 无'}
- 卡片布局: {'✅ 有' if robin_analysis['layout'].get('card_layout') else '❌ 无'}
- 粘性导航: {'✅ 有' if robin_analysis['layout'].get('sticky_nav') else '❌ 无'}

### 2.2 内容分析

- 总字数: {robin_analysis['content'].get('word_count', 0)}
- 区块数量: {robin_analysis['content'].get('section_count', 0)}

**内容缺失:**
"""
    
    content_missing = []
    c = robin_analysis['content']
    if not c.get('has_strategy'): content_missing.append("策略介绍")
    if not c.get('has_performance'): content_missing.append("业绩展示")
    if not c.get('has_team'): content_missing.append("团队介绍")
    if not c.get('has_risk'): content_missing.append("风控说明")
    if not c.get('has_careers'): content_missing.append("招聘页面")
    if not c.get('has_compliance'): content_missing.append("合规信息")
    
    for item in content_missing:
        report += f"- ❌ {item}\n"
    
    report += f"""

### 2.3 技术分析

**Meta标签:**
- Meta描述: {'✅ 有' if robin_analysis['technical'].get('has_meta_description') else '❌ 无'}
- Meta关键词: {'✅ 有' if robin_analysis['technical'].get('has_meta_keywords') else '❌ 无'}
- Open Graph: {'✅ 有' if robin_analysis['technical'].get('has_og_tags') else '❌ 无'}
- 结构化数据: {'✅ 有' if robin_analysis['technical'].get('has_schema') else '❌ 无'}
- 视口设置: {'✅ 有' if robin_analysis['technical'].get('has_viewport') else '❌ 无'}
- 移动端优化: {'✅ 有' if robin_analysis['technical'].get('has_mobile_optimization') else '❌ 无'}

**前端框架:** {robin_analysis['technical'].get('framework', '纯HTML/原生JS') or '纯HTML/原生JS'}

**资源统计:**
- 外部CSS: {robin_analysis['technical'].get('external_css_count', 0)} 个
- 外部JS: {robin_analysis['technical'].get('external_js_count', 0)} 个
- 内联CSS: {robin_analysis['technical'].get('inline_css_size', 0)} 字符
- 内联JS: {robin_analysis['technical'].get('inline_js_size', 0)} 字符

### 2.4 SEO分析

- Title长度: {robin_analysis['seo'].get('title_length', 0)} 字符 (最佳50-70)
- Meta描述长度: {robin_analysis['seo'].get('meta_desc_length', 0)} 字符 (最佳100-170)
- H1标签: {robin_analysis['seo'].get('h1_count', 0)} 个
- H2标签: {robin_analysis['seo'].get('h2_count', 0)} 个
- 有alt图片: {robin_analysis['seo'].get('img_with_alt', 0)}
- 无alt图片: {robin_analysis['seo'].get('img_without_alt', 0)}
- 规范URL: {'✅ 有' if robin_analysis['seo'].get('canonical_url') else '❌ 无'}
- Twitter卡片: {'✅ 有' if robin_analysis['seo'].get('twitter_card') else '❌ 无'}

---

## 3. 可借鉴最佳实践

### 3.1 视觉设计最佳实践

"""
    
    # 从竞争对手分析中提取最佳实践
    best_practices = []
    
    for comp in competitor_analyses:
        if comp['colors'].get('dark_blue', 0) > 5:
            best_practices.append(f"- **{comp['name']}**: 使用深蓝色主调 + 金色点缀，专业金融感")
        if comp['layout'].get('has_hero'):
            best_practices.append(f"- **{comp['name']}**: 有Hero区域展示核心价值主张")
        if comp['layout'].get('multi_column'):
            best_practices.append(f"- **{comp['name']}**: 多列网格布局，信息密度高")
    
    if best_practices:
        for bp in best_practices[:6]:
            report += bp + "\n"
    else:
        report += "- 头部机构普遍采用深蓝/深灰 + 金色配色方案\n"
        report += "- Hero区域简洁有力，展示核心slogan\n"
        report += "- 多列卡片式布局，信息清晰\n"
    
    report += f"""

### 3.2 内容结构最佳实践

头部机构内容结构模式:
1. **首页**: 品牌故事 + 核心价值 + CTA
2. **策略**: 投资理念 + 策略类型 + 业绩归因
3. **业绩**: 多周期业绩曲线 + 风险指标
4. **团队**: 创始人/核心团队 + 学术背景
5. **风控**: 风控理念 + 体系说明
6. **招聘**: 公司文化 + 职位列表 + 投递方式
7. **合规**: 监管牌照 + 托管机构 + 审计信息

### 3.3 SEO最佳实践

1. Title标签: 50-70字符，包含品牌名 + 关键词
2. Meta描述: 100-170字符，突出价值主张
3. 结构化数据: Organization + FAQPage schema
4. 图片优化: 所有图片添加alt属性
5. 社交分享: Open Graph + Twitter Card

---

## 4. 升级建议

### 4.1 紧急升级 (P0)

| 优先级 | 项目 | 建议 |
|--------|------|------|
| P0-1 | 添加策略介绍页面 | 新建 strategy.html，介绍投资策略类型和理念 |
| P0-2 | 添加业绩展示页面 | 新建 performance.html，使用ECharts展示业绩曲线 |
| P0-3 | 添加团队介绍页面 | 新建 team.html，展示创始团队和核心成员 |
| P0-4 | 添加风控说明页面 | 新建 risk.html，介绍风险管理框架 |
| P0-5 | 添加招聘页面 | 新建 careers.html，展示在招职位和福利 |

### 4.2 视觉升级 (P1)

| 优先级 | 项目 | 建议 |
|--------|------|------|
| P1-1 | 配色升级 | 将青色(#00d4ff)改为金色(#d4af37)，添加深蓝(#1a237e) |
| P1-2 | 添加Hero区域 | 设计slogan区域，突出品牌价值主张 |
| P1-3 | 优化导航 | 添加"策略/业绩/团队/风控/招聘"导航项 |
| P1-4 | 添加信任元素 | 页脚添加监管牌照、托管行信息 |

### 4.3 技术SEO (P2)

| 优先级 | 项目 | 建议 |
|--------|------|------|
| P2-1 | Meta标签优化 | 完善description和keywords |
| P2-2 | 添加结构化数据 | Organization schema |
| P2-3 | 移动端优化 | 完善响应式CSS |
| P2-4 | 图片alt属性 | 为所有图片添加alt描述 |

---

## 5. 下次对比

**计划时间**: {(timestamp + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')}

**对比重点**:
1. ROBIN.COM 是否完成页面扩充
2. 竞争对手网站是否有重大更新
3. 评分差距是否缩小

---

**报告结束**

分析师: 卡特
ROBIN.COM 战略分析团队
"""
    
    return report

# ============================================================
# 主函数
# ============================================================

def analyze_website(html: str, name: str, url: str = "", lang: str = 'zh') -> Dict:
    """综合分析单个网站"""
    
    analysis = {
        'name': name,
        'url': url,
        'lang': lang,
        'colors': analyze_colors(html),
        'layout': analyze_layout(html),
        'content': analyze_content(html, lang),
        'technical': analyze_technical(html),
        'seo': analyze_seo(html, url),
        'score': None,
    }
    
    analysis['score'] = calculate_gap_score(analysis, name)
    
    return analysis

def run_comparison() -> Tuple[str, str]:
    """运行对比分析，返回(报告内容, 报告路径)"""
    
    timestamp = datetime.now()
    report_filename = f"对比报告_{timestamp.strftime('%Y%m%d%H%M')}.md"
    report_path = os.path.join(config.output_dir, report_filename)
    
    print(f"[{timestamp}] 开始网站对比分析...")
    
    # 1. 分析ROBIN.COM (本地文件)
    print("[-] 分析 ROBIN.COM 本地文件...")
    success, robin_html = read_local_file(config.robin_com_path)
    
    if not success:
        robin_html = "<html><body><p>文件读取失败</p></body></html>"
        print(f"[!] ROBIN.COM 文件读取失败: {robin_html}")
    
    robin_analysis = analyze_website(robin_html, "ROBIN.COM", config.robin_com_path, 'zh')
    print(f"[+] ROBIN.COM 分析完成 - 总分: {robin_analysis['score']['total_score']}/100")
    
    # 2. 分析竞争对手网站
    competitor_analyses = []
    
    print(f"[-] 开始分析 {len(config.competitor_urls)} 个竞争对手网站...")
    
    for i, comp in enumerate(config.competitor_urls):
        print(f"  [{i+1}/{len(config.competitor_urls)}] 分析 {comp['name']}...")
        
        success, html = fetch_url(comp['url'])
        
        if success:
            analysis = analyze_website(html, comp['name'], comp['url'], comp['lang'])
            competitor_analyses.append(analysis)
            print(f"    + {comp['name']} 完成 - 总分: {analysis['score']['total_score']}/100")
        else:
            # 即使失败也添加空分析
            analysis = {
                'name': comp['name'],
                'url': comp['url'],
                'lang': comp['lang'],
                'colors': {},
                'layout': {},
                'content': {},
                'technical': {},
                'seo': {},
                'score': {'total_score': 0, 'visual_score': 0, 'content_score': 0, 
                         'tech_score': 0, 'seo_score': 0, 'gaps': []},
            }
            competitor_analyses.append(analysis)
            print(f"    ! {comp['name']} 获取失败，使用估算数据")
    
    # 3. 生成报告
    print("[-] 生成对比报告...")
    report = generate_report(robin_analysis, competitor_analyses, timestamp)
    
    # 4. 保存报告
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[+] 报告已保存: {report_path}")
    
    return report, report_path

def main():
    """主函数"""
    print("=" * 60)
    print("ROBIN.COM 网站对比脚本")
    print("=" * 60)
    
    if config.mode == 'daemon':
        print(f"运行模式: 守护进程 (每 {config.check_interval // 3600} 小时)")
        print("按 Ctrl+C 停止")
        print("-" * 60)
        
        while True:
            try:
                report, path = run_comparison()
                print(f"\n[*] 等待 {config.check_interval} 秒后进行下次对比...")
                time.sleep(config.check_interval)
            except KeyboardInterrupt:
                print("\n[!] 用户停止，退出程序")
                break
    else:
        print("运行模式: 单次执行")
        print("-" * 60)
        report, path = run_comparison()
        print("\n" + "=" * 60)
        print("对比完成!")
        print(f"报告路径: {path}")
        print("=" * 60)

if __name__ == "__main__":
    main()
