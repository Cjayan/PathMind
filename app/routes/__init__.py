def register_blueprints(app):
    from app.routes.pages import pages_bp
    from app.routes.api_product import api_product_bp
    from app.routes.api_flow import api_flow_bp
    from app.routes.api_step import api_step_bp
    from app.routes.api_ai import api_ai_bp
    from app.routes.api_export import api_export_bp
    from app.routes.api_config import api_config_bp
    from app.routes.api_search import api_search_bp
    from app.routes.api_data import api_data_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_product_bp, url_prefix='/api/products')
    app.register_blueprint(api_flow_bp, url_prefix='/api/flows')
    app.register_blueprint(api_step_bp, url_prefix='/api/steps')
    app.register_blueprint(api_ai_bp, url_prefix='/api/ai')
    app.register_blueprint(api_export_bp, url_prefix='/api/export')
    app.register_blueprint(api_config_bp, url_prefix='/api/config')
    app.register_blueprint(api_search_bp, url_prefix='/api/search')
    app.register_blueprint(api_data_bp, url_prefix='/api/data')
