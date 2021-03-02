import os
from typing import Iterator, Tuple, List, Any
import json
import logging

from forte.data.base_pack import PackType
from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.data.readers.base_reader import PackReader
from forte.data.readers.base_reader import MultiPackReader

from edu.cmu import TitleSpan, DateSpan, BodySpan


def doc_name(doc_path):
    return os.path.basename(doc_path).split(".")[0]


def doc_text(doc_path):
    with open(doc_path) as d:
        return d.read()


class DocumentReader(PackReader):
    def _collect(self, data_dir: str) -> Iterator[Any]:
        for f in os.listdir(data_dir):
            yield os.path.join(data_dir, f)

    def _parse_pack(self, input_file: str) -> Iterator[PackType]:
        with open(input_file) as f:
            pack: DataPack = DataPack()
            pack.pack_name = os.path.basename(input_file).split(".")[0]
            pack.set_text(f.read())
            yield pack


class TwoDocumentPackReader(MultiPackReader):
    def _collect(
        self, data_dir: str, pairs: List[Tuple[str, str]]
    ) -> Iterator[Tuple[Tuple[str, str, str], Tuple[str, str, str]]]:
        for doc1, doc2 in pairs:
            pack_path1 = os.path.join(data_dir, doc1)
            pack_path2 = os.path.join(data_dir, doc2)

            if not os.path.isfile(pack_path1):
                logging.warning("missing file: %s" % pack_path1)
            elif not os.path.isfile(pack_path2):
                logging.warning("missing file: %s" % pack_path2)
            else:
                yield pack_path1, pack_path2

    def _parse_pack(self, doc_path_pair: Tuple[str, str]) -> Iterator[MultiPack]:
        mp = MultiPack()
        doc1, doc2 = doc_path_pair

        with open(doc1) as doc1_f, open(doc2) as doc2_f:
            p1: DataPack = DataPack.deserialize(doc1_f.read())
            p2: DataPack = DataPack.deserialize(doc2_f.read())
            mp.add_pack_(p1)
            mp.add_pack_(p2)
            mp.pack_name = f"pair_{p1.pack_name}_and_{p2.pack_name}"

        yield mp


class DocumentReaderJson(PackReader):
    def _collect(self, data_dir: str) -> Iterator[Any]:
        for f in os.listdir(data_dir):
            yield os.path.join(data_dir, f)

    def _parse_pack(self, input_file: str) -> Iterator[PackType]:
        with open(input_file) as f:
            pack: DataPack = DataPack()
            pack.pack_name = os.path.basename(input_file).split(".")[0]

            text = ""
            data = json.load(f)

            title = data.get("title", None)
            title_str = f"Title: {title}"
            title_offset, title_length = len(text), len(title_str)
            text += f"{title_str}\n\n"

            date = data.get("date", None)
            date_str = f"Date: {date}"
            date_offset, date_length = len(text), len(date_str)
            text += f"{date_str}\n\n"

            body = data["text"]
            body_offset, body_length = len(text), len(body)
            text += f"{body}"

            pack.set_text(text)

            TitleSpan(pack, title_offset, title_offset + title_length)
            DateSpan(pack, date_offset, date_offset + date_length)
            BodySpan(pack, body_offset, body_offset + body_length)

            yield pack
