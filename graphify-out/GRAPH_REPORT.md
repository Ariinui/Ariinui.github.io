# Graph Report - .  (2026-08-13)

## Corpus Check
- 6 files · ~13,380 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 68 nodes · 86 edges · 7 communities detected
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

## God Nodes (most connected - your core abstractions)
1. `main()` - 6 edges
2. `apply_en_translate()` - 5 edges
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
Cohesion: 0.14
Nodes (9): clean_bom_en_verse_text(), parse_bom_en_source(), Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp, books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_, Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume, render_volume_block(), split_verse_number(), tah_normalize() (+1 more)

### Community 1 - "Community 1"
Cohesion: 0.27
Nodes (9): content_stem(), dereduplicate_candidates(), fr_words(), normalize(), part_stem(), One-off extraction: builds tah_dict.json (word -> short French gloss) from the R, Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = ", strip_accents() (+1 more)

### Community 2 - "Community 2"
Cohesion: 0.25
Nodes (6): entryParts(), entryText(), goToEntry(), showEntry(), todayLong(), underline()

### Community 3 - "Community 3"
Cohesion: 0.36
Nodes (9): dereduplicate_candidates(), get_token(), glosses_from_lexeme_page(), main(), normalize(), One-off: for every Tahitian word in the Livre de Mormon text still without a Fre, Returns list of (href, normalized_lexeme) for exact normalized matches     in th, search_exact() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (10): apply_en_translate(), guide_section_content_html(), load_conference_issues(), parse_conference_issue(), HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'., Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot, Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha, Un <section id=...> de premier niveau sans div.body-block est un     separateur (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.38
Nodes (6): build_dict(), extract_book_vocab(), load_muse_dict(), load_sqlite_dict(), Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des, Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (1): One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)

## Knowledge Gaps
- **15 isolated node(s):** `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des`, `Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines`, `One-off extraction: builds tah_dict.json (word -> short French gloss) from the R`, `Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = "` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `apply_en_translate()` connect `Community 4` to `Community 0`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `parse_conference_issue()` connect `Community 4` to `Community 0`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des`, `Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.14 - nodes in this community are weakly interconnected._