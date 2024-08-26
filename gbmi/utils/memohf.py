import pickle
import time
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
    TypeVar,
)

from datasets import Dataset, DatasetDict, load_dataset
from datasets.data_files import EmptyDatasetError
from datasets.exceptions import DataFilesNotFoundError

from gbmi.utils.hashing import get_hash_ascii

PUSH_INTERVAL: float = (
    10  # Push only if more than 10 seconds have passed since the last push
)

last_push_time: Dict[str, float] = {}
memohf_cache: Dict[str, Dict[str, Any]] = {}

T = TypeVar("T")
K1 = TypeVar("K1")
K2 = TypeVar("K2")
V = TypeVar("V")
K = TypeVar("K")


def should_push(repo_id: str) -> bool:
    """Determines if we should push based on the last push time."""
    last_time = last_push_time.get(repo_id, 0)
    return time.time() - last_time > PUSH_INTERVAL


def update_last_push_time(repo_id: str):
    """Updates the last push time for the given repo."""
    last_push_time[repo_id] = time.time()


class HFOpenDictLike(dict):
    """A dict-like object that supports push_to_hub."""

    def __init__(self, dataset: DatasetDict, repo_id: str):
        super().__init__()
        self.repo_id = repo_id
        self.dataset = dataset
        self.update(self._load_db())  # Load the data and update the internal dict
        self._reset_hash()

    def _gethash(self):
        return get_hash_ascii(tuple(self.items()))

    def _reset_hash(self):
        """Resets the hash to the current state of the database."""
        self.init_hash = self._gethash()

    def _load_db(self) -> Dict[str, Any]:
        """Loads the dataset data from the Hugging Face hub based on the mode."""
        return {
            key: pickle.loads(self.dataset[key]["data"][0])
            for key in self.dataset.keys()
        }

    def push_to_hub(self):
        """Pushes the current state of the database back to the Hugging Face hub."""
        for key, data in self.items():
            serialized_data = pickle.dumps(data)
            self.dataset[key] = Dataset.from_dict({"data": [serialized_data]})
        self.dataset.push_to_hub(self.repo_id)
        update_last_push_time(self.repo_id)
        self._reset_hash()

    @property
    def modified(self) -> bool:
        """Determines if the database has been modified."""
        return self.init_hash != self._gethash()


@contextmanager
def hf_open(
    repo_id: str,
    name: Optional[str] = None,
    save: bool = True,
    **kwargs,
):
    """Context manager for opening a Hugging Face dataset in dict-like format."""
    try:
        # Load the dataset and keep it in memory
        dataset = cast(
            DatasetDict, load_dataset(repo_id, name=name, keep_in_memory=True, **kwargs)
        )
    except (EmptyDatasetError, DataFilesNotFoundError, ValueError):
        dataset = DatasetDict()

    db = HFOpenDictLike(dataset, repo_id)

    try:
        yield db
    finally:
        if save:
            db.push_to_hub()


def merge_subdicts(
    *dicts_keys: Tuple[dict[K1, dict[K2, V]], K1],
    default_factory: Callable[[], dict[K2, V]] = dict,
) -> dict[K2, V]:
    """Merges multiple sub dictionaries into a single dictionary."""
    (dict0, k0), *rest_dicts_keys = dicts_keys
    merged = dict0.setdefault(k0, default_factory())
    for d, k in rest_dicts_keys:
        old = d.setdefault(k, merged)
        if old is not merged:
            d[k] = merged
            merged.update(old)

    return merged


StorageMethod = Literal["single_data_file", "named_data_files", "data_splits"]


@contextmanager
def hf_open_staged(
    repo_id,
    storage_methods: Union[StorageMethod, Iterable[StorageMethod]] = "single_data_file",
    save: bool = True,
    **kwargs,
):
    """Context manager for opening a Hugging Face dataset in dict-like format."""
    if isinstance(storage_methods, str):
        storage_methods = [storage_methods]
    else:
        storage_methods = list(storage_methods)

    if "single_data_file" in storage_methods or "data_splits" in storage_methods:
        with hf_open(repo_id, save=save, **kwargs) as db:

            @contextmanager
            def inner(name: str):
                db_keys = []
                if "data_splits" in storage_methods:
                    db_keys.append((db, name))
                if "single_data_file" in storage_methods:
                    db_keys.append((db.setdefault("all", {}), name))
                if "named_data_files" in storage_methods:
                    with hf_open(repo_id, name=name, save=save, **kwargs) as db2:
                        db_keys.append((db2, "all"))
                        try:
                            yield merge_subdicts(*db_keys)
                        finally:
                            if save and should_push(repo_id):
                                if db.modified:
                                    db.push_to_hub()
                                if db2.modified:
                                    db2.push_to_hub()
                else:
                    try:
                        yield merge_subdicts(*db_keys)
                    finally:
                        if save and db.modified:
                            db.push_to_hub()

            yield inner
    else:
        assert "named_data_files" in storage_methods

        @contextmanager
        def inner(name: str):
            with hf_open(repo_id, name=name, save=save, **kwargs) as db:
                yield db.setdefault("all", {})

        yield inner


@contextmanager
def memohf_staged(
    repo_id: str,
    *,
    save: bool = True,
    storage_methods: Union[StorageMethod, Iterable[StorageMethod]] = "single_data_file",
    **kwargs,
):
    with hf_open_staged(
        repo_id, storage_methods=storage_methods, save=save, **kwargs
    ) as open_db:

        @contextmanager
        def inner(
            value: Callable,
            dataset_key: str,
            cache: Dict[str, Dict[str, Any]] = memohf_cache,
            get_hash: Callable = get_hash_ascii,
            get_hash_mem: Optional[Callable] = None,
            print_cache_miss: bool = False,
        ):
            mem_db = cache.setdefault(repo_id, {}).setdefault(dataset_key, {})
            if get_hash_mem is None:
                get_hash_mem = get_hash

            with open_db(dataset_key) as db:

                def delegate(*args, **kwargs):
                    mkey = get_hash_mem((args, kwargs))
                    try:
                        return mem_db[mkey]
                    except KeyError:
                        if print_cache_miss:
                            print(f"Cache miss (mem): {mkey}")
                        key = get_hash((args, kwargs))
                        try:
                            mem_db[mkey] = db[key]
                        except Exception as e:
                            if isinstance(e, KeyError):
                                if print_cache_miss:
                                    print(f"Cache miss (huggingface): {key}")
                            elif isinstance(e, (KeyboardInterrupt, SystemExit)):
                                raise e
                            else:
                                print(
                                    f"Error {e} in {dataset_key} in {repo_id} with key {key}"
                                )
                            if not isinstance(e, (KeyError, AttributeError)):
                                raise e
                            mem_db[mkey] = db[key] = value(*args, **kwargs)
                        return mem_db[mkey]

                yield delegate

        yield inner


def memohf(
    value: Callable,
    repo_id: str,
    dataset_key: str,
    *,
    cache: Dict[str, Dict[str, Any]] = memohf_cache,
    get_hash: Callable = get_hash_ascii,
    get_hash_mem: Optional[Callable] = None,
    print_cache_miss: bool = False,
    save: bool = True,
    storage_methods: Union[StorageMethod, Iterable[StorageMethod]] = "single_data_file",
    **kwargs,
):
    """Memoziation using huggingface + in-memory cache"""

    @contextmanager
    def open_db():
        with memohf_staged(
            repo_id, save=save, storage_methods=storage_methods, **kwargs
        ) as staged_db:
            with staged_db(
                value,
                dataset_key,
                cache=cache,
                get_hash=get_hash,
                get_hash_mem=get_hash_mem,
                print_cache_miss=print_cache_miss,
            ) as func:
                yield func

    return open_db


def uncache(
    *args,
    repo_id: str,
    dataset_key: str,
    storage_methods: Union[StorageMethod, Iterable[StorageMethod]] = "single_data_file",
    cache: Dict[str, Dict[str, Any]] = memohf_cache,
    get_hash: Callable = get_hash_ascii,
    get_hash_mem: Optional[Callable] = None,
    save: bool = True,
    load_dataset_kwargs: Dict[str, Any] = {},
    **kwargs,
):
    """Lightweight memoziation using shelve + in-memory cache"""
    mem_db = cache.setdefault(repo_id, {}).setdefault(dataset_key, {})
    if get_hash_mem is None:
        get_hash_mem = get_hash

    mkey = get_hash_mem((args, kwargs))
    if mkey in mem_db:
        del mem_db[mkey]

    key = get_hash((args, kwargs))

    with hf_open_staged(
        repo_id, storage_methods=storage_methods, save=save, **load_dataset_kwargs
    ) as open_db:
        with open_db(dataset_key) as db:
            if key in db:
                del db[key]
