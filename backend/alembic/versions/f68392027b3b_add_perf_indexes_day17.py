"""add_perf_indexes_day17

Revision ID: f68392027b3b
Revises: b234201d53b1
Create Date: 2026-06-23 10:39:00.691978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f68392027b3b'
down_revision: Union[str, Sequence[str], None] = 'b234201d53b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_index(
        "ix_alerts_created_at", "alerts", ["created_at"], postgresql_using="btree"
    )
    op.create_index(
        "ix_predictions_created_at", "predictions", ["created_at"], postgresql_using="btree"
    )

def downgrade():
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_predictions_created_at", table_name="predictions")
