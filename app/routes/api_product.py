from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Product

api_product_bp = Blueprint('api_product', __name__)


@api_product_bp.route('/', methods=['GET'])
def list_products():
    products = Product.query.order_by(Product.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in products])


@api_product_bp.route('/', methods=['POST'])
def create_product():
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '产品名称不能为空'}), 400

    product = Product(
        name=data['name'].strip(),
        description=data.get('description', '').strip() or None
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@api_product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


@api_product_bp.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400

    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify({'error': '产品名称不能为空'}), 400
        product.name = name
    if 'description' in data:
        product.description = data['description'].strip() or None

    db.session.commit()
    return jsonify(product.to_dict())


@api_product_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': '产品已删除'})
