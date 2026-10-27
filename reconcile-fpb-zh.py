#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
free-programming-books-zh 书单 ↔ 语雀实际库 对账 + 未导入清单编号
判定"已导入"的双源：
  1. last-imported.json 账本（URL 归一化 + 换源/变体映射）
  2. 语雀账号全量库名（精确匹配）——可查 10-15 等未记账批次（Git 系列等）
用法:
    python3 reconcile-fpb-zh.py <书单markdown文件> [--json <last-imported.json>] [--out <输出txt>] [--repos <全量库json>]

已知假阳性（2026-10-26/27 实捶）:
    title-starts 误命中：书名带「前端代码规范」的条目 #117 会命中同名前缀的 Isobar 规范库
    （#34 所建）→ recon 多算 1；对账报告里若剩 1 条存疑，先按 name-starts 人工复核。
"""
import json, os, re, sys

def norm(u: str) -> str:
    """归一化 URL：剥 web.archive 包装/协议/www/锚点/尾斜杠/github blob-tree 路径"""
    u = u.strip().rstrip(')').rstrip('）')
    m = re.match(r'^https?://web\.archive\.org/web/\d+/(.+)$', u)
    if m:
        u = m.group(1)
    u = u.split('#')[0]
    u = re.sub(r'^https?://', '', u)
    u = re.sub(r'^www\.', '', u)
    u = u.rstrip('/')
    m = re.match(r'^github\.com/([^/]+/[^/]+?)(?:/(blob|tree))?(?:/.*)?$', u)
    if m:
        u = 'github.com/' + m.group(1)
    return u.lower()

def norm_title(s: str, cut_dash: bool = True) -> str:
    """标题规范化：去括号（版本/作者）；cut_dash 时截断 '- 作者'（仅用于库名）"""
    s = re.sub(r'[（(][^）)]*[）)]', '', s)
    if cut_dash:
        s = re.sub(r'\s*-\s*.*$', '', s)
    return re.sub(r'[^\w\u4e00-\u9fff]', '', s.lower())

def load_repos(path=None):
    """语雀全量库列表；无缓存文件则调 MCP 拉取"""
    if path and os.path.exists(path):
        return [(d.get('slug', ''), d.get('name', '') or '') for d in json.load(open(path, encoding='utf-8'))]
    import subprocess
    repos = []
    for off in range(0, 600, 100):
        r = subprocess.run(['mcporter', 'call', 'yuque-mcp.yuque_list_repos', '--args',
                            f'{{"login":"yehuoshun","offset":{off},"limit":100}}'],
                           capture_output=True, text=True)
        try:
            data = json.loads(r.stdout).get('data', [])
        except Exception:
            break
        if not data:
            break
        repos.extend(data)
    return [(d.get('slug', ''), d.get('name', '') or '') for d in repos]

def build_lib_exact(repos):
    """库名 -> (slug, name) 精确索引；截断后 <4 字符的改用不截断 norm（防 Git-Cheat-Sheet 类误伤）"""
    idx = {}
    for slug, name in repos:
        lt = norm_title(name, cut_dash=True)
        if len(lt) < 4:
            lt = norm_title(name, cut_dash=False)
        if len(lt) >= 4:
            idx.setdefault(lt, (slug, name))
    return idx

# 书单URL → 已导入账本 key（换源 / 域名迁移 / 仓库版 / 同书多链 / 同文转载）
VARIANTS = {
    'https://rogerdudler.github.io/git-guide/index.zh.html': 'https://github.com/rogerdudler/git-guide',
    'http://danielkummer.github.io/git-flow-cheatsheet/index.zh_CN.html': 'https://github.com/danielkummer/git-flow-cheatsheet',
    'https://aiyanbo.gitbooks.io/spark-programming-guide-zh-cn/content/': 'https://github.com/aiyanbo/spark-programming-guide-zh-cn',
    'https://www.gitbook.com/book/fuxiaopang/learnelasticsearch/details': 'https://legacy.gitbook.com/book/fuxiaopang/learnelasticsearch/details',
    'http://ifeve.com/perfbook/': 'https://github.com/pengdonglin137/perfbook_cn',
    'http://yuedu.baidu.com/ebook/d817967416fc700abb68fca1': 'https://yd.baidu.com/view/d817967416fc700abb68fca1',
    'https://lv.qizhen.xyz': 'https://github.com/ruanqizhen/labview_book',
    'https://llmbook-zh.github.io': 'https://github.com/LLMBook-zh/LLMBook-zh.github.io',
    'https://llmknowledge.pages.dev/zh/': 'https://llmknowledge.org/zh',
    'https://nndl.github.io': 'https://nndl.ai/nndl-v2/',
    'http://www.infoq.com/cn/minibooks/scrum-xp-from-the-trenches': 'https://www.infoq.cn/minibook/scrum-xp-from-the-trenches',
    'https://learnxinyminutes.com': 'https://github.com/adambard/learnxinyminutes-docs',
    'https://web.archive.org/web/20161119141236/http://deerchao.net:80/tutorials/regex/regex.htm': 'https://deerchao.net/tutorials/regex/regex.htm',
    'https://web.archive.org/web/20200415002730/http://man.lupaworld.com/content/network/wireshark/index.html': 'https://wizardforcel.gitbooks.io/wireshark-manual/content/',
    'http://works.jinbuguo.com/apache/menu22/index.html': 'http://shouce.jb51.net/ApacheMenu/',
    'http://www.ttlsa.com/nginx/nginx-stu-pdf/': 'https://github.com/cloudsmithy/2/blob/master/book/Nginx教程从入门到精通(运维生存时间TTLSA出品).pdf',
    'http://tengine.taobao.org/book/index.html': 'https://github.com/taobao/nginx-book',
    'http://cn.linux.vbird.org/linux_basic/linux_basic.php': 'http://cn.linux.vbird.org/linux_basic/',
    'http://sketchcn.com/sketch-chinese-user-manual.html#introduce': 'http://sketchcn.com/sketch-chinese-user-manual.html',
    'https://tinylab.gitbooks.io/elinux/content/zh/': 'https://github.com/tinyclub/elinux',
    'https://book.bsdcn.org': 'https://github.com/FreeBSD-Ask/FreeBSD-Ask',
    'http://www.freebsd.org/doc/zh_CN.UTF-8/books/handbook/': 'https://docs.freebsd.org/zh-cn/books/handbook/',
    'https://web.archive.org/web/20200415002735/https://es.xiaoleilu.com/': 'https://legacy.gitbook.com/book/fuxiaopang/learnelasticsearch/details',
    'http://billie66.github.io/TLCL/book/': 'http://billie66.github.io/TLCL/index.html',
    'http://www.oschina.net/translate/what-every-programmer-should-know-about-memory-part1': 'https://blog.csdn.net/lxlmycsdnfree/article/details/80886903',
}

PLATFORMS = ['51CTO学院', '黑马程序员', '汇智网', '极客学院', '计蒜客', '慕课网', 'Codecademy', 'CodeSchool', 'Coursera', 'shiyanlou', 'TeamTreeHouse', 'Udacity', 'xuetangX']
LOW = ['精通C#(第6版)', '献给写作者的 Markdown 新手指南', 'Java程序员的Golang入门指南', '命名函数表达式探秘', '学用 JavaScript 设计模式', 'Backbone.js入门教程', '楚狂人的D3教程', '在Windows环境下用Yeoman构建AngularJS项目', '21分钟MySQL入门教程', 'MySQL索引背后的数据结构及算法原理', 'iPhone 6 屏幕揭秘', 'Gradle 中文使用文档', '编程入门指南']
PDFS = ['逆向工程权威指南 《Reverse Engineering for Beginners》 Vol.1', '逆向工程权威指南 《Reverse Engineering for Beginners》 Vol.2', 'Spring 2.0核心技术与最佳实践', 'Cmake 实践', '大家來學 LaTeX', 'Yii 2.0 权威指南', '153分钟学会 R', '统计学与 R 读书笔记', 'R 导论', '走向分布式']
# 人工修正（规则误伤覆盖）：标题 → 组
MOVE = {
    'PostgreSQL 8.2.3 中文文档': '07', 'PostgreSQL 9.3.1 中文文档': '07', 'PostgreSQL 9.4.4 中文文档': '07',
    'PostgreSQL 9.5.3 中文文档': '07', 'PostgreSQL 9.6.0 中文文档': '07',
    '人生苦短，我用python': '06', 'Django 1.11.6 中文文档': '06', 'reStructuredText 入门': '06',
    'Tour of Rust': '09', 'Effective Scala': '09', 'Scala 课堂': '09', 'TypeScript 教程': '09',
    'TypeScript 入门教程': '09', 'TypeScript 中文网': '09',
    'ANSI Common Lisp 中文翻译版': '09',
    'C++ Primer 5th Answers': '03',
    '深入 Python 3': '06',
    'Elasticsearch 权威指南': '07',
    'Google Material Design 中文协同翻译': '10', 'Google Material Design 正體中文版': '10', 'Point-of-Android': '10',
    'CSS3 Tutorial 《CSS3 教程》': '05',
    '网易斯坦福大学公开课：iOS 7应用开发字幕文件': '10', 'iOS开发60分钟入门': '10', 'Google Objective-C Style Guide 中文版': '10',
    'Fortran77和90/95编程入门': '09',
    'Phoenix 框架中文文档': '09',
    '阿里巴巴 Java 开发手册': '04',
    'JavaScript 教程 - 廖雪峰的官方网站': '05', 'Python教程 - 廖雪峰的官方网站': '06',
    'Common Lisp 高级编程技术': '09',
    'Perl 教程': '09', 'Visual Prolog 7边练边学': '09', 'Visual Prolog 7初学指南': '09',
}
NAMES = {
    '01': '01-Git/版本控制', '02': '02-Go 语言', '03': '03-C/C++', '04': '04-Java 生态',
    '05': '05-前端(JS/HTML/CSS/Node)', '06': '06-Python/Django', '07': '07-数据库/NoSQL',
    '08': '08-PHP', '09': '09-其他语言/工具', '10': '10-大数据/移动/设计',
    'F': 'F-PDF 类', 'W': 'W-死链快照(需探测原站)', 'P': 'P-在线教育平台(不可导)', 'L': 'L-文章/书页/零散(低价值)',
}
ORDER = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', 'F', 'W', 'P', 'L']

def cate(t: str, u: str) -> str:
    uu = u.lower()
    if t in PLATFORMS: return 'P'
    if t in LOW: return 'L'
    if t in PDFS: return 'F'
    if 'web.archive.org' in uu: return 'W'
    if 'github.com' in uu:
        if any(x in uu for x in ['go-', 'golang', 'go_', 'the-little-go', 'go/', 'npwg']): return '02'
        if any(x in uu for x in ['cppwasm', 'wuzhouhui', 'limingth', 'hellogcc', 'andycai', 'forhappy', 'wuye9036', 'leeyiw', 'anjuke', 'cprimer', 'gcc', 'gdb', 'cgdb', 'awk', 'cpp-primer']): return '03'
        if any(x in uu for x in ['waylau', 'spring', 'mybatis', 'netty', 'servlet', 'jersey', 'shiro', 'mina', 'activiti', 'h2-database', 'jsse', 'qibaoguang', 'p3c']): return '04'
        if any(x in uu for x in ['css', 'javascript', 'angular', 'backbone', 'react', 'webpack', 'node', 'koa', 'express', 'jquery', 'd3', '12-javascript', 'jayli', 'xufei', 'mgechev', 'nswbmw', 'guo-yu', 'alsotang', 'jollen', 'nodejs-tw', 'thejian', 'hateonion', 'fakefish', 'chadluo', 'adamlu', 'getify', 'justjavac', 'coffeescript', 'elrrrrrrr', 'geekplux', 'electron', 'css3-tutorial']): return '05'
        if any(x in uu for x in ['redis', 'mongodb', 'huangz1990', 'jasonlai256', 'justinyhuang', 'looly', 'elasticsearch']): return '07'
        if any(x in uu for x in ['rust', 'ruby', 'perl', 'scala', 'elixir', 'erlang', 'swift', 'lisp', 'excel', 'typescript', 'diveintopython', 'jiechic', 'fayland', 'juanitofatas', 'jkyin', 'qinjx', 'graduate-project', '49951331', 'moophy', 'material_design_zh', 'fx-max', 'point-of-android']): return '09'
        return '09'
    if any(x in uu for x in ['backlogtool', 'gitref', 'gitmagic', 'git-scm', 'svnbook', 'hginit', 'mercurial', 'gitbooks.io/github-cheat', 'worldhello', 'gitbooks.io/progit2', 'liaoxuefeng.com/wiki/896043488029600']): return '01'
    if any(x in uu for x in ['go-', 'golang', 'mikespook', 'tiancaiamao', 'build-web-application', 'gorevel', 'tour.go-zh', 'draveness.me/golang', 'go-internals', 'kevingo.gitbooks.io/the-little-go-book', 'astaxie.gitbooks.io']): return '02'
    if any(x in uu for x in ['wangdoc', 'dotcpp', 'linuxtone', 'nowamagic', 'c-faq', 'beej', 'sunistudio', 'tinylab.gitbooks.io/cbook', 'ituring.com.cn/book/1203', 'hackmd', 'readthedocs.org/en/latest/google-cpp', 'awk.readthedocs', 'zh-google-styleguide', 'clang', 'cbook', 'cppfaq', 'micro.ustc']): return '03'
    if any(x in uu for x in ['liaoxuefeng.com/wiki/1252599548343744', 'quanke', 'mybatis', 'nutz', 'hawstein']): return '04'
    if any(x in uu for x in ['javascript', 'node', 'angular', 'react', 'vue', 'backbone', 'jquery', 'electron', 'extjs', 'd3', 'css', 'html', 'sass', 'emmet', 'bootstrap', 'zepto', 'coffee-script', 'es6.ruanyifeng', 'learnlayout', 'doyoe', 'w3school', 'codeguide', 'zh.javascript', 'typeof', 'promises-book', 'the5fire', 'html.cn', 'decembercafe', 'fraserxu', 'discountry', 'expressjs', 'ruanyifeng.com/nodejs', 'nqdeng', 'nodebeginner', 'i5ting', 'npmjs.com/package/learnyounode', 'gitbook.com/book/0532', 'wizardforcel.gitbooks.io/electron', 'wcc723.gitbooks.io/google_design', 'alloyteam', 'yanxyz', 'bootcss', 'wcc723', 'angular.cn', 'material.angular']): return '05'
    if any(x in uu for x in ['python', 'django', 'numpy', 'matplotlib', 'tornado', 'osgeo', 'bop.mol', 'cnblogs.com/derek', 'pythondoc', 'interpy', 'funhacks', 'py.qizhen', 'yiyibooks', 'djangobook', 'djangogirls', 'dusaiphoto', 'docspy3zh']): return '06'
    if any(x in uu for x in ['postgresql', 'mysql', 'redis', 'mongodb', 'disque', 'redisdoc', 'redisbook', 'codinglabs']): return '07'
    if any(x in uu for x in ['laravel', 'symfony', 'composer', 'codeigniter', 'phalcon', 'psr', 'wusuopu', 'yii2', 'yiichina', 'phpcomposer', 'phphub']): return '08'
    if any(x in uu for x in ['rust', 'ruby', 'perl', 'scala', 'haskell', 'elixir', 'erlang', 'swift', 'scheme', 'lisp', 'fortran', 'lua', 'deno', 'typescript', 'tslang', 'visual-prolog', 'excel', 'vba', 'prolog', 'groovy', 'dart', 'markdown.tw', 'ctan', 'latex', 'shell', 'ubuntu.org.cn', '52fhy', 'strikingly', 'sinatrarb', 'ihower', 'ruby-china', 'lrthw', 'twitter.github', 'deathking', 'yast', 'course.rs', 'tourofrust', 'tlborm', 'zjp-cn', 'learnyouahaskell', 'cnhaskell', 'elixirschool', 'runoob', 'w3cschool', 'pythonguidecn', 'python3-cookbook', 'mydearxym', 'acl.readthedocs', 'ituring.com.cn/minibook', 'yiibai']): return '09'
    if any(x in uu for x in ['android', 'ios', 'objective', 'apple', 'wileam', 'material', 'design', 'elasticsearch']): return '10'
    return 'L'

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    body = open(args[0], encoding='utf-8').read()
    ledger_path = 'last-imported.json'
    out_path = None
    repos_path = None
    if '--json' in args:
        ledger_path = args[args.index('--json') + 1]
    if '--out' in args:
        out_path = args[args.index('--out') + 1]
    if '--repos' in args:
        repos_path = args[args.index('--repos') + 1]
    d = json.load(open(ledger_path, encoding='utf-8'))
    repos = load_repos(repos_path)
    lib_exact = build_lib_exact(repos)

    book_links = [(t.strip(), u) for t, u in re.findall(r'\[([^\]]*)\]\((https?://[^)\s]+)\)', body)]
    imported = set(norm(k) for k in d.keys())
    vmap = {norm(u): norm(v) for u, v in VARIANTS.items()}

    seen, miss, hit = set(), [], []
    for t, u in book_links:
        n = norm(u)
        if n in seen:
            continue
        seen.add(n)
        n2 = vmap.get(n, n)
        why = None
        if n2 in imported:
            why = f"账本: {n2}"
        else:
            bt = norm_title(t, cut_dash=False)
            if bt in lib_exact:
                why = f"库名: {lib_exact[bt][0]} | {lib_exact[bt][1]}"
        if why:
            hit.append((t, u, why))
        else:
            miss.append((t, u))

    print(f"书单链接去重: {len(seen)} 条 | 已导入: {len(hit)} 条 | 未导入: {len(miss)} 条")

    groups = {c: [] for c in ORDER}
    for t, u in miss:
        groups[MOVE.get(t, cate(t, u))].append((t, u))
    if out_path:
        lines, idx = [], 0
        for c in ORDER:
            items = groups[c]
            if not items:
                continue
            lines.append(f"\n{'='*62}\n■ {NAMES[c]}（{len(items)} 条）\n{'='*62}")
            for t, u in items:
                idx += 1
                lines.append(f"{idx:03d}. {t}\n     {u}")
        open(out_path, 'w').write("\n".join(lines) + "\n")
        print(f"未导入清单已写入: {out_path}")

if __name__ == '__main__':
    main()
