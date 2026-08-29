import os, re

CONF_ANALOGY_SPLIT_RE = re.compile(r'\n\s*[─\-]{3,}\s*\n')
CONF_ANALOGY_SPLIT_COMPACT_RE = re.compile(r'\n\s*\n(?=Conf[ée]rence g[ée]n[ée]rale du )')
CONF_ANALOGY_DATE_RE = re.compile(r'Conf[ée]rence g[ée]n[ée]rale du ([^\n]+)')
CONF_ANALOGY_FIELD_BOUNDARY = r"(?=\n\s*\n|\n\s*(?:Th[eè]me|L'analogie|Signification|Lien)\s*:|\Z)"
CONF_ANALOGY_THEME_RE = re.compile(r'Th[eè]me\s*:\s*(.+?)\s*' + CONF_ANALOGY_FIELD_BOUNDARY, re.DOTALL)
CONF_ANALOGY_TEXT_RE = re.compile(r"L'analogie\s*:\s*(.+?)\s*" + CONF_ANALOGY_FIELD_BOUNDARY, re.DOTALL)
CONF_ANALOGY_SIGNIF_RE = re.compile(r'Signification\s*:\s*(.+?)\s*' + CONF_ANALOGY_FIELD_BOUNDARY, re.DOTALL)
CONF_ANALOGY_LIEN_RE = re.compile(r'Lien\s*:\s*(\S+)')
CONF_ANALOGY_DASH_LINE_RE = re.compile(r'^(.+?)\s+[–—‐―-]\s+(.+?)\s*$')
CONF_ANALOGY_KNOWN_PREFIXES = ('Conf', 'Thème', 'Theme', "L'analogie", 'Signification', 'Lien')

folder = 'conference-analogies-source'
total_lien = 0
total_extracted = 0
skipped_no_fields = []
skipped_long_theme = []
skipped_no_context = []

for fname in sorted(os.listdir(folder)):
    if not fname.lower().endswith('.txt'):
        continue
    with open(os.path.join(folder, fname), 'r', encoding='utf-8') as f:
        text = f.read()
    text = text.replace('\r\n', '\n')
    text = re.sub(r'\*\*', '', text)

    last_issue_key = last_speaker = None
    raw_blocks = CONF_ANALOGY_SPLIT_RE.split(text)
    blocks = []
    for raw_block in raw_blocks:
        if len(CONF_ANALOGY_LIEN_RE.findall(raw_block)) > 1:
            blocks.extend(CONF_ANALOGY_SPLIT_COMPACT_RE.split(raw_block))
        else:
            blocks.append(raw_block)
    for block in blocks:
        lien_m = CONF_ANALOGY_LIEN_RE.search(block)
        if not lien_m:
            continue
        total_lien += 1
        theme_m = CONF_ANALOGY_THEME_RE.search(block)
        analogie_m = CONF_ANALOGY_TEXT_RE.search(block)
        signif_m = CONF_ANALOGY_SIGNIF_RE.search(block)
        if not (theme_m and analogie_m and signif_m):
            skipped_no_fields.append((fname, block[:200]))
            continue
        if len(theme_m.group(1)) > 80:
            skipped_long_theme.append((fname, theme_m.group(1)[:150]))
            continue

        date_m = CONF_ANALOGY_DATE_RE.search(block)
        if date_m:
            # rough issue key just for context tracking
            last_issue_key = date_m.group(1).strip()

        speaker = None
        for line in block.split('\n'):
            s = line.strip()
            if not s or s.startswith(CONF_ANALOGY_KNOWN_PREFIXES):
                continue
            stm = CONF_ANALOGY_DASH_LINE_RE.match(s)
            if stm:
                speaker = stm.group(1).strip()
                break
        if speaker:
            last_speaker = speaker

        if not last_issue_key or not last_speaker:
            skipped_no_context.append((fname, block[:200]))
            continue

        total_extracted += 1

print(f"total Lien: found = {total_lien}")
print(f"total extracted = {total_extracted}")
print(f"skipped (missing field) = {len(skipped_no_fields)}")
print(f"skipped (theme too long) = {len(skipped_long_theme)}")
print(f"skipped (no context) = {len(skipped_no_context)}")

with open('scratch_diag_skipped.txt', 'w', encoding='utf-8') as f:
    f.write("=== MISSING FIELD ===\n")
    for fname, snippet in skipped_no_fields:
        f.write(f"[{fname}] {snippet!r}\n\n")
    f.write("=== THEME TOO LONG ===\n")
    for fname, snippet in skipped_long_theme:
        f.write(f"[{fname}] {snippet!r}\n\n")
    f.write("=== NO CONTEXT ===\n")
    for fname, snippet in skipped_no_context:
        f.write(f"[{fname}] {snippet!r}\n\n")
