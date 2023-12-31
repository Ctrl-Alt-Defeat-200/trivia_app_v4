"""empty message

Revision ID: 023ff50ae829
Revises: 
Create Date: 2023-10-10 20:31:08.857635

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023ff50ae829'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_active')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.BOOLEAN(), nullable=False))

    # ### end Alembic commands ###
