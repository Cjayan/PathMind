import sys
from flask import Blueprint, render_template
from app.models import Product, Flow

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    return render_template('index.html')


@pages_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)


@pages_bp.route('/flow/<int:flow_id>/record')
def flow_record(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    return render_template('flow_record.html', flow=flow)


@pages_bp.route('/flow/<int:flow_id>/view')
def flow_view(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    return render_template('flow_view.html', flow=flow)


@pages_bp.route('/flow/<int:flow_id>/summary')
def flow_summary(flow_id):
    flow = Flow.query.get_or_404(flow_id)
    return render_template('summary_view.html', flow=flow)


@pages_bp.route('/settings')
def settings():
    return render_template('settings.html', platform=sys.platform)


@pages_bp.route('/flows')
def flows_list():
    products = Product.query.order_by(Product.name).all()
    return render_template('flows.html', products=products)
