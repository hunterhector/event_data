from forte.pipeline import Pipeline
from forte.processors.writers import DocIdJsonPackWriter
from readers.event_reader import EventReader

input_path = 'sample_data/input'
output_path = 'sample_data/output'

pl = Pipeline()
pl.set_reader(EventReader())

pl.add_processor(
    DocIdJsonPackWriter(),
    {
        'output_dir': output_path
    },
)

pl.initialize()
pl.run(input_path)
