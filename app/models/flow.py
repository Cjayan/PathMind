import uuid as _uuid
from datetime import datetime, timezone
from app.extensions import db


class Flow(db.Model):
    __tablename__ = 'flows'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False,
                     default=lambda: str(_uuid.uuid4()))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='recording')  # recording / completed
    ai_summary = db.Column(db.Text, nullable=True)
    exported_at = db.Column(db.DateTime, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_pinned = db.Column(db.Boolean, default=False)
    mark_color = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    steps = db.relationship('Step', backref='flow', lazy=True,
                            cascade='all, delete-orphan', order_by='Step.order')

    def to_dict(self, include_steps=False):
        data = {
            'id': self.id,
            'uuid': self.uuid,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'name': self.name,
            'status': self.status,
            'has_summary': bool(self.ai_summary),
            'step_count': len(self.steps),
            'average_score': self._average_score(),
            'sort_order': self.sort_order,
            'is_pinned': self.is_pinned or False,
            'mark_color': self.mark_color,
            'exported_at': self.exported_at.isoformat() if self.exported_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_steps:
            data['steps'] = [s.to_dict() for s in self.steps]
            data['ai_summary'] = self.ai_summary
        return data

    def _average_score(self):
        scores = [s.score for s in self.steps if s.score is not None]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 1)
