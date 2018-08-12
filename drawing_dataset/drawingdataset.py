from pathlib import Path
import logging
import json
import pickle

class DrawingDataset(object):
    """
    interface to the drawing dataset
    """

    def __init__(self, path_to_drawing_dataset, path_to_label_mapping):
        self._path = Path(path_to_drawing_dataset)
        self._categories_filepath = self._path / 'categories.txt'
        self._category_mapping_filepath = path_to_label_mapping
        self._categories = []
        self._category_mapping = dict()
        self._logger = logging.getLogger(self.__class__.__name__)

    def setup(self):
        try:
            with open(self._category_mapping_filepath, encoding='utf-8') as data_file:
                 self._category_mapping = json.loads(data_file.read())
            # with jsonlines.open(self._category_mapping_filepath, mode='r') as reader:
            #     self._category_mapping = reader.read()
        except IOError as e:
            self._logger.exception(e)
            print('label_mapping.jsonl not found')
            raise e
        self._categories = self.load_categories(self._path)

    def load_categories(self, path):
        files = Path(path).glob('*.p')
        categories = [f.stem for f in files]
        return categories

    def get_drawing(self, name, index):
        """get a drawing by name and index starting from 0.
        """
        try:
            if name not in self._categories:
                # try and get the closest matching drawing. If nothing suitable foumd then return a scorpion
                name = self._category_mapping.get(name, 'scorpion')
            if index < 1 or index >= 100 or not isinstance(index, int):
                raise ValueError('index', index, ';index must be integer > 0 and < 100')
            pickleFile = str(self._path / Path(name).with_suffix('.p'))
            with open(pickleFile,'rb') as f:
                image = pickle.load(f)[index]
            return image
        except ValueError as e:
            self.log.exception(e)
            raise e
            
    @property
    def categories(self):
        return self._categories
