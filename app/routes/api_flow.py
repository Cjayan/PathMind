from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Flow, Product

api_flow_bp = Blueprint('api_flow', __name__)


@api_flow_bp.route('/', methods=['GET'])
def list_flows():
    product_id = request.args.get('product_id', type=int)
    status = request.args.get('status')
    is_pinned = request.args.get('is_pinned')
    mark_color = request.args.get('mark_color')

    query = Flow.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    if status:
        query = query.filter_by(status=status)
    if is_pinned is not None:
        query = query.filter_by(is_pinned=(is_pinned.lower() == 'true'))
    if mark_color:
        query = query.filter_by(mark_color=mark_color)

    flows = query.order_by(
        Flow.is_pinned.desc(),
        Flow.sort_order.asc(),
        Flow.updated_at.desc()
    ).all()
    return jsonify([f.to_dict() for f in flows])


@api_flow_bp.route('/', methods=['POST'])
def create_flow():
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '流程名称不能为空'}), 400
    if not data.get('product_id'):
        return jsonify({'error': '必须指定产品ID'}), 400

    product = Product.query.get(data['product_id'])
    if not product:
        return jsonify({'error': '产品不存在'}), 404

    name = data['name'].strip()
    existing = Flow.query.filter_by(product_id=data['product_id'], name=name).first()
    if existing:
        return jsonify({'error': f'该产品下已存在名为「{name}」的流程'}), 409

    flow = Flow(
        product_id=data['product_id'],
        name=name,
        status='recording'
    )
    db.session.add(flow)
    db.session.commit()
    return jsonify(flow.to_dict()), 201


@api_flow_bp.route('/<int:flow_id>', methods=['GET'])
def get_flow(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    return jsonify(flow.to_dict(include_steps=True))


@api_flow_bp.route('/<int:flow_id>', methods=['PUT'])
def update_flow(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400

    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify({'error': '流程名称不能为空'}), 400
        flow.name = name

    if 'is_pinned' in data:
        flow.is_pinned = bool(data['is_pinned'])

    if 'mark_color' in data:
        flow.mark_color = data['mark_color'] if data['mark_color'] else None

    db.session.commit()
    return jsonify(flow.to_dict())


@api_flow_bp.route('/<int:flow_id>', methods=['DELETE'])
def delete_flow(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    db.session.delete(flow)
    db.session.commit()
    return jsonify({'message': '流程已删除'})


@api_flow_bp.route('/<int:flow_id>/complete', methods=['POST'])
def complete_flow(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    flow.status = 'completed'
    db.session.commit()
    return jsonify(flow.to_dict())


@api_flow_bp.route('/reorder', methods=['POST'])
def reorder_flows():
    data = request.get_json()
    flow_ids = data.get('flow_ids', [])
    if not flow_ids:
        return jsonify({'error': '缺少 flow_ids'}), 400

    for index, flow_id in enumerate(flow_ids):
        flow = Flow.query.get(flow_id)
        if flow:
            flow.sort_order = index + 1

    db.session.commit()
    return jsonify({'message': '排序已更新'})
