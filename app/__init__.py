import os
import uuid as _uuid
from flask import Flask
from sqlalchemy import inspect, text
from app.extensions import db
from app.config import config_manager, BASE_DIR


def _auto_migrate(app):
    """检测并添加缺失的数据库列，并为空 uuid 填充值"""
    migrations = [
        ('steps', 'solution', 'TEXT'),
        ('products', 'uuid', 'VARCHAR(36)'),
        ('flows', 'uuid', 'VARCHAR(36)'),
        ('steps', 'uuid', 'VARCHAR(36)'),
        ('steps', 'updated_at', 'DATETIME'),
        ('flows', 'sort_order', 'INTEGER DEFAULT 0'),
        ('flows', 'is_pinned', 'BOOLEAN DEFAULT 0'),
        ('flows', 'mark_color', 'VARCHAR(20)'),
        ('steps', 'ai_description', 'TEXT'),
        ('steps', 'ai_experience', 'TEXT'),
        ('steps', 'ai_improvement', 'TEXT'),
        ('steps', 'ai_interaction', 'TEXT'),
    ]
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            for table, column, col_type in migrations:
                existing = {col['name'] for col in inspector.get_columns(table)}
                if column not in existing:
                    db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
                    app.logger.info(f'已自动添加列: {table}.{column}')
            db.session.commit()

            # Backfill NULL uuids
            for table in ('products', 'flows', 'steps'):
                rows = db.session.execute(text(f'SELECT id FROM {table} WHERE uuid IS NULL')).fetchall()
                for row in rows:
                    db.session.execute(
                        text(f'UPDATE {table} SET uuid = :uuid WHERE id = :id'),
                        {'uuid': str(_uuid.uuid4()), 'id': row[0]}
                    )
                if rows:
                    app.logger.info(f'已为 {table} 回填 {len(rows)} 个 uuid')
            db.session.commit()

            # Migrate score 1-5 → 1-10 (one-time)
            score_marker = os.path.join(BASE_DIR, 'data', '.migration_score10_done')
            if not os.path.exists(score_marker):
                # Check if ai_description column was just added (new migration)
                updated = db.session.execute(
                    text('UPDATE steps SET score = score * 2 WHERE score IS NOT NULL AND score <= 5')
                ).rowcount
                db.session.commit()
                if updated:
                    app.logger.info(f'已将 {updated} 个步骤的评分从 1-5 映射到 1-10')
                os.makedirs(os.path.dirname(score_marker), exist_ok=True)
                with open(score_marker, 'w') as f:
                    f.write('done')
    except Exception as e:
        app.logger.warning(f'自动迁移失败: {e}')


def create_app():
    config = config_manager.load()

    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))

    # Database config
    data_dir = os.path.join(BASE_DIR, 'data')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'uploads'), exist_ok=True)

    db_path = os.path.join(data_dir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

    # Store config and paths in app
    app.config['APP_CONFIG'] = config
    app.config['DATA_DIR'] = data_dir
    app.config['UPLOAD_DIR'] = os.path.join(data_dir, 'uploads')

    # Init extensions
    db.init_app(app)

    # Register blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Create tables
    with app.app_context():
        from app import models  # noqa: F401 - ensure models are loaded
        db.create_all()

    # Auto-migrate: add missing columns to existing databases
    _auto_migrate(app)

    # Ensure sync instance_id exists
    _ensure_instance_id()

    # Clean temp directory from previous sessions
    _clean_temp(data_dir)

    return app


def _ensure_instance_id():
    """首次启动时自动生成安装实例 ID"""
    config = config_manager.get()
    sync = config.get('sync', {})
    if not sync.get('instance_id'):
        sync['instance_id'] = str(_uuid.uuid4())
        if not sync.get('instance_name'):
            sync['instance_name'] = 'default'
        if not sync.get('backup_keep_days'):
            sync['backup_keep_days'] = 3
        config['sync'] = sync
        config_manager.save(config)


def _clean_temp(data_dir):
    """清理临时导入目录"""
    import shutil
    temp_dir = os.path.join(data_dir, 'temp')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
