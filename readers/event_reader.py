import os
from typing import Any, Iterator, Tuple

from forte.data.data_pack import DataPack
from forte.data.readers import PackReader
from ft.onto.base_ontology import EventMention


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

    def _parse_pack(self, data_pair: Tuple[str, str, str]
                    ) -> Iterator[DataPack]:
        pack = DataPack()

        doc_name, text_file, anno_file = data_pair

        with open(text_file) as doc, open(anno_file) as anno:
            # Get the text of the news.
            pack.set_text(doc.read())

            pack.set_meta(doc_id=doc_name)

            # Add the annotation into the data pack.
            for line in anno.readlines():
                event_type, begin, end = line.strip().split()
                event_mention: EventMention = EventMention(pack, begin, end)
                event_mention.event_type = event_type

                pack.add_entry(event_mention)

        yield pack

    def _cache_key_function(self, collection: Any) -> str:
        pass
