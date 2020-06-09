import os
from typing import Iterator, Tuple, List

from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.data.readers.base_reader import MultiPackReader


def doc_name(doc_path):
    return os.path.basename(doc_path).split('.')[0]


def doc_text(doc_path):
    with open(doc_path) as d:
        return d.read()


class TwoDocumentPackReader(MultiPackReader):
    def _collect(
            self, data_dir: str, pairs: List[Tuple[str, str]]
    ) -> Iterator[Tuple[Tuple[str, str, str], Tuple[str, str, str]]]:
        for doc1, doc2 in pairs:
            text_doc1 = os.path.join(data_dir, doc1 + '.txt')
            text_doc2 = os.path.join(data_dir, doc2 + '.txt')

            yield text_doc1, text_doc2

    def _parse_pack(
            self,
            doc_path_pair: Tuple[str, str]
    ) -> Iterator[MultiPack]:
        mp = MultiPack()
        doc1, doc2 = doc_path_pair

        doc1_name, doc2_name = doc_name(doc1), doc_name(doc2)
        doc1_text, doc2_text = doc_text(doc1), doc_text(doc2)

        mp.meta.doc_id = f'pair_{doc1_name}_and_{doc2_name}'

        p1 = DataPack(doc1_name)
        p1.set_text(doc1_text)
        mp.add_pack_(p1)

        p2 = DataPack(doc2_name)
        p2.set_text(doc2_text)
        mp.add_pack_(p2)

        yield mp
