import json
import os
from PIL import Image
from typing import Dict, Any, List, Optional

UNKNOWN_IMG = Image.new("RGBA", (1, 1), (0, 0, 0, 0))

class LocalAssetLoader:
    def __init__(self, resource_path: str, region: str = 'jp'):
        self.resource_path = resource_path
        self.asset_path = os.path.join(resource_path, 'assets', region)
        self.static_path = os.path.join(resource_path, 'static_images')

        if not os.path.isdir(self.asset_path):
            raise FileNotFoundError(f"Asset path does not exist: {self.asset_path}")

        self.metadata_path = os.path.join(resource_path, 'metadata', region)
        self.region = region
        self._image_cache: Dict[str, Image.Image] = {}

        self.md = self.MasterDataLocal(self)
        self.rip = self
        self.static_imgs = self

    def get(self, path: str, **kwargs) -> Image.Image:
        path_no_rip = path.replace("_rip", "")
        if path_no_rip in self._image_cache: return self._image_cache[path_no_rip].copy()

        file_path_static = os.path.join(self.static_path, path_no_rip)
        try:
            image = Image.open(file_path_static).convert("RGBA")
            self._image_cache[path_no_rip] = image
            return image.copy()
        except FileNotFoundError:
            return self.img(path_no_rip, **kwargs)
        except Exception:
            return UNKNOWN_IMG

    def img(self, path: str, **kwargs) -> Image.Image:
        path_no_rip = path.replace("_rip", "")
        if path_no_rip in self._image_cache: return self._image_cache[path_no_rip].copy()

        file_path = os.path.join(self.asset_path, path_no_rip)
        try:
            image = Image.open(file_path).convert("RGBA")
            self._image_cache[path_no_rip] = image
            return image.copy()
        except FileNotFoundError:
            return UNKNOWN_IMG
        except Exception:
            return UNKNOWN_IMG

    class MasterDataLocal:
        def __init__(self, loader: 'LocalAssetLoader'):
            self._loader = loader
            self._tables: Dict[str, 'LocalAssetLoader.MasterDataTable'] = {}

        def __getattr__(self, name: str) -> 'LocalAssetLoader.MasterDataTable':
            if name not in self._tables:
                self._tables[name] = LocalAssetLoader.MasterDataTable(self._loader, name)
            return self._tables[name]

    class MasterDataTable:
        def __init__(self, loader: 'LocalAssetLoader', table_name: str):
            self._loader = loader
            self._table_name = table_name
            self._data: Optional[List[Dict[str, Any]]] = None
            self._index_by_id: Optional[Dict[int, Any]] = None

        def _load_data(self) -> List[Dict[str, Any]]:
            if self._data is not None: return self._data

            parts = self._table_name.split('_')
            camel_case_name = parts[0] + ''.join(p.capitalize() for p in parts[1:])

            file_path = os.path.join(self._loader.resource_path, 'metadata', self._loader.region, f"{camel_case_name}.json")

            if not os.path.exists(file_path):
                print(f"Warning: Metadata file not found: {file_path}")
                self._data = []
                return self._data

            try:
                with open(file_path, 'r', encoding='utf-8') as f: self._data = json.load(f)
                return self._data
            except Exception as e:
                print(f"Warning: Error reading metadata file {file_path}: {e}")
                self._data = []
                return self._data

        def _build_index_by_id(self):
            if self._index_by_id is not None: return
            self._index_by_id = {}
            data = self._load_data()
            if not isinstance(data, list): return
            for item in data:
                if isinstance(item, dict) and 'id' in item:
                    self._index_by_id[item['id']] = item

        def find_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
            self._build_index_by_id()
            return self._index_by_id.get(record_id)