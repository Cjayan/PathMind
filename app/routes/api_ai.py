from flask import Blueprint, request, jsonify
from app.config import config_manager
from app.services.ai_service import AIService
from app.services.image_service import get_image_base64, compress_image_for_ai
from app.models import Flow, Step
from app.extensions import db

api_ai_bp = Blueprint('api_ai', __name__)


@api_ai_bp.route('/analyze-screenshot', methods=['POST'])
def analyze_screenshot():
    ai_config = config_manager.get_ai_config()
    if not ai_config.get('api_key'):
        return jsonify({'error': '请先在设置中配置AI API密钥'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400

    image_base64 = data.get('image_base64')
    if not image_base64:
        return jsonify({'error': '未提供截图数据'}), 400

    context = data.get('context', {})

    try:
        ai = AIService(ai_config)
        result = ai.analyze_screenshot(image_base64, context)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'AI分析失败: {str(e)}'}), 500


@api_ai_bp.route('/generate-summary/<int:flow_id>', methods=['POST'])
def generate_summary(flow_id):
    ai_config = config_manager.get_ai_config()
    if not ai_config.get('api_key'):
        return jsonify({'error': '请先在设置中配置AI API密钥'}), 400

    flow = Flow.query.get_or_404(flow_id)
    steps = Step.query.filter_by(flow_id=flow_id).order_by(Step.order).all()

    if not steps:
        return jsonify({'error': '该流程没有任何步骤，无法生成总结'}), 400

    flow_data = {
        'product_name': flow.product.name,
        'flow_name': flow.name,
        'steps': [{
            'order': s.order,
            'description': s.description or '(无描述)',
            'score': s.score,
            'notes': s.notes or '',
        } for s in steps]
    }

    try:
        ai = AIService(ai_config)
        summary = ai.generate_flow_summary(flow_data)
        flow.ai_summary = summary
        db.session.commit()
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': f'AI总结生成失败: {str(e)}'}), 500


@api_ai_bp.route('/generate-step-comment', methods=['POST'])
def generate_step_comment():
    ai_config = config_manager.get_ai_config()
    if not ai_config.get('api_key'):
        return jsonify({'error': '请先在设置中配置AI API密钥'}), 400

    data = request.get_json()
    if not data or not data.get('step_id'):
        return jsonify({'error': '缺少 step_id'}), 400

    step = Step.query.get_or_404(data['step_id'])
    flow = Flow.query.get_or_404(step.flow_id)

    if not step.image_path:
        return jsonify({'error': '该步骤没有截图，无法生成评论'}), 400

    # Get image
    from flask import current_app
    upload_dir = current_app.config['UPLOAD_DIR']
    try:
        image_base64 = compress_image_for_ai(upload_dir, step.image_path)
    except Exception as e:
        return jsonify({'error': f'读取截图失败: {str(e)}'}), 500

    # Build context with previous steps
    prev_steps = Step.query.filter(
        Step.flow_id == flow.id, Step.order < step.order
    ).order_by(Step.order).all()
    previous_summary = '\n'.join(
        f"步骤{s.order}: {s.description or '(无描述)'}" for s in prev_steps
    )

    context = {
        'product_name': flow.product.name if flow.product else '未知产品',
        'flow_name': flow.name,
        'step_order': step.order,
        'step_title': step.description or '',
        'previous_steps': previous_summary,
    }

    try:
        ai = AIService(ai_config)
        result = ai.generate_step_comment(image_base64, context)

        # Save to database
        step.ai_interaction = result.get('ai_interaction', '')
        step.ai_experience = result.get('ai_experience', '')
        step.ai_improvement = result.get('ai_improvement', '')
        step.score = result.get('score', step.score)
        db.session.commit()

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'AI评论生成失败: {str(e)}'}), 500


@api_ai_bp.route('/test-connection', methods=['POST'])
def test_connection():
    ai_config = config_manager.get_ai_config()
    if not ai_config.get('api_key'):
        return jsonify({'error': '请先配置API密钥'}), 400

    try:
        ai = AIService(ai_config)
        result = ai.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'连接测试失败: {str(e)}'}), 500
