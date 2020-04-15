import os
from typing import Iterator, Tuple, List

from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.data.readers.base_reader import PackReader, MultiPackReader

from edu.cmu import EventMention


def create_pack(doc_name, text_file, anno_file):
    pack = DataPack()

    with open(text_file) as doc, open(anno_file) as anno:
        # Get the text of the news.
        pack.set_text(doc.read())

        pack.set_meta(doc_id=doc_name)

        # Add the annotation into the data pack.
        for line in anno.readlines():
            event_type, begin, end = line.strip().split()

            event_mention = EventMention(pack, int(begin), int(end))
            event_mention.event_type = event_type

            pack.add_entry(event_mention)
    return pack


class EventReader(PackReader):
    def _collect(self, data_dir) -> Iterator[Tuple[str, str]]:
        for f in os.listdir(data_dir):
            if f.endswith('txt'):
                doc_name = f.replace('.txt', '')
                anno_filename = doc_name + '.anno'

                text_f = os.path.join(data_dir, f)
                anno_f = os.path.join(data_dir, anno_filename)

                if os.path.exists(anno_f):
                    yield doc_name, text_f, anno_f

    def _parse_pack(
            self, data_info: Tuple[str, str, str]) -> Iterator[DataPack]:
        doc_name, text_file, anno_file = data_info
        yield create_pack(doc_name, text_file, anno_file)


class TwoDocumentEventReader(MultiPackReader):
    def _collect(
            self, data_dir: str, pairs: List[Tuple[str, str]]
    ) -> Iterator[Tuple[Tuple[str, str, str], Tuple[str, str, str]]]:
        for doc1, doc2 in pairs:
            text_doc1 = os.path.join(data_dir, doc1 + '.txt')
            anno_doc1 = os.path.join(data_dir, doc1 + '.anno')

            text_doc2 = os.path.join(data_dir, doc2 + '.txt')
            anno_doc2 = os.path.join(data_dir, doc2 + '.anno')

            yield (doc1, text_doc1, anno_doc1), (doc2, text_doc2, anno_doc2)

    def _parse_pack(
            self,
            doc_pair: Tuple[Tuple[str, str, str], Tuple[str, str, str]]
    ) -> Iterator[MultiPack]:
        mp = MultiPack()

        doc1, doc2 = doc_pair

        mp.meta.doc_id = f'pair_{doc1[0]}_and_{doc2[0]}'

        p1 = create_pack(*doc1)
        p2 = create_pack(*doc2)

        mp.add_pack_(p1)
        mp.add_pack_(p2)

        yield mp
