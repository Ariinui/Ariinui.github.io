# Graph Report - .  (2026-08-16)

## Corpus Check
- 5 files · ~21,085 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 120 nodes · 108 edges · 50 communities detected
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
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 6 edges
2. `entryBlocks()` - 6 edges
3. `write_guide_volume()` - 5 edges
4. `search_exact()` - 4 edges
5. `book_display_title()` - 4 edges
6. `chapter_display_title()` - 4 edges
7. `render_volume_block()` - 4 edges
8. `dereduplicate_candidates()` - 3 edges
9. `strip_accents()` - 3 edges
10. `content_stem()` - 3 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Community 0"
Cohesion: 0.18
Nodes (11): entryBlocks(), entryFullText(), entryParts(), entryTextParts(), goToEntry(), refsHidden(), showEntry(), splitLongBlock() (+3 more)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (0): 

### Community 2 - "Community 2"
Cohesion: 0.27
Nodes (9): content_stem(), dereduplicate_candidates(), fr_words(), normalize(), part_stem(), One-off extraction: builds tah_dict.json (word -> short French gloss) from the R, Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = ", strip_accents() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.36
Nodes (9): dereduplicate_candidates(), get_token(), glosses_from_lexeme_page(), main(), normalize(), One-off: for every Tahitian word in the Livre de Mormon text still without a Fre, Returns list of (href, normalized_lexeme) for exact normalized matches     in th, search_exact() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.25
Nodes (9): book_display_title(), chapter_display_title(), books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_, Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon, raw_title est toujours '{book_title} Chapitre N' (source) - ne     remplace que, render_volume_block(), to_superscript(), write() (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.4
Nodes (5): clean_evidence_body(), parse_evidence_scripture_reference(), parse_evidence_source(), 1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)], Parse le HTML de l'article et retourne un fragment pret a inserer.     Deux net

### Community 6 - "Community 6"
Cohesion: 0.5
Nodes (4): parse_bomm_heading_ref(), parse_bomm_source(), parse_bomm_title_book_chapter(), 1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (1): One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)

### Community 8 - "Community 8"
Cohesion: 0.67
Nodes (3): Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp, tah_normalize(), wrap_tah_words()

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (2): guide_section_content_html(), HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (2): guide2_section_content_html(), HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (2): Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume, split_verse_number()

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2, sans son <p class="Chapter-Number">     (dej

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

## Knowledge Gaps
- **53 isolated node(s):** `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `One-off extraction: builds tah_dict.json (word -> short French gloss) from the R`, `Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = "`, `One-off: for every Tahitian word in the Livre de Mormon text still without a Fre`, `Returns list of (href, normalized_lexeme) for exact normalized matches     in th` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 9`** (2 nodes): `guide_section_content_html()`, `HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (2 nodes): `guide2_section_content_html()`, `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (2 nodes): `Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume`, `split_verse_number()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `HTML interne d'une section guide2, sans son <p class="Chapter-Number">     (dej`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `write_guide_volume()` connect `Community 4` to `Community 1`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Why does `split_verse_number()` connect `Community 11` to `Community 1`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Why does `wrap_tah_words()` connect `Community 8` to `Community 1`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **What connects `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `One-off extraction: builds tah_dict.json (word -> short French gloss) from the R`, `Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = "` to the rest of the system?**
  _53 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.14 - nodes in this community are weakly interconnected._