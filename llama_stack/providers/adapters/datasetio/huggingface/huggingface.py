# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
from typing import List, Optional

from llama_stack.apis.datasetio import *  # noqa: F403


import datasets as hf_datasets
from llama_stack.providers.datatypes import DatasetsProtocolPrivate
from llama_stack.providers.utils.datasetio.url_utils import get_dataframe_from_url

from .config import HuggingfaceDatasetIOConfig


def load_hf_dataset(dataset_def: DatasetDef):
    if dataset_def.metadata.get("path", None):
        return hf_datasets.load_dataset(**dataset_def.metadata)

    df = get_dataframe_from_url(dataset_def.url)

    if df is None:
        raise ValueError(f"Failed to load dataset from {dataset_def.url}")

    dataset = hf_datasets.Dataset.from_pandas(df)
    return dataset


class HuggingfaceDatasetIOImpl(DatasetIO, DatasetsProtocolPrivate):
    def __init__(self, config: HuggingfaceDatasetIOConfig) -> None:
        self.config = config
        # local registry for keeping track of datasets within the provider
        self.dataset_infos = {}

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None: ...

    async def register_dataset(
        self,
        dataset_def: DatasetDef,
    ) -> None:
        self.dataset_infos[dataset_def.identifier] = dataset_def

    async def list_datasets(self) -> List[DatasetDef]:
        return list(self.dataset_infos.values())

    async def get_rows_paginated(
        self,
        dataset_id: str,
        rows_in_page: int,
        page_token: Optional[str] = None,
        filter_condition: Optional[str] = None,
    ) -> PaginatedRowsResult:
        dataset_def = self.dataset_infos[dataset_id]
        loaded_dataset = load_hf_dataset(dataset_def)

        if page_token and not page_token.isnumeric():
            raise ValueError("Invalid page_token")

        if page_token is None or len(page_token) == 0:
            next_page_token = 0
        else:
            next_page_token = int(page_token)

        start = next_page_token
        if rows_in_page == -1:
            end = len(loaded_dataset)
        else:
            end = min(start + rows_in_page, len(loaded_dataset))

        rows = [loaded_dataset[i] for i in range(start, end)]

        return PaginatedRowsResult(
            rows=rows,
            total_count=len(rows),
            next_page_token=str(end),
        )
