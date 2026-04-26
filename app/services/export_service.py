import json
import logging
import os
import shutil
from datetime import datetime, timezone
from app.extensions import db

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, obsidian_config):
        self.vault_path = obsidian_config.get('vault_path', '')
        self.products_folder = obsidian_config.get('products_folder', 'Products')

    def _get_products_dir(self):
        return os.path.join(self.vault_path, self.products_folder)

    def export_flow(self, flow):
        """Export a flow to Obsidian vault as Markdown files."""
        from flask import current_app

        product_name = flow.product.name
        flow_name = flow.name
        steps = flow.steps

        # Build directory structure
        products_dir = self._get_products_dir()
        product_dir = os.path.join(products_dir, product_name)
        flow_dir = os.path.join(product_dir, flow_name)
        os.makedirs(flow_dir, exist_ok=True)

        # Clean up old image files from flow directory (from previous exports)
        for f in os.listdir(flow_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                os.remove(os.path.join(flow_dir, f))

        # Copy images into attachments subfolder to avoid duplicate names
        upload_dir = current_app.config['UPLOAD_DIR']
        attachments_dir = os.path.join(flow_dir, 'attachments')
        os.makedirs(attachments_dir, exist_ok=True)
        image_files = {}
        for step in steps:
            if step.image_path:
                src = os.path.join(upload_dir, step.image_path)
                if os.path.exists(src):
                    dest_name = f"step_{step.order:02d}.png"
                    dest = os.path.join(attachments_dir, dest_name)
                    shutil.copy2(src, dest)
                    image_files[step.id] = dest_name

        # Generate individual step markdown files
        for i, step in enumerate(steps):
            next_step = steps[i + 1] if i + 1 < len(steps) else None
            is_last = (i == len(steps) - 1)
            step_md = self._generate_step_markdown(
                step, flow, image_files.get(step.id), next_step, is_last
            )
            step_md_name = f"step_{step.order:02d}.md"
            step_md_path = os.path.join(flow_dir, step_md_name)
            with open(step_md_path, 'w', encoding='utf-8') as f:
                f.write(step_md)

        # Generate flow markdown (overview that links to first step)
        flow_md = self._generate_flow_markdown(flow, steps, image_files)
        flow_md_path = os.path.join(flow_dir, f"{flow_name}_路径.md")
        with open(flow_md_path, 'w', encoding='utf-8') as f:
            f.write(flow_md)

        # Generate AI summary markdown if available
        if flow.ai_summary:
            summary_md = self._generate_summary_markdown(flow)
            summary_md_path = os.path.join(flow_dir, f"{flow_name}_总结.md")
            with open(summary_md_path, 'w', encoding='utf-8') as f:
                f.write(summary_md)

        # Update product overview
        self.update_product_overview(flow.product)

        # Export RAG metadata (isolated — failure does not affect MD export)
        try:
            self._export_rag_metadata(flow, flow_dir)
            self._update_global_rag_index()
        except Exception as e:
            logger.warning('RAG metadata export failed: %s', e)

        # Update exported_at
        flow.exported_at = datetime.now(timezone.utc)
        db.session.commit()

        return {
            'message': f'流程 "{flow_name}" 已导出到 Obsidian',
            'path': flow_dir,
        }

    def _generate_flow_markdown(self, flow, steps, image_files):
        """Generate the main flow markdown content (overview linking to steps)."""
        product_name = flow.product.name
        flow_name = flow.name
        now = datetime.now().strftime('%Y-%m-%d')

        scores = [s.score for s in steps if s.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        # YAML frontmatter
        md = "---\n"
        md += f'product: "{product_name}"\n'
        md += f'flow: "{flow_name}"\n'
        md += f'date: "{now}"\n'
        md += f"total_steps: {len(steps)}\n"
        md += f"average_score: {avg_score}\n"
        md += f'status: "{flow.status}"\n'
        md += "tags:\n"
        md += f"  - product/{product_name}\n"
        md += f"  - flow/{flow_name}\n"
        md += "  - type/usage-path\n"
        md += "---\n\n"

        # Header with link to product overview (upstream)
        md += f"# {flow_name}\n\n"
        stars = self._score_stars(avg_score)
        md += f"> **产品**: [[{product_name}_概览|{product_name}]]\n"
        md += f"> **记录日期**: {now}\n"
        md += f"> **总步骤**: {len(steps)} 步\n"
        md += f"> **平均体验评分**: {avg_score} / 10\n"
        md += "\n---\n\n"

        # Steps list (plain text, no [[ ]] links to keep graph linear)
        md += "## 操作步骤\n\n"
        for step in steps:
            score_str = f" ({step.score}/10)" if step.score is not None else ""
            solved = " ✅" if step.solution else ""
            md += f"1. 步骤 {step.order}: {step.description or '(无描述)'}{score_str}{solved}\n"
        md += "\n"

        # Only link to first step (graph chain: flow → step_01)
        if steps:
            first_step = f"step_{steps[0].order:02d}"
            md += f"**开始**: [[{first_step}|进入步骤 1 →]]\n\n"

        return md

    def _generate_step_markdown(self, step, flow, image_file, next_step, is_last):
        """Generate markdown for an individual step with full details."""
        flow_name = flow.name
        now = datetime.now().strftime('%Y-%m-%d')

        # YAML frontmatter
        md = "---\n"
        md += f'flow: "{flow_name}"\n'
        md += f"step: {step.order}\n"
        if step.score is not None:
            md += f"score: {step.score}\n"
        md += f'date: "{now}"\n'
        md += "tags:\n"
        md += f"  - flow/{flow_name}\n"
        md += "  - type/step\n"
        md += "---\n\n"

        # Title
        md += f"# 步骤 {step.order}: {step.description or '(无描述)'}\n\n"
        md += f"> **所属流程**: {flow_name}\n\n"

        # Image (from attachments subfolder)
        if image_file:
            md += f"![[attachments/{image_file}]]\n\n"

        # Details
        md += "## 详细信息\n\n"
        md += f"- **描述**: {step.description or '(无描述)'}\n"
        if step.score is not None:
            md += f"- **体验评分**: {step.score}/10\n"
        if step.notes:
            md += f"- **备注**: {step.notes}\n"
        if step.solution:
            md += f"- **解决方案**: {step.solution}\n"
        if step.ai_interaction or step.ai_description or step.ai_experience or step.ai_improvement:
            md += "\n### AI 评审意见\n\n"
            if step.ai_interaction:
                md += f"- **互动预测**: {step.ai_interaction}\n"
            elif step.ai_description:
                md += f"- **界面描述**: {step.ai_description}\n"
            if step.ai_experience:
                md += f"- **体验感受**: {step.ai_experience}\n"
            if step.ai_improvement:
                md += f"- **改进建议**: {step.ai_improvement}\n"
        md += "\n---\n\n"

        # Navigation: link to next step or summary (builds the chain)
        if next_step:
            next_page = f"step_{next_step.order:02d}"
            md += f"**下一步**: [[{next_page}|步骤 {next_step.order}: {next_step.description or '(无描述)'}]]\n"
        elif is_last and flow.ai_summary:
            md += f"**查看总结**: [[{flow_name}_总结]]\n"

        return md

    def _generate_summary_markdown(self, flow):
        """Generate the AI summary markdown content."""
        product_name = flow.product.name
        flow_name = flow.name
        now = datetime.now().isoformat()
        steps = flow.steps

        from app.config import config_manager
        ai_config = config_manager.get_ai_config()
        model = ai_config.get('model', 'unknown')

        md = "---\n"
        md += f'product: "{product_name}"\n'
        md += f'flow: "{flow_name}"\n'
        md += 'type: "ai-summary"\n'
        md += f'generated_at: "{now}"\n'
        md += f'model: "{model}"\n'
        md += "tags:\n"
        md += f"  - product/{product_name}\n"
        md += f"  - flow/{flow_name}\n"
        md += "  - type/ai-summary\n"
        md += "---\n\n"

        md += f"# {flow_name} - 总结\n\n"
        # Plain text back reference (no [[ ]] to keep graph linear)
        md += f"> **所属流程**: {flow_name}\n"
        md += "\n"
        md += flow.ai_summary or "(无总结内容)"
        md += "\n"

        return md

    def update_product_overview(self, product):
        """Create or update the product overview markdown file."""
        products_dir = self._get_products_dir()
        product_dir = os.path.join(products_dir, product.name)
        os.makedirs(product_dir, exist_ok=True)

        overview_path = os.path.join(product_dir, f"{product.name}_概览.md")

        md = "---\n"
        md += 'type: "product-overview"\n'
        md += f'product: "{product.name}"\n'
        md += "tags:\n"
        md += f"  - product/{product.name}\n"
        md += "  - type/product\n"
        md += "---\n\n"

        md += f"# {product.name}\n\n"
        if product.description:
            md += f"{product.description}\n\n"

        md += "## 已记录的使用流程\n\n"

        for flow in product.flows:
            avg = flow._average_score()
            score_str = f"平均 {avg}/10" if avg else "未评分"
            # Only link to flow page (graph chain: product → flow → steps → summary)
            link = f"[[{flow.name}/{flow.name}_路径|{flow.name}]]"
            md += f"- {link} ({len(flow.steps)}步, {score_str})\n"

        with open(overview_path, 'w', encoding='utf-8') as f:
            f.write(md)

        # Update product RAG document (isolated)
        try:
            self._update_product_rag(product, product_dir)
        except Exception:
            pass

    @staticmethod
    def _score_stars(score):
        if score is None or score == 0:
            return ""
        full = int(round(score))
        return "⭐" * full

    # ── RAG metadata helpers ──────────────────────────────────────────

    @staticmethod
    def _build_full_text(flow, steps, avg_score):
        """Concatenate flow content into natural-language text for embedding."""
        product_name = flow.product.name
        parts = [
            f'产品「{product_name}」的使用流程「{flow.name}」，'
            f'共{len(steps)}步，平均体验评分{avg_score or 0}/10。'
        ]
        for step in steps:
            seg = f'第{step.order}步：{step.description or "(无描述)"}。'
            if step.score is not None:
                seg += f'评分{step.score}/10。'
            if step.notes:
                seg += f'备注：{step.notes}。'
            if step.solution:
                seg += f'解决方案：{step.solution}。'
            if step.ai_interaction:
                seg += f'AI互动预测：{step.ai_interaction}。'
            if step.ai_experience:
                seg += f'AI体验感受：{step.ai_experience}。'
            if step.ai_improvement:
                seg += f'AI改进建议：{step.ai_improvement}。'
            # Truncate single-step text to 200 chars
            if len(seg) > 200:
                seg = seg[:197] + '...'
            parts.append(seg)
        if flow.ai_summary:
            summary = flow.ai_summary[:500]
            parts.append(f'流程总结：{summary}')
        return '\n'.join(parts)

    @staticmethod
    def _build_tags(flow, avg_score):
        """Generate semantic tags for RAG filtering."""
        tags = [
            f'product:{flow.product.name}',
            f'flow:{flow.name}',
            f'status:{flow.status}',
        ]
        if avg_score is not None:
            if avg_score >= 8:
                tags.append('score:high')
            elif avg_score >= 5:
                tags.append('score:medium')
            else:
                tags.append('score:low')
        if len(flow.steps) > 10:
            tags.append('complexity:high')
        if flow.ai_summary:
            tags.append('has_summary')
        return tags

    def _build_flow_document(self, flow):
        """Build the complete flow-level RAG document dict."""
        steps = flow.steps
        product = flow.product
        scores = [s.score for s in steps if s.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        now = datetime.now(timezone.utc).isoformat()

        steps_data = []
        for step in steps:
            has_image = bool(step.image_path)
            step_doc = {
                'uuid': step.uuid,
                'order': step.order,
                'description': step.description or '',
                'score': step.score,
                'notes': step.notes or '',
                'solution': step.solution or '',
                'has_image': has_image,
                'image_ref': f'attachments/step_{step.order:02d}.png' if has_image else None,
                'ai_review': {
                    'interaction': step.ai_interaction or '',
                    'experience': step.ai_experience or '',
                    'improvement': step.ai_improvement or '',
                },
            }
            steps_data.append(step_doc)

        return {
            '$schema': 'rag-flow-v1',
            'document_id': flow.uuid,
            'document_type': 'product-usage-flow',
            'version': now,
            'product': {
                'uuid': product.uuid,
                'name': product.name,
                'description': product.description or '',
            },
            'flow': {
                'uuid': flow.uuid,
                'name': flow.name,
                'status': flow.status,
                'step_count': len(steps),
                'average_score': avg_score,
                'created_at': flow.created_at.isoformat() if flow.created_at else None,
                'updated_at': flow.updated_at.isoformat() if flow.updated_at else None,
            },
            'steps': steps_data,
            'ai_summary': flow.ai_summary or '',
            'tags': self._build_tags(flow, avg_score),
            'full_text': self._build_full_text(flow, steps, avg_score),
        }

    def _export_rag_metadata(self, flow, flow_dir):
        """Write flow.json RAG document to {flow_dir}/.rag/."""
        rag_dir = os.path.join(flow_dir, '.rag')
        os.makedirs(rag_dir, exist_ok=True)
        doc = self._build_flow_document(flow)
        rag_path = os.path.join(rag_dir, 'flow.json')
        with open(rag_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    def _update_product_rag(self, product, product_dir):
        """Write product.json RAG aggregation to {product_dir}/.rag/."""
        rag_dir = os.path.join(product_dir, '.rag')
        os.makedirs(rag_dir, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        flows_summary = []
        all_scores = []
        total_steps = 0
        completed = 0
        recording = 0

        for fl in product.flows:
            scores = [s.score for s in fl.steps if s.score is not None]
            avg = round(sum(scores) / len(scores), 1) if scores else None
            if avg is not None:
                all_scores.append(avg)
            total_steps += len(fl.steps)
            if fl.status == 'completed':
                completed += 1
            else:
                recording += 1
            flows_summary.append({
                'uuid': fl.uuid,
                'name': fl.name,
                'status': fl.status,
                'step_count': len(fl.steps),
                'average_score': avg,
                'has_summary': bool(fl.ai_summary),
                'rag_path': f'{fl.name}/.rag/flow.json',
            })

        overall_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

        # Build product full_text
        ft_parts = [f'产品「{product.name}」概览。']
        if product.description:
            ft_parts.append(product.description)
        ft_parts.append(f'共{len(product.flows)}条使用流程，合计{total_steps}个步骤。')
        for fs in flows_summary:
            score_str = f'平均评分{fs["average_score"]}/10' if fs['average_score'] else '未评分'
            ft_parts.append(f'流程「{fs["name"]}」：{fs["step_count"]}步，{score_str}。')

        doc = {
            '$schema': 'rag-product-v1',
            'document_id': product.uuid,
            'document_type': 'product-overview',
            'version': now,
            'product': {
                'uuid': product.uuid,
                'name': product.name,
                'description': product.description or '',
            },
            'flows_summary': flows_summary,
            'statistics': {
                'total_flows': len(product.flows),
                'total_steps': total_steps,
                'overall_average_score': overall_avg,
                'completed_flows': completed,
                'recording_flows': recording,
            },
            'tags': [f'product:{product.name}'],
            'full_text': '\n'.join(ft_parts),
        }

        rag_path = os.path.join(rag_dir, 'product.json')
        with open(rag_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    def _update_global_rag_index(self):
        """Write index.json global RAG discovery index to {vault_path}/.rag/."""
        from app.models.product import Product

        rag_dir = os.path.join(self.vault_path, '.rag')
        os.makedirs(rag_dir, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        products_data = []
        total_flows = 0
        total_steps = 0

        for product in Product.query.all():
            flows_data = []
            for fl in product.flows:
                total_steps += len(fl.steps)
                flows_data.append({
                    'uuid': fl.uuid,
                    'name': fl.name,
                    'rag_path': f'{self.products_folder}/{product.name}/{fl.name}/.rag/flow.json',
                })
            total_flows += len(product.flows)
            products_data.append({
                'uuid': product.uuid,
                'name': product.name,
                'flow_count': len(product.flows),
                'rag_path': f'{self.products_folder}/{product.name}/.rag/product.json',
                'flows': flows_data,
            })

        doc = {
            '$schema': 'rag-index-v1',
            'version': now,
            'generated_at': now,
            'products': products_data,
            'statistics': {
                'total_products': len(products_data),
                'total_flows': total_flows,
                'total_steps': total_steps,
            },
        }

        index_path = os.path.join(rag_dir, 'index.json')
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
