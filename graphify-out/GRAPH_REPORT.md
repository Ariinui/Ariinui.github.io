# Graph Report - .  (2026-08-13)

## Corpus Check
- 6 files · ~15,290 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 79 nodes · 93 edges · 16 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 6 edges
2. `apply_en_translate()` - 6 edges
3. `search_exact()` - 4 edges
4. `parse_conference_issue()` - 4 edges
5. `entryText()` - 4 edges
6. `build_dict()` - 3 edges
7. `dereduplicate_candidates()` - 3 edges
8. `strip_accents()` - 3 edges
9. `content_stem()` - 3 edges
10. `part_stem()` - 3 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Community 0"
Cohesion: 0.17
Nodes (12): apply_en_translate(), guide2_section_content_html(), guide_section_content_html(), load_conference_issues(), parse_conference_issue(), HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'., HTML interne d'une section guide2, sans son <p class="Chapter-Number">     (dej, Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot (+4 more)

### Community 1 - "Community 1"
Cohesion: 0.27
Nodes (9): content_stem(), dereduplicate_candidates(), fr_words(), normalize(), part_stem(), One-off extraction: builds tah_dict.json (word -> short French gloss) from the R, Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = ", strip_accents() (+1 more)

### Community 2 - "Community 2"
Cohesion: 0.18
Nodes (0): 

### Community 3 - "Community 3"
Cohesion: 0.25
Nodes (6): entryParts(), entryText(), goToEntry(), showEntry(), todayLong(), underline()

### Community 4 - "Community 4"
Cohesion: 0.36
Nodes (9): dereduplicate_candidates(), get_token(), glosses_from_lexeme_page(), main(), normalize(), One-off: for every Tahitian word in the Livre de Mormon text still without a Fre, Returns list of (href, normalized_lexeme) for exact normalized matches     in th, search_exact() (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.38
Nodes (6): build_dict(), extract_book_vocab(), load_muse_dict(), load_sqlite_dict(), Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des, Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (1): One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (3): Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp, tah_normalize(), wrap_tah_words()

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (2): clean_bom_en_verse_text(), parse_bom_en_source()

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (2): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_, render_volume_block()

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (2): Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume, split_verse_number()

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

## Knowledge Gaps
- **21 isolated node(s):** `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des`, `Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines`, `One-off extraction: builds tah_dict.json (word -> short French gloss) from the R`, `Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = "` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 8`** (2 nodes): `clean_bom_en_verse_text()`, `parse_bom_en_source()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 9`** (2 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`, `render_volume_block()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (2 nodes): `Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume`, `split_verse_number()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `apply_en_translate()` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `parse_conference_issue()` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `split_verse_number()` connect `Community 10` to `Community 2`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **What connects `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des`, `Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines` to the rest of the system?**
  _21 weakly-connected nodes found - possible documentation gaps or missing edges._