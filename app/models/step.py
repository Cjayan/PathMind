import uuid as _uuid
from datetime import datetime, timezone
from app.extensions import db


class Step(db.Model):
    __tablename__ = 'steps'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False,
                     default=lambda: str(_uuid.uuid4()))
    flow_id = db.Column(db.Integer, db.ForeignKey('flows.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    image_path = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, nullable=True)  # 1-10
    notes = db.Column(db.Text, nullable=True)
    ai_suggestion = db.Column(db.Text, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    ai_description = db.Column(db.Text, nullable=True)   # AI 界面描述 (旧版，保留兼容)
    ai_interaction = db.Column(db.Text, nullable=True)    # AI 互动预测
    ai_experience = db.Column(db.Text, nullable=True)     # AI 体验感受
    ai_improvement = db.Column(db.Text, nullable=True)    # AI 改进建议
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'flow_id': self.flow_id,
            'order': self.order,
            'image_path': self.image_path,
            'description': self.description,
            'score': self.score,
            'notes': self.notes,
            'ai_suggestion': self.ai_suggestion,
            'solution': self.solution,
            'ai_description': self.ai_description,
            'ai_interaction': self.ai_interaction,
            'ai_experience': self.ai_experience,
            'ai_improvement': self.ai_improvement,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
