import re, os, shutil
from bs4 import BeautifulSoup

SRC = '/home/admin/.openclaw/workspace/tmp/fpb189-node-lessons-src'
OUT = '/home/admin/.openclaw/workspace/tmp/fpb189-node-lessons/site'
os.makedirs(OUT, exist_ok=True)

# 1. 课程列表（README.md）解析课名
readme = open(os.path.join(SRC, 'README.md'), encoding='utf-8').read()
lessons = []  # (lessonN, 标题)
for line in readme.split('\n'):
    m = re.match(r'\* Lesson (\d+): \[《(.*?)》\]', line)
    if m:
        lessons.append((int(m.group(1)), m.group(2)))
lessons.sort()
print("lessons:", len(lessons))

# 2. 拷每课 README → NN-标题.md
os.makedirs(OUT, exist_ok=True)
for num, title in lessons:
    d = f'lesson{num}'
    src_md = os.path.join(SRC, d, 'README.md')
    if not os.path.exists(src_md):
        print(f"MISSING {d}/README.md")
        continue
    t = open(src_md, encoding='utf-8').read()
    # 剥首个 H1
    t = re.sub(r'^# .*$', '', t, flags=re.M, count=1)
    # 外链图 → 本地相对路径（lessonN/x.png）
    def fix_img(m):
        alt, url = m.group(1), m.group(2)
        # github blob/raw 外链 → basename 反查本地
        fn = os.path.basename(url.split('?')[0])
        return f'![{alt}]({d}/{fn})'
    t = re.sub(r'!\[([^\]]*)\]\((https?://[^)]+)\)', fix_img, t)
    fname = f'{num:02d}-{title}.md'
    with open(os.path.join(OUT, fname), 'w', encoding='utf-8') as f:
        f.write(f'# {title}\n\n' + t.strip() + '\n')
    print(fname)

# 3. lesson14 附加篇
extra = os.path.join(SRC, 'lesson14', '解密设计模式-王垠.md')
if os.path.exists(extra):
    t = open(extra, encoding='utf-8').read()
    t = re.sub(r'^# .*$', '', t, flags=re.M, count=1)
    with open(os.path.join(OUT, '14-附-解密设计模式（王垠）.md'), 'w', encoding='utf-8') as f:
        f.write(f'# 附-解密设计模式（王垠）\n\n' + t.strip() + '\n')
    print("14-附-解密设计模式（王垠）.md")

# 4. 图：拷 lessonN/*.png 到 site/lessonN/
for d in sorted(os.listdir(SRC)):
    if not re.match(r'^lesson\d+$', d): continue
    src_d = os.path.join(SRC, d)
    pngs = [f for f in os.listdir(src_d) if f.endswith('.png')]
    if pngs:
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
        for png in pngs:
            shutil.copy(os.path.join(src_d, png), os.path.join(OUT, d, png))
        print(f"imgs {d}: {len(pngs)}")

# 5. 校验：md 图引用都能解析
missing = 0
for f in os.listdir(OUT):
    if not f.endswith('.md'): continue
    t = open(os.path.join(OUT, f), encoding='utf-8').read()
    for m in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', t):
        p = os.path.normpath(os.path.join(OUT, m.group(1)))
        if not os.path.exists(p):
            missing += 1
            print(f"MISSING {f}: {m.group(1)}")
print("missing:", missing)