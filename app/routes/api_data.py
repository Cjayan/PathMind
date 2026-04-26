"""
api_data.py - Data import/export and backup API endpoints
"""
from flask import Blueprint, request, jsonify, send_file
from app.services.data_service import DataExportService, DataImportService, BackupService

api_data_bp = Blueprint('api_data', __name__)


@api_data_bp.route('/export', methods=['POST'])
def export_data():
    data = request.get_json() or {}
    export_type = data.get('type', 'full')

    export_svc = DataExportService()

    if export_type == 'incremental':
        buf = export_svc.export_incremental()
        if buf is None:
            return jsonify({'message': '没有新的变更需要导出'}), 200
    else:
        buf = export_svc.export_full()

    from datetime import datetime
    filename = f"export_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename,
    )


@api_data_bp.route('/import-preview', methods=['POST'])
def import_preview():
    if 'file' not in request.files:
        return jsonify({'error': '请上传 ZIP 文件'}), 400

    file = request.files['file']
    if not file.filename.endswith('.zip'):
        return jsonify({'error': '仅支持 ZIP 文件'}), 400

    import_svc = DataImportService()
    try:
        preview = import_svc.preview(file)
        return jsonify(preview)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_data_bp.route('/import', methods=['POST'])
def import_data():
    data = request.get_json()
    if not data or not data.get('preview_id'):
        return jsonify({'error': '缺少 preview_id'}), 400

    import_svc = DataImportService()
    try:
        result = import_svc.execute(data['preview_id'])
        return jsonify({
            'message': '导入完成',
            'added': result['added'],
            'updated': result['updated'],
        })
    except (ValueError, RuntimeError) as e:
        return jsonify({'error': str(e)}), 400


@api_data_bp.route('/backups', methods=['GET'])
def list_backups():
    svc = BackupService()
    return jsonify(svc.list_backups())


@api_data_bp.route('/backups', methods=['POST'])
def create_backup():
    svc = BackupService()
    backup_id = svc.create_backup('manual')
    return jsonify({'message': '备份已创建', 'backup_id': backup_id}), 201


@api_data_bp.route('/restore', methods=['POST'])
def restore_backup():
    data = request.get_json()
    if not data or not data.get('backup_id'):
        return jsonify({'error': '缺少 backup_id'}), 400

    svc = BackupService()
    try:
        svc.restore_backup(data['backup_id'])
        return jsonify({'message': '已从备份恢复，请刷新页面'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_data_bp.route('/backups/<backup_id>', methods=['DELETE'])
def delete_backup(backup_id):
    svc = BackupService()
    if svc.delete_backup(backup_id):
        return jsonify({'message': '备份已删除'})
    return jsonify({'error': '备份不存在'}), 404
