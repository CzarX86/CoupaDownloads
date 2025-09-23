"""Dataset generation for the training pipeline."""
from __future__ import annotations

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import repository


class DatasetBuilder:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def build_from_annotations(self) -> list[dict]:
        """Builds a dataset from completed annotations."""
        annotations = await repository.get_completed_annotations(self.db_session)
        
        records = []
        for annotation in annotations:
            if annotation.latest_payload:
                records.append(
                    {
                        "document_id": annotation.document_id,
                        "filename": annotation.document.filename,
                        "payload": annotation.latest_payload,
                    }
                )
        return records

    async def to_dataframe(self, data: list[dict]) -> pd.DataFrame:
        """Converts the dataset to a pandas DataFrame."""
        return pd.DataFrame(data)