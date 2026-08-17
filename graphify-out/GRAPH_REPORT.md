# Graph Report - .  (2026-08-16)

## Corpus Check
- 5 files · ~24,487 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 153 nodes · 122 edges · 71 communities detected
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
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 6 edges
2. `entryBlocks()` - 6 edges
3. `cameo_render_entry()` - 5 edges
4. `write_guide_volume()` - 5 edges
5. `search_exact()` - 4 edges
6. `book_display_title()` - 4 edges
7. `chapter_display_title()` - 4 edges
8. `render_volume_block()` - 4 edges
9. `cameo_clean_field()` - 4 edges
10. `write_cameos()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `write_guide_volume()` --calls--> `write()`  [EXTRACTED]
  generate_pages.py → generate_pages.py  _Bridges community 5 → community 4_

## Communities

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (14): guide2_section_content_html(), guide_section_content_html(), parse_bomm_heading_ref(), parse_bomm_source(), parse_bomm_title_book_chapter(), Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp, 1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag, HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'. (+6 more)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (11): entryBlocks(), entryFullText(), entryParts(), entryTextParts(), goToEntry(), refsHidden(), showEntry(), splitLongBlock() (+3 more)

### Community 2 - "Community 2"
Cohesion: 0.27
Nodes (9): content_stem(), dereduplicate_candidates(), fr_words(), normalize(), part_stem(), One-off extraction: builds tah_dict.json (word -> short French gloss) from the R, Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = ", strip_accents() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.36
Nodes (9): dereduplicate_candidates(), get_token(), glosses_from_lexeme_page(), main(), normalize(), One-off: for every Tahitian word in the Livre de Mormon text still without a Fre, Returns list of (href, normalized_lexeme) for exact normalized matches     in th, search_exact() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.29
Nodes (8): book_display_title(), chapter_display_title(), books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_, raw_title est toujours '{book_title} Chapitre N' (source) - ne     remplace que, Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon, render_volume_block(), to_superscript(), write_guide_volume()

### Community 5 - "Community 5"
Cohesion: 0.29
Nodes (8): cameo_clean_field(), cameo_render_entry(), cameo_render_paragraphs(), Certains champs de la source (ex. le nom d'une entree) contiennent du     HTML, La description (contrairement au texte d'analyse, deja extrait en     texte pur, Une entree top-level (personne/concept) peut avoir plusieurs     sous-articles, write(), write_cameos()

### Community 6 - "Community 6"
Cohesion: 0.4
Nodes (5): clean_evidence_body(), parse_evidence_scripture_reference(), parse_evidence_source(), 1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)], Parse le HTML de l'article et retourne un fragment pret a inserer.     Deux net

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (1): One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (1): Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (1): Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (1): raw_title est toujours '{book_title} Chapitre N' (source) - ne     remplace que

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (1): HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (1): 1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)]

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Parse le HTML de l'article et retourne un fragment pret a inserer.     Deux net

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): 1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): 1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): 1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)]

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Parse le HTML de l'article et retourne un fragment pret a inserer.     Deux net

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): 1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): 1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2 : uniquement les paires     question/reponse

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): HTML interne d'une section guide2, sans son <p class="Chapter-Number">     (dej

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Un <section id=...> de premier niveau sans div.body-block est un     separateur

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Forme attendue par render_volume_block : un 'livre' par numero de     conferenc

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_

## Knowledge Gaps
- **81 isolated node(s):** `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `One-off extraction: builds tah_dict.json (word -> short French gloss) from the R`, `Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = "`, `One-off: for every Tahitian word in the Livre de Mormon text still without a Fre`, `Returns list of (href, normalized_lexeme) for exact normalized matches     in th` (+76 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 8`** (1 nodes): `Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de nume`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 9`** (1 nodes): `Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (1 nodes): `raw_title est toujours '{book_title} Chapitre N' (source) - ne     remplace que`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)]`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `Parse le HTML de l'article et retourne un fragment pret a inserer.     Deux net`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)]`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Parse le HTML de l'article et retourne un fragment pret a inserer.     Deux net`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut     d'une pag`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Genere les pages chapitre d'un volume de commentaire lie au Livre de     Mormon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate des`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Vocabulaire reel de tous les livres anglais deja importes - pas les     dizaines`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe     comp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `HTML interne d'une section guide2 : uniquement les paires     question/reponse`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `HTML interne d'une section guide2, sans son <p class="Chapter-Number">     (dej`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Equivalent anglais de wrap_tah_words() - pas de detection de groupes     de mot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne     toucha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Un <section id=...> de premier niveau sans div.body-block est un     separateur`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Forme attendue par render_volume_block : un 'livre' par numero de     conferenc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `cameo_render_entry()` connect `Community 5` to `Community 0`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Why does `write_guide_volume()` connect `Community 4` to `Community 0`, `Community 5`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **What connects `One-off: extracts embark_supplement.json (single-word Tahitian -> French gloss)`, `One-off extraction: builds tah_dict.json (word -> short French gloss) from the R`, `Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.     "maitatai" = "` to the rest of the system?**
  _81 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._