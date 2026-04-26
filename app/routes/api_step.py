import os
from flask import Blueprint, request, jsonify, current_app, send_file
from app.extensions import db
from app.models import Step, Flow
from app.services.image_service import save_upload_image

api_step_bp = Blueprint('api_step', __name__)


@api_step_bp.route('/', methods=['GET'])
def list_steps():
    flow_id = request.args.get('flow_id', type=int)
    if not flow_id:
        return jsonify({'error': '必须指定flow_id'}), 400
    steps = Step.query.filter_by(flow_id=flow_id).order_by(Step.order).all()
    return jsonify([s.to_dict() for s in steps])


@api_step_bp.route('/', methods=['POST'])
def create_step():
    flow_id = request.form.get('flow_id', type=int)
    if not flow_id:
        return jsonify({'error': '必须指定flow_id'}), 400

    flow = Flow.query.get(flow_id)
    if not flow:
        return jsonify({'error': '流程不存在'}), 404

    # Determine next order
    max_order = db.session.query(db.func.max(Step.order))\
        .filter_by(flow_id=flow_id).scalar()
    next_order = (max_order or 0) + 1

    # Handle image upload
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename:
            upload_dir = current_app.config['UPLOAD_DIR']
            image_path = save_upload_image(file, upload_dir, flow_id, next_order)

    step = Step(
        flow_id=flow_id,
        order=next_order,
        image_path=image_path,
        description=request.form.get('description', '').strip() or None,
        score=request.form.get('score', type=int),
        notes=request.form.get('notes', '').strip() or None,
        solution=request.form.get('solution', '').strip() or None,
    )
    db.session.add(step)
    db.session.commit()
    return jsonify(step.to_dict()), 201


@api_step_bp.route('/<int:step_id>', methods=['PUT'])
def update_step(step_id):
    step = Step.query.get_or_404(step_id)

    # Handle JSON or form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    if 'description' in data:
        step.description = data['description'].strip() if data['description'] else None
    if 'score' in data:
        score = int(data['score']) if data['score'] else None
        if score is not None and (score < 1 or score > 10):
            return jsonify({'error': '评分必须在1-10之间'}), 400
        step.score = score
    if 'notes' in data:
        step.notes = data['notes'].strip() if data['notes'] else None
    if 'solution' in data:
        step.solution = data['solution'].strip() if data['solution'] else None
    if 'ai_description' in data:
        step.ai_description = data['ai_description'].strip() if data['ai_description'] else None
    if 'ai_interaction' in data:
        step.ai_interaction = data['ai_interaction'].strip() if data['ai_interaction'] else None
    if 'ai_experience' in data:
        step.ai_experience = data['ai_experience'].strip() if data['ai_experience'] else None
    if 'ai_improvement' in data:
        step.ai_improvement = data['ai_improvement'].strip() if data['ai_improvement'] else None

    # Handle image replacement
    if request.files and 'image' in request.files:
        file = request.files['image']
        if file.filename:
            upload_dir = current_app.config['UPLOAD_DIR']
            # Delete old image
            if step.image_path:
                old_path = os.path.join(upload_dir, step.image_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            step.image_path = save_upload_image(file, upload_dir, step.flow_id, step.order)

    db.session.commit()
    return jsonify(step.to_dict())


@api_step_bp.route('/<int:step_id>', methods=['DELETE'])
def delete_step(step_id):
    step = Step.query.get_or_404(step_id)
    flow_id = step.flow_id

    # Delete image file
    if step.image_path:
        upload_dir = current_app.config['UPLOAD_DIR']
        old_path = os.path.join(upload_dir, step.image_path)
        if os.path.exists(old_path):
            os.remove(old_path)

    db.session.delete(step)
    db.session.commit()

    # Re-order remaining steps
    remaining = Step.query.filter_by(flow_id=flow_id).order_by(Step.order).all()
    for i, s in enumerate(remaining, 1):
        s.order = i
    db.session.commit()

    return jsonify({'message': '步骤已删除'})


@api_step_bp.route('/reorder', methods=['POST'])
def reorder_steps():
    data = request.get_json()
    if not data or 'step_ids' not in data:
        return jsonify({'error': '必须提供step_ids列表'}), 400

    step_ids = data['step_ids']
    for i, step_id in enumerate(step_ids, 1):
        step = Step.query.get(step_id)
        if step:
            step.order = i
    db.session.commit()
    return jsonify({'message': '排序已更新'})


@api_step_bp.route('/image/<path:image_path>', methods=['GET'])
def get_step_image(image_path):
    upload_dir = current_app.config['UPLOAD_DIR']
    full_path = os.path.join(upload_dir, image_path)
    if not os.path.exists(full_path):
        return jsonify({'error': '图片不存在'}), 404
    return send_file(full_path)
