from app.services.ai_service import AIService
from app.services.image_service import compress_image_for_ai
from app.models import Flow, Step
from app.extensions import db
from app.config import config_manager


def generate_and_save_summary(flow_id, upload_dir):
    """Generate AI summary for a flow and save to database."""
    flow = Flow.query.get(flow_id)
    if not flow:
        raise ValueError(f"流程 {flow_id} 不存在")

    steps = Step.query.filter_by(flow_id=flow_id).order_by(Step.order).all()
    if not steps:
        raise ValueError("该流程没有任何步骤")

    ai_config = config_manager.get_ai_config()
    ai = AIService(ai_config)

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

    summary = ai.generate_flow_summary(flow_data)
    flow.ai_summary = summary
    db.session.commit()
    return summary
