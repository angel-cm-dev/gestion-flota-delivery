"""Esquema inicial: usuarios, vehículos, conductores, rutas, pedidos, mantenimiento y combustible.

Revision ID: 0001
Revises: 
Create Date: 2026-11-01 16:13:28.037658
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('vehicles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('plate', sa.String(length=10), nullable=False),
    sa.Column('brand', sa.String(length=60), nullable=False),
    sa.Column('model', sa.String(length=60), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('vehicle_type', sa.String(length=20), nullable=False),
    sa.Column('fuel_type', sa.String(length=20), nullable=False),
    sa.Column('capacity_kg', sa.Float(), nullable=False),
    sa.Column('odometer_km', sa.Integer(), nullable=False),
    sa.Column('soat_expiry', sa.Date(), nullable=False),
    sa.Column('tech_review_expiry', sa.Date(), nullable=False),
    sa.Column('maintenance_interval_km', sa.Integer(), nullable=False),
    sa.Column('last_maintenance_km', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('capacity_kg > 0', name='ck_vehicles_capacity_positive'),
    sa.CheckConstraint('odometer_km >= 0', name='ck_vehicles_odometer_non_negative'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_vehicles_plate'), ['plate'], unique=True)
        batch_op.create_index(batch_op.f('ix_vehicles_status'), ['status'], unique=False)

    op.create_table('drivers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('dni', sa.String(length=8), nullable=False),
    sa.Column('phone', sa.String(length=15), nullable=False),
    sa.Column('license_number', sa.String(length=9), nullable=False),
    sa.Column('license_category', sa.String(length=10), nullable=False),
    sa.Column('license_expiry', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dni'),
    sa.UniqueConstraint('license_number'),
    sa.UniqueConstraint('user_id')
    )
    with op.batch_alter_table('drivers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_drivers_status'), ['status'], unique=False)

    op.create_table('maintenance_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('odometer_km', sa.Integer(), nullable=False),
    sa.Column('cost', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('workshop', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_maintenance_records_vehicle_id'), ['vehicle_id'], unique=False)

    op.create_table('fuel_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('driver_id', sa.Integer(), nullable=True),
    sa.Column('fill_date', sa.Date(), nullable=False),
    sa.Column('liters', sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=False),
    sa.Column('total_cost', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
    sa.Column('odometer_km', sa.Integer(), nullable=False),
    sa.Column('station', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('liters > 0', name='ck_fuel_liters_positive'),
    sa.CheckConstraint('total_cost >= 0', name='ck_fuel_cost_non_negative'),
    sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('fuel_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fuel_logs_vehicle_id'), ['vehicle_id'], unique=False)

    op.create_table('routes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('route_date', sa.Date(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('driver_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('depot_lat', sa.Float(), nullable=False),
    sa.Column('depot_lng', sa.Float(), nullable=False),
    sa.Column('total_distance_km', sa.Float(), nullable=False),
    sa.Column('total_weight_kg', sa.Float(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    with op.batch_alter_table('routes', schema=None) as batch_op:
        batch_op.create_index('ix_routes_date_status', ['route_date', 'status'], unique=False)

    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('customer_name', sa.String(length=120), nullable=False),
    sa.Column('customer_phone', sa.String(length=15), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=False),
    sa.Column('district', sa.String(length=80), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('scheduled_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('route_id', sa.Integer(), nullable=True),
    sa.Column('stop_sequence', sa.Integer(), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('proof_note', sa.Text(), nullable=True),
    sa.Column('proof_photo_path', sa.String(length=255), nullable=True),
    sa.Column('failure_reason', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('latitude BETWEEN -90 AND 90', name='ck_orders_lat'),
    sa.CheckConstraint('longitude BETWEEN -180 AND 180', name='ck_orders_lng'),
    sa.CheckConstraint('weight_kg > 0', name='ck_orders_weight_positive'),
    sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index('ix_orders_date_status', ['scheduled_date', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_district'), ['district'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_route_id'), ['route_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_route_id'))
        batch_op.drop_index(batch_op.f('ix_orders_district'))
        batch_op.drop_index('ix_orders_date_status')

    op.drop_table('orders')
    with op.batch_alter_table('routes', schema=None) as batch_op:
        batch_op.drop_index('ix_routes_date_status')

    op.drop_table('routes')
    with op.batch_alter_table('fuel_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fuel_logs_vehicle_id'))

    op.drop_table('fuel_logs')
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_maintenance_records_vehicle_id'))

    op.drop_table('maintenance_records')
    with op.batch_alter_table('drivers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_drivers_status'))

    op.drop_table('drivers')
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_vehicles_status'))
        batch_op.drop_index(batch_op.f('ix_vehicles_plate'))

    op.drop_table('vehicles')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
