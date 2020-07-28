import brat_tool

import sys, glob
import spacy
nlp = spacy.load("en_core_web_sm")

src_dir = sys.argv[1]

target_lemma_set = set()


for dir_ in ['train', 'dev']:
    for doc_count, annotation_file in enumerate(glob.glob(src_dir+dir_+"/*.ann", recursive=True)):
        with open(annotation_file, encoding="utf-8") as f:
            ann_text = f.read()
            ann = brat_tool.BratAnnotations(ann_text)

            for ev in ann.getEventAnnotationList():
                if " " not in ev.textbound.text: # single word
                    doc = nlp(ev.textbound.text)
                    if doc[0].pos in [spacy.symbols.NOUN or spacy.symbols.VERB]:
                        target_lemma_set.add(doc[0].lemma_)
                else:
                    if not ev.textbound.separated: # not separated
                        doc = nlp(ev.textbound.text)
                        target_lemma_set.add(" ".join([token.lemma_ for token in doc]))
                    else: # seprated text
                        pass

print(len(target_lemma_set))

with open("event_lemma.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(target_lemma_set))
