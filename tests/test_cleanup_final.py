#!/usr/bin/env python3
"""
=============================================================================
HTML CLEANUP TEST SCRIPT für n8n Weekly Blog Feed Workflow
=============================================================================

ZWECK:
    Dieses Script testet die HTML-Cleanup-Funktion, die im n8n Workflow 
    "Weekly Blog Feed" verwendet wird. Es spiegelt exakt die JavaScript-
    Funktion im Node "Clean HTML Content" wider.

WORKFLOW-REFERENZ:
    - Datei: /Users/janneuber/Documents/Repos/n8n/workflows/Weekly Blog Feed.json
    - Node: "Clean HTML Content" (id: fallback-clean-html)
    - Position im Workflow: Nach "Fetch Page Content", vor "Page Summary Chain"

VERWENDUNG:
    python3 test_cleanup_final.py
    
    Testet automatisch alle 8 BC-Blog-Feeds und zeigt:
    - Original HTML-Größe
    - Bereinigte Text-Größe
    - Vorschau des extrahierten Contents

GETESTETE BLOGS:
    waldo.be, demiliani.com, hougaard.com, kauffmann.nl,
    yzhums.com, vjeko.com, mynavblog.com, katson.com

BEI ÄNDERUNGEN:
    1. Änderung hier im Python testen
    2. Bei Erfolg: JavaScript im Workflow anpassen (jsCode im Node)
    3. Workflow JSON speichern und in n8n neu importieren

LETZTE AKTUALISIERUNG: 2026-02-01
=============================================================================
"""
import urllib.request
import re

def cleanHtml(html):
    if not html:
        return ""
    
    content = None
    elementor_used = False
    
    # Strategie A: entry-content (WordPress)
    entry_match = re.search(r'<div[^>]*class="[^"]*\bentry-content\b[^"]*"[^>]*>([\s\S]+)', html, re.IGNORECASE)
    if entry_match:
        inner = entry_match.group(1)
        end_patterns = [
            r'<footer\b',
            r'<div[^>]*class="[^"]*\b(?:comments|comment-respond|related|share-buttons?|author-box|post-navigation|yarpp-related)\b',
            r'<section[^>]*class="[^"]*\b(?:comments|related)\b',
            r'<!--\s*[./]entry-content',
            r'</article\s*>',
            r'<div[^>]*id="comments"',
        ]
        end_pos = len(inner)
        for pat in end_patterns:
            m = re.search(pat, inner, re.IGNORECASE)
            if m and m.start() < end_pos and m.start() > 500:
                end_pos = m.start()
        if end_pos > 500:
            content = inner[:end_pos]
    
    # Strategie B: Elementor - Sammle ALLE widget-container (ZUERST, da vollständiger)
    if not content or len(content) < 500:
        elementor_blocks = []
        for match in re.finditer(r'<div class="elementor-widget-container">([\s\S]+?)</div>\s*</div>', html, re.IGNORECASE):
            block = match.group(1)
            if 'Leave a Reply' in block or 'Cancel reply' in block:
                continue
            if '<p' in block.lower() or '<h' in block.lower():
                text_only = re.sub(r'<[^>]+>', ' ', block)
                words = [w for w in text_only.split() if len(w) > 2]
                if len(words) > 15:
                    elementor_blocks.append(block)
        if len(elementor_blocks) >= 3:
            content = '\n\n'.join(elementor_blocks)
            elementor_used = True
    
    # Strategie B2: Elementor theme-post-content (Fallback für Video-Posts wie hougaard.com)
    if not content or len(content) < 100:
        theme_post = re.search(r'data-widget_type="theme-post-content[^"]*"[^>]*>\s*<div class="elementor-widget-container">([\s\S]+?)</div>\s*</div>', html, re.IGNORECASE)
        if theme_post and len(theme_post.group(1)) > 50:
            content = theme_post.group(1)
    
    # Strategien C-E nur wenn kein Elementor
    if not elementor_used:
        # Strategie C: article Tag
        if not content or len(content) < 500:
            article_match = re.search(r'<article[^>]*>([\s\S]+?)</article>', html, re.IGNORECASE)
            if article_match and len(article_match.group(1)) > (len(content) if content else 0):
                content = article_match.group(1)
        
        # Strategie D: post-content div
        if not content or len(content) < 500:
            post_match = re.search(r'<div[^>]*class="[^"]*\bpost-content\b[^"]*"[^>]*>([\s\S]+)', html, re.IGNORECASE)
            if post_match:
                inner = post_match.group(1)
                end_patterns = [r'<footer\b', r'</article\s*>', r'<div[^>]*class="[^"]*\bcomments\b']
                end_pos = min(len(inner), 50000)
                for pat in end_patterns:
                    m = re.search(pat, inner, re.IGNORECASE)
                    if m and m.start() < end_pos and m.start() > 500:
                        end_pos = m.start()
                if end_pos > (len(content) if content else 0):
                    content = inner[:end_pos]
        
        # Strategie E: main Tag
        if not content or len(content) < 500:
            main_match = re.search(r'<main[^>]*>([\s\S]+?)</main>', html, re.IGNORECASE)
            if main_match and len(main_match.group(1)) > (len(content) if content else 0):
                content = main_match.group(1)
    
    # Fallback: Body
    if not content or len(content) < 300:
        body_match = re.search(r'<body[^>]*>([\s\S]+?)</body>', html, re.IGNORECASE)
        content = body_match.group(1) if body_match else html
    
    # NOISE ENTFERNUNG
    noise_patterns = [
        r'<script[^>]*>[\s\S]*?</script>',
        r'<style[^>]*>[\s\S]*?</style>',
        r'<noscript[^>]*>[\s\S]*?</noscript>',
        r'<nav[^>]*>[\s\S]*?</nav>',
        r'<footer[^>]*>[\s\S]*?</footer>',
        r'<header[^>]*>[\s\S]*?</header>',
        r'<aside[^>]*>[\s\S]*?</aside>',
        r'<iframe[^>]*>[\s\S]*?</iframe>',
        r'<form[^>]*>[\s\S]*?</form>',
        r'<svg[^>]*>[\s\S]*?</svg>',
        r'<!--[\s\S]*?-->',
    ]
    for pattern in noise_patterns:
        content = re.sub(pattern, ' ', content, flags=re.IGNORECASE)
    
    # STRUKTUR IN TEXT
    content = re.sub(r'<h1[^>]*>([\s\S]*?)</h1>', r'\n\n# \1\n', content, flags=re.IGNORECASE)
    content = re.sub(r'<h2[^>]*>([\s\S]*?)</h2>', r'\n\n## \1\n', content, flags=re.IGNORECASE)
    content = re.sub(r'<h3[^>]*>([\s\S]*?)</h3>', r'\n\n### \1\n', content, flags=re.IGNORECASE)
    content = re.sub(r'</p>', '\n\n', content, flags=re.IGNORECASE)
    content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
    content = re.sub(r'<li[^>]*>', '\n• ', content, flags=re.IGNORECASE)
    
    # ALLE TAGS ENTFERNEN
    content = re.sub(r'<[^>]+>', ' ', content)
    
    # ENTITIES
    entities = {
        '&amp;': '&', '&lt;': '<', '&gt;': '>', 
        '&quot;': '"', '&#39;': "'", '&nbsp;': ' ',
        '&mdash;': '—', '&ndash;': '–', '&hellip;': '…',
    }
    for entity, char in entities.items():
        content = content.replace(entity, char)
    content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
    content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)
    
    # WHITESPACE CLEANUP
    content = re.sub(r'[ \t]+', ' ', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    
    # LIMIT
    if len(content) > 8000:
        content = content[:8000]
        last_period = content.rfind('. ')
        if last_period > 6000:
            content = content[:last_period + 1]
    
    return content


# TESTE ALLE FEEDS
feeds = [
    "https://waldo.be/feed/",
    "https://demiliani.com/feed/",
    "https://www.hougaard.com/feed/",
    "https://www.kauffmann.nl/feed/",
    "https://yzhums.com/feed/",
    "https://vjeko.com/feed/",
    "https://mynavblog.com/feed/",
    "https://www.katson.com/feed/"
]

results = []

for feed_url in feeds:
    try:
        req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as response:
            feed_xml = response.read().decode('utf-8', errors='ignore')
        
        item_match = re.search(r'<item>[\s\S]*?<link>([^<]+)</link>', feed_xml)
        if not item_match:
            item_match = re.search(r'<entry>[\s\S]*?<link[^>]*href="([^"]+)"', feed_xml)
        
        if item_match:
            article_url = item_match.group(1).strip()
            
            req2 = urllib.request.Request(article_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
            with urllib.request.urlopen(req2, timeout=15) as response2:
                html = response2.read().decode('utf-8', errors='ignore')
            
            cleaned = cleanHtml(html)
            domain = feed_url.split('/')[2].replace('www.', '')
            
            results.append({
                'domain': domain,
                'url': article_url,
                'original_len': len(html),
                'cleaned_len': len(cleaned),
                'preview': cleaned[:300].replace('\n', ' ')[:150]
            })
        else:
            domain = feed_url.split('/')[2].replace('www.', '')
            results.append({'domain': domain, 'error': 'Kein Artikel-Link gefunden'})
            
    except Exception as e:
        domain = feed_url.split('/')[2].replace('www.', '')
        results.append({'domain': domain, 'error': str(e)})

# Ausgabe
print("\n" + "=" * 70)
print("HTML CLEANUP TEST - FINALE VERSION")
print("=" * 70 + "\n")

good = 0
for r in results:
    if 'error' in r:
        print(f"❌ {r['domain']}: {r['error']}")
    else:
        ok = r['cleaned_len'] >= 500
        if ok:
            good += 1
        status = "✅" if r['cleaned_len'] >= 1000 else ("⚠️" if r['cleaned_len'] >= 500 else "❌")
        print(f"{status} {r['domain']}")
        print(f"   Original: {r['original_len']:,} → Cleaned: {r['cleaned_len']:,} Zeichen")
        print(f"   Preview: {r['preview']}...")
        print()

print("=" * 70)
print(f"Ergebnis: {good}/{len(results)} Blogs liefern ausreichend Content (≥500 Zeichen)")
print("=" * 70)
