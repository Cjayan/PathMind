import html
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from app.extensions import db
from app.models import Step, Flow, Product

api_search_bp = Blueprint('api_search', __name__)


def _escape_like(s):
    """Escape SQL LIKE wildcards."""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _make_snippet(text, keyword, context_chars=40):
    """Generate a text snippet with <mark> highlighted keyword."""
    if not text:
        return ''
    # HTML-escape the full text first
    safe_text = html.escape(text)
    safe_keyword = html.escape(keyword)

    lower_text = safe_text.lower()
    lower_kw = safe_keyword.lower()
    pos = lower_text.find(lower_kw)
    if pos == -1:
        return safe_text[:80] + ('...' if len(safe_text) > 80 else '')

    start = max(0, pos - context_chars)
    end = min(len(safe_text), pos + len(safe_keyword) + context_chars)
    snippet = safe_text[start:end]

    # Add ellipsis
    prefix = '...' if start > 0 else ''
    suffix = '...' if end < len(safe_text) else ''

    # Highlight keyword (case-insensitive replace in snippet)
    lower_snippet = snippet.lower()
    kw_pos = lower_snippet.find(lower_kw)
    if kw_pos >= 0:
        original_match = snippet[kw_pos:kw_pos + len(safe_keyword)]
        snippet = snippet[:kw_pos] + f'<mark>{original_match}</mark>' + snippet[kw_pos + len(safe_keyword):]

    return prefix + snippet + suffix


def _find_matched_field(step, keyword):
    """Determine which field matched the keyword."""
    kw = keyword.lower()
    if step.description and kw in step.description.lower():
        return 'description', step.description
    if step.notes and kw in step.notes.lower():
        return 'notes', step.notes
    if step.solution and kw in step.solution.lower():
        return 'solution', step.solution
    return 'description', step.description or ''


@api_search_bp.route('/', methods=['GET'])
def search():
    q = request.args.get('q', '').strip()
    field = request.args.get('field', 'all')

    if not q:
        return jsonify({'error': '请输入搜索关键词'}), 400

    escaped_q = _escape_like(q)
    like_pattern = f'%{escaped_q}%'

    # Build query with joins
    query = Step.query.join(Flow).join(Product)

    # Build field filter
    if field == 'description':
        query = query.filter(Step.description.like(like_pattern))
    elif field == 'notes':
        query = query.filter(Step.notes.like(like_pattern))
    elif field == 'solution':
        query = query.filter(Step.solution.like(like_pattern))
    else:  # all
        query = query.filter(or_(
            Step.description.like(like_pattern),
            Step.notes.like(like_pattern),
            Step.solution.like(like_pattern),
        ))

    steps = query.order_by(Product.name, Flow.name, Step.order).limit(50).all()

    results = []
    for step in steps:
        flow = step.flow
        product = flow.product

        if field == 'all':
            matched_field, matched_text = _find_matched_field(step, q)
        else:
            matched_field = field
            matched_text = getattr(step, field) or ''

        results.append({
            'step_id': step.id,
            'step_order': step.order,
            'flow_id': flow.id,
            'flow_name': flow.name,
            'product_id': product.id,
            'product_name': product.name,
            'matched_field': matched_field,
            'matched_text': _make_snippet(matched_text, q),
            'description': step.description,
            'score': step.score,
        })

    return jsonify({
        'query': q,
        'field': field,
        'total': len(results),
        'results': results,
    })
