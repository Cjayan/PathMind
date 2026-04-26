from flask import Blueprint, jsonify
from app.models import Flow, Product
from app.config import config_manager
from app.services.export_service import ExportService

api_export_bp = Blueprint('api_export', __name__)


@api_export_bp.route('/flow/<int:flow_id>', methods=['POST'])
def export_flow(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    obsidian_config = config_manager.get_obsidian_config()

    if not obsidian_config.get('vault_path'):
        return jsonify({'error': '请先在设置中配置Obsidian Vault路径'}), 400

    try:
        export_svc = ExportService(obsidian_config)
        result = export_svc.export_flow(flow)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@api_export_bp.route('/product/<int:product_id>', methods=['POST'])
def export_product(product_id):
    product = Product.query.get_or_404(product_id)
    obsidian_config = config_manager.get_obsidian_config()

    if not obsidian_config.get('vault_path'):
        return jsonify({'error': '请先在设置中配置Obsidian Vault路径'}), 400

    try:
        export_svc = ExportService(obsidian_config)
        results = []
        for flow in product.flows:
            result = export_svc.export_flow(flow)
            results.append(result)
        export_svc.update_product_overview(product)
        return jsonify({'message': f'已导出 {len(results)} 个流程', 'results': results})
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500
