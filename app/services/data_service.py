"""
data_service.py - Data export, import, and backup services
"""
import io
import json
import os
import shutil
import uuid as _uuid
import zipfile
from datetime import datetime, timezone, timedelta

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models import Product, Flow, Step
from app.config import config_manager


# ============================================================
# Export
# ============================================================

class DataExportService:

    def export_full(self):
        """全量导出：所有产品、流程、步骤 + 图片 -> ZIP BytesIO"""
        products = Product.query.all()
        flows = Flow.query.all()
        steps = Step.query.all()
        return self._build_zip(products, flows, steps, export_type='full')

    def export_incremental(self):
        """增量导出：仅导出上次导出后有变更的流程（及其全部步骤）"""
        changed_flows = Flow.query.filter(
            or_(
                Flow.exported_at.is_(None),
                Flow.updated_at > Flow.exported_at,
            )
        ).all()

        if not changed_flows:
            return None  # nothing to export

        # Gather related products and steps
        product_ids = set(f.product_id for f in changed_flows)
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        flow_ids = [f.id for f in changed_flows]
        steps = Step.query.filter(Step.flow_id.in_(flow_ids)).all()

        return self._build_zip(products, changed_flows, steps, export_type='incremental')

    def _build_zip(self, products, flows, steps, export_type):
        upload_dir = current_app.config['UPLOAD_DIR']
        sync_config = config_manager.get().get('sync', {})

        # Serialize data
        products_data = []
        for p in products:
            products_data.append({
                'uuid': p.uuid,
                'name': p.name,
                'description': p.description,
                'created_at': p.created_at.isoformat() if p.created_at else None,
                'updated_at': p.updated_at.isoformat() if p.updated_at else None,
            })

        # Build product uuid lookup
        product_uuid_map = {p.id: p.uuid for p in products}

        flows_data = []
        for f in flows:
            flows_data.append({
                'uuid': f.uuid,
                'product_uuid': product_uuid_map.get(f.product_id, ''),
                'name': f.name,
                'status': f.status,
                'ai_summary': f.ai_summary,
                'sort_order': f.sort_order or 0,
                'is_pinned': f.is_pinned or False,
                'mark_color': f.mark_color,
                'created_at': f.created_at.isoformat() if f.created_at else None,
                'updated_at': f.updated_at.isoformat() if f.updated_at else None,
            })

        flow_uuid_map = {f.id: f.uuid for f in flows}

        steps_data = []
        image_refs = []  # (src_path, zip_path)
        for s in steps:
            flow_uuid = flow_uuid_map.get(s.flow_id, '')
            img_ref = None
            if s.image_path:
                src = os.path.join(upload_dir, s.image_path)
                if os.path.exists(src):
                    zip_img_path = f"{flow_uuid}/{os.path.basename(s.image_path)}"
                    image_refs.append((src, zip_img_path))
                    img_ref = zip_img_path

            steps_data.append({
                'uuid': s.uuid,
                'flow_uuid': flow_uuid,
                'order': s.order,
                'image_ref': img_ref,
                'description': s.description,
                'score': s.score,
                'notes': s.notes,
                'ai_suggestion': s.ai_suggestion,
                'solution': s.solution,
                'ai_description': s.ai_description,
                'ai_interaction': s.ai_interaction,
                'ai_experience': s.ai_experience,
                'ai_improvement': s.ai_improvement,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
            })

        manifest = {
            'version': '1.0',
            'type': export_type,
            'source_instance_id': sync_config.get('instance_id', ''),
            'source_instance_name': sync_config.get('instance_name', 'unknown'),
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'stats': {
                'products': len(products_data),
                'flows': len(flows_data),
                'steps': len(steps_data),
                'images': len(image_refs),
            },
        }

        data_json = {
            'products': products_data,
            'flows': flows_data,
            'steps': steps_data,
        }

        # Build ZIP in memory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
            zf.writestr('data.json', json.dumps(data_json, ensure_ascii=False, indent=2))
            for src_path, zip_path in image_refs:
                zf.write(src_path, f'images/{zip_path}')

        buf.seek(0)

        # Update exported_at using raw SQL to avoid triggering onupdate on updated_at
        now = datetime.now(timezone.utc)
        flow_ids = [f.id for f in flows]
        if flow_ids:
            from sqlalchemy import text
            placeholders = ','.join([':id' + str(i) for i in range(len(flow_ids))])
            params = {'now': now}
            for i, fid in enumerate(flow_ids):
                params['id' + str(i)] = fid
            db.session.execute(
                text(f'UPDATE flows SET exported_at = :now WHERE id IN ({placeholders})'),
                params
            )
            db.session.commit()

        return buf


# ============================================================
# Import
# ============================================================

class DataImportService:

    def preview(self, zip_file):
        """
        解析上传的 ZIP, 比对本地数据, 返回变更预览.
        zip_file: file-like object
        返回: { preview_id, source, changes, warnings }
        """
        preview_id = str(_uuid.uuid4())
        data_dir = current_app.config['DATA_DIR']
        temp_dir = os.path.join(data_dir, 'temp', preview_id)
        os.makedirs(temp_dir, exist_ok=True)

        # Save and extract ZIP
        zip_path = os.path.join(temp_dir, 'upload.zip')
        zip_file.save(zip_path)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)
        except zipfile.BadZipFile:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise ValueError('无效的 ZIP 文件')

        # Parse manifest and data
        manifest_path = os.path.join(temp_dir, 'manifest.json')
        data_path = os.path.join(temp_dir, 'data.json')
        if not os.path.exists(manifest_path) or not os.path.exists(data_path):
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise ValueError('ZIP 中缺少 manifest.json 或 data.json')

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Compare with local data
        changes = {
            'products': {'add': [], 'update': [], 'unchanged': 0},
            'flows': {'add': [], 'update': [], 'unchanged': 0},
            'steps': {'add': 0, 'update': 0, 'unchanged': 0},
            'images': {'new': 0, 'replace': 0},
        }
        warnings = []

        # Products
        local_products = {p.uuid: p for p in Product.query.all()}
        local_products_by_name = {p.name: p for p in Product.query.all()}
        for rp in data.get('products', []):
            local = local_products.get(rp['uuid'])
            if not local:
                local = local_products_by_name.get(rp['name'])
            if not local:
                changes['products']['add'].append({'uuid': rp['uuid'], 'name': rp['name']})
            else:
                r_updated = rp.get('updated_at') or ''
                l_updated = local.updated_at.isoformat() if local.updated_at else ''
                if r_updated > l_updated:
                    changes['products']['update'].append({'uuid': rp['uuid'], 'name': rp['name']})
                else:
                    changes['products']['unchanged'] += 1

        # Flows
        local_flows = {f.uuid: f for f in Flow.query.all()}
        for rf in data.get('flows', []):
            local = local_flows.get(rf['uuid'])
            if not local:
                changes['flows']['add'].append({
                    'uuid': rf['uuid'],
                    'name': rf['name'],
                    'product_name': self._find_product_name(rf['product_uuid'], data['products']),
                })
            else:
                r_updated = rf.get('updated_at') or ''
                l_updated = local.updated_at.isoformat() if local.updated_at else ''
                if r_updated > l_updated:
                    changes['flows']['update'].append({'uuid': rf['uuid'], 'name': rf['name']})
                else:
                    changes['flows']['unchanged'] += 1

        # Steps
        local_steps = {s.uuid: s for s in Step.query.all()}
        for rs in data.get('steps', []):
            local = local_steps.get(rs['uuid'])
            if not local:
                changes['steps']['add'] += 1
                if rs.get('image_ref'):
                    changes['images']['new'] += 1
            else:
                r_updated = rs.get('updated_at') or ''
                l_updated = local.updated_at.isoformat() if local.updated_at else ''
                if r_updated > l_updated:
                    changes['steps']['update'] += 1
                    if rs.get('image_ref'):
                        changes['images']['replace'] += 1
                else:
                    changes['steps']['unchanged'] += 1

        return {
            'preview_id': preview_id,
            'source': {
                'instance_id': manifest.get('source_instance_id'),
                'instance_name': manifest.get('source_instance_name'),
                'exported_at': manifest.get('exported_at'),
                'type': manifest.get('type'),
            },
            'changes': changes,
            'warnings': warnings,
        }

    def execute(self, preview_id):
        """执行导入操作（先自动备份）"""
        data_dir = current_app.config['DATA_DIR']
        upload_dir = current_app.config['UPLOAD_DIR']
        temp_dir = os.path.join(data_dir, 'temp', preview_id)

        if not os.path.exists(temp_dir):
            raise ValueError('预览数据不存在或已过期，请重新上传')

        data_path = os.path.join(temp_dir, 'data.json')
        images_dir = os.path.join(temp_dir, 'images')

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Auto backup before import
        backup_svc = BackupService()
        backup_svc.create_backup('pre_import')

        added = {'products': 0, 'flows': 0, 'steps': 0}
        updated = {'products': 0, 'flows': 0, 'steps': 0}

        try:
            # --- Import Products ---
            local_products = {p.uuid: p for p in Product.query.all()}
            local_products_by_name = {p.name: p for p in Product.query.all()}
            product_uuid_to_id = {}

            for rp in data.get('products', []):
                local = local_products.get(rp['uuid']) or local_products_by_name.get(rp['name'])
                if not local:
                    p = Product(
                        uuid=rp['uuid'],
                        name=rp['name'],
                        description=rp.get('description'),
                    )
                    db.session.add(p)
                    db.session.flush()
                    product_uuid_to_id[rp['uuid']] = p.id
                    added['products'] += 1
                else:
                    product_uuid_to_id[rp['uuid']] = local.id
                    r_updated = rp.get('updated_at') or ''
                    l_updated = local.updated_at.isoformat() if local.updated_at else ''
                    if r_updated > l_updated:
                        if rp.get('name'):
                            local.name = rp['name']
                        if rp.get('description') is not None:
                            local.description = rp['description']
                        if not local.uuid or local.uuid != rp['uuid']:
                            local.uuid = rp['uuid']
                        updated['products'] += 1

            # --- Import Flows ---
            local_flows = {f.uuid: f for f in Flow.query.all()}
            flow_uuid_to_id = {}

            for rf in data.get('flows', []):
                pid = product_uuid_to_id.get(rf['product_uuid'])
                if not pid:
                    continue  # skip if product not found

                local = local_flows.get(rf['uuid'])
                if not local:
                    f = Flow(
                        uuid=rf['uuid'],
                        product_id=pid,
                        name=rf['name'],
                        status=rf.get('status', 'completed'),
                        ai_summary=rf.get('ai_summary'),
                        sort_order=rf.get('sort_order', 0),
                        is_pinned=rf.get('is_pinned', False),
                        mark_color=rf.get('mark_color'),
                    )
                    db.session.add(f)
                    db.session.flush()
                    flow_uuid_to_id[rf['uuid']] = f.id
                    added['flows'] += 1
                else:
                    flow_uuid_to_id[rf['uuid']] = local.id
                    r_updated = rf.get('updated_at') or ''
                    l_updated = local.updated_at.isoformat() if local.updated_at else ''
                    if r_updated > l_updated:
                        local.name = rf['name']
                        local.status = rf.get('status', local.status)
                        local.ai_summary = rf.get('ai_summary', local.ai_summary)
                        local.sort_order = rf.get('sort_order', local.sort_order)
                        local.is_pinned = rf.get('is_pinned', local.is_pinned)
                        local.mark_color = rf.get('mark_color', local.mark_color)
                        updated['flows'] += 1

            # --- Import Steps ---
            local_steps = {s.uuid: s for s in Step.query.all()}

            for rs in data.get('steps', []):
                fid = flow_uuid_to_id.get(rs['flow_uuid'])
                if not fid:
                    continue

                local = local_steps.get(rs['uuid'])
                if not local:
                    s = Step(
                        uuid=rs['uuid'],
                        flow_id=fid,
                        order=rs.get('order', 0),
                        description=rs.get('description'),
                        score=rs.get('score'),
                        notes=rs.get('notes'),
                        ai_suggestion=rs.get('ai_suggestion'),
                        solution=rs.get('solution'),
                        ai_description=rs.get('ai_description'),
                        ai_interaction=rs.get('ai_interaction'),
                        ai_experience=rs.get('ai_experience'),
                        ai_improvement=rs.get('ai_improvement'),
                    )
                    db.session.add(s)
                    db.session.flush()

                    # Copy image
                    if rs.get('image_ref'):
                        new_path = self._import_image(images_dir, rs['image_ref'], upload_dir, fid, s)
                        if new_path:
                            s.image_path = new_path

                    added['steps'] += 1
                else:
                    r_updated = rs.get('updated_at') or ''
                    l_updated = local.updated_at.isoformat() if local.updated_at else ''
                    if r_updated > l_updated:
                        local.flow_id = fid
                        local.order = rs.get('order', local.order)
                        local.description = rs.get('description', local.description)
                        local.score = rs.get('score', local.score)
                        local.notes = rs.get('notes', local.notes)
                        local.ai_suggestion = rs.get('ai_suggestion', local.ai_suggestion)
                        local.solution = rs.get('solution', local.solution)
                        local.ai_description = rs.get('ai_description', local.ai_description)
                        local.ai_interaction = rs.get('ai_interaction', local.ai_interaction)
                        local.ai_experience = rs.get('ai_experience', local.ai_experience)
                        local.ai_improvement = rs.get('ai_improvement', local.ai_improvement)

                        if rs.get('image_ref'):
                            new_path = self._import_image(images_dir, rs['image_ref'], upload_dir, fid, local)
                            if new_path:
                                local.image_path = new_path

                        updated['steps'] += 1

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            raise RuntimeError(f'导入失败: {e}')
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return {'added': added, 'updated': updated}

    def _import_image(self, images_dir, image_ref, upload_dir, flow_id, step):
        """Copy image from temp to upload directory"""
        src = os.path.join(images_dir, image_ref)
        if not os.path.exists(src):
            return None
        dest_dir = os.path.join(upload_dir, str(flow_id))
        os.makedirs(dest_dir, exist_ok=True)
        filename = f"step_{step.order:02d}_{_uuid.uuid4().hex[:8]}.png"
        dest = os.path.join(dest_dir, filename)
        shutil.copy2(src, dest)
        return f"{flow_id}/{filename}"

    @staticmethod
    def _find_product_name(product_uuid, products_list):
        for p in products_list:
            if p['uuid'] == product_uuid:
                return p['name']
        return '(未知产品)'


# ============================================================
# Backup
# ============================================================

class BackupService:

    def _backup_dir(self):
        data_dir = current_app.config['DATA_DIR']
        d = os.path.join(data_dir, 'backups')
        os.makedirs(d, exist_ok=True)
        return d

    def create_backup(self, reason='manual'):
        """创建备份：复制 app.db + uploads/ 到 backups/{timestamp}_{reason}/"""
        data_dir = current_app.config['DATA_DIR']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = f"{timestamp}_{reason}"
        backup_path = os.path.join(self._backup_dir(), backup_id)
        os.makedirs(backup_path, exist_ok=True)

        # Copy database
        db_src = os.path.join(data_dir, 'app.db')
        if os.path.exists(db_src):
            shutil.copy2(db_src, os.path.join(backup_path, 'app.db'))

        # Copy uploads
        uploads_src = os.path.join(data_dir, 'uploads')
        uploads_dest = os.path.join(backup_path, 'uploads')
        if os.path.exists(uploads_src):
            shutil.copytree(uploads_src, uploads_dest)

        # Write metadata
        meta = {
            'backup_id': backup_id,
            'reason': reason,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'db_size': os.path.getsize(db_src) if os.path.exists(db_src) else 0,
        }
        with open(os.path.join(backup_path, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Cleanup old backups
        self.cleanup_old_backups()

        return backup_id

    def list_backups(self):
        """列出所有备份"""
        backup_dir = self._backup_dir()
        backups = []
        if not os.path.exists(backup_dir):
            return backups

        for name in sorted(os.listdir(backup_dir), reverse=True):
            meta_path = os.path.join(backup_dir, name, 'meta.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                backups.append(meta)
            else:
                backups.append({
                    'backup_id': name,
                    'reason': 'unknown',
                    'created_at': None,
                })
        return backups

    def restore_backup(self, backup_id):
        """从备份恢复"""
        data_dir = current_app.config['DATA_DIR']
        backup_path = os.path.join(self._backup_dir(), backup_id)
        if not os.path.exists(backup_path):
            raise ValueError('备份不存在')

        # Create a safety backup before restoring
        self.create_backup('pre_restore')

        # Close db connections
        db.session.remove()
        db.engine.dispose()

        # Restore database
        db_backup = os.path.join(backup_path, 'app.db')
        db_dest = os.path.join(data_dir, 'app.db')
        if os.path.exists(db_backup):
            shutil.copy2(db_backup, db_dest)

        # Restore uploads
        uploads_backup = os.path.join(backup_path, 'uploads')
        uploads_dest = os.path.join(data_dir, 'uploads')
        if os.path.exists(uploads_backup):
            if os.path.exists(uploads_dest):
                shutil.rmtree(uploads_dest)
            shutil.copytree(uploads_backup, uploads_dest)

        return True

    def delete_backup(self, backup_id):
        """删除指定备份"""
        backup_path = os.path.join(self._backup_dir(), backup_id)
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
            return True
        return False

    def cleanup_old_backups(self):
        """清理超过保留天数的备份"""
        config = config_manager.get()
        keep_days = config.get('sync', {}).get('backup_keep_days', 3)
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)

        for meta in self.list_backups():
            if meta.get('created_at'):
                try:
                    created = datetime.fromisoformat(meta['created_at'])
                    if created < cutoff:
                        self.delete_backup(meta['backup_id'])
                except (ValueError, TypeError):
                    pass
