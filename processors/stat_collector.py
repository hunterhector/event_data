import sys
from typing import Dict, Tuple, Set

from forte.data.multi_pack import MultiPack
from forte.data.readers.stave_readers import StaveMultiDocSqlReader
from forte.pipeline import Pipeline
from forte.processors.base import MultiPackProcessor

from edu.cmu import CrossEventRelation


class MaceFormatCollector(MultiPackProcessor):
    """
    This is a class to show how to compute statistics from the collected0
    event pairs (as multi packs). This class collect event relation
    annotation from a database to produce a CSV like the MACE requirement:
    https://github.com/dirkhovy/MACE
    """

    def __init__(self):
        self.event_pair_indices: Dict[
            Tuple[Tuple[int, int], Tuple[int, int]], int] = {}
        self.annotator_indices: Dict[str, int] = {}
        self.mace_matrix_ones: Set[Tuple[int, int]] = set()

    def _process(self, input_pack: MultiPack):
        # Creator index corresponds to each row of the MACE matrix.
        for creator in input_pack.get_all_creator():
            if creator not in self.annotator_indices:
                creator_id = len(self.annotator_indices)
                self.annotator_indices[creator] = creator_id
            else:
                creator_id = self.annotator_indices[creator]
            relation: CrossEventRelation

            for relation in input_pack.get(CrossEventRelation, creator):
                event_ids = (
                    (relation.parent_pack_id(), relation.parent_id()),
                    (relation.child_pack_id(), relation.child_id()),
                )

                # Pair index correspond to each column of the MACE matrix.
                if event_ids not in self.event_pair_indices:
                    pair_index = len(self.event_pair_indices)
                    self.event_pair_indices[event_ids] = pair_index
                else:
                    pair_index = self.event_pair_indices[event_ids]

                if relation.rel_type == 'coref':
                    self.mace_matrix_ones.add((pair_index, creator_id))

    def finish(self, _):
        num_row, num_col = len(self.event_pair_indices), len(
            self.annotator_indices)

        if num_row > 0 and num_col > 0:
            for r in range(num_row):
                sep = ''
                for c in range(num_col):
                    n = 1 if (r, c) in self.mace_matrix_ones else 0
                    sys.stdout.write(f'{sep}{n}')
                    sep = ','
                sys.stdout.write('\n')


if __name__ == '__main__':
    db_path = sys.argv[1]
    pipeline = Pipeline()
    pipeline.set_reader(StaveMultiDocSqlReader(), config={
        'stave_db_path': db_path
    })
    pipeline.add(MaceFormatCollector())
    pipeline.run()
