import json
import httpx


class AIService:
    def __init__(self, config):
        self.base_url = config.get('base_url', 'https://api.openai.com/v1').rstrip('/')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'gpt-4o')
        self.max_tokens = config.get('max_tokens', 4096)
        self.temperature = config.get('temperature', 0.7)

    def _is_omni_model(self):
        return 'omni' in self.model.lower()

    def _build_text_content(self, text):
        """Build content field: array for Omni, string for standard."""
        if self._is_omni_model():
            return [{"type": "text", "text": text}]
        return text

    def _call_chat(self, messages, max_tokens=None, with_image=False):
        """Send a chat completion request."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        if self._is_omni_model():
            body["output_modalities"] = ["text"]
        else:
            body["max_tokens"] = max_tokens or self.max_tokens
            body["temperature"] = self.temperature

        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=body)

        if resp.status_code != 200:
            error_detail = resp.text
            try:
                error_json = resp.json()
                error_detail = error_json.get('error', {}).get('message', resp.text)
            except Exception:
                pass
            raise Exception(f"API请求失败 ({resp.status_code}): {error_detail}")

        data = resp.json()
        return data['choices'][0]['message']['content']

    def analyze_screenshot(self, image_base64, context=None):
        """Analyze a screenshot and return description suggestions."""
        context = context or {}
        product_name = context.get('product_name', '未知产品')
        flow_name = context.get('flow_name', '未知流程')
        step_order = context.get('step_order', '?')
        previous_steps = context.get('previous_steps', '')

        system_prompt = (
            "你是一个产品体验分析助手，擅长分析UI截图。"
            "请用中文回复。你的任务是帮助用户记录产品使用路径。"
        )

        user_text = (
            f"产品: {product_name}\n"
            f"流程: {flow_name}\n"
            f"当前是第 {step_order} 步\n"
        )
        if previous_steps:
            user_text += f"前面步骤摘要:\n{previous_steps}\n"
        user_text += (
            "\n请分析这张截图，给出:\n"
            "1. **页面描述**: 简洁描述当前页面内容和用户所处的操作阶段\n"
            "2. **关键UI元素**: 列出页面上的关键交互元素\n"
            "3. **建议步骤描述**: 用一句话描述用户在这一步的操作（适合作为步骤标题）\n"
            "\n请以JSON格式返回，包含 description, ui_elements(数组), suggested_title 三个字段。"
        )

        if self._is_omni_model():
            # LongCat Omni format: content is array, image uses input_image type
            user_content = [
                {
                    "type": "input_image",
                    "input_image": {
                        "type": "base64",
                        "data": [f"data:image/png;base64,{image_base64}"]
                    }
                },
                {"type": "text", "text": user_text}
            ]
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": user_content}
            ]
        else:
            # Standard OpenAI vision format
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }}
                ]}
            ]

        content = self._call_chat(messages, with_image=True)

        try:
            text = content.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
                if text.endswith('```'):
                    text = text[:-3]
                text = text.strip()
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            result = {
                'description': content,
                'ui_elements': [],
                'suggested_title': '',
            }
        return result

    @staticmethod
    def _truncate_bullet_text(text, max_len=300):
        """按分点边界智能截断文本"""
        text = str(text).strip()
        if len(text) <= max_len:
            return text
        lines = text.split('\n')
        result = []
        total = 0
        for line in lines:
            if total + len(line) + (1 if result else 0) > max_len - 3:
                break
            result.append(line)
            total += len(line) + (1 if len(result) > 1 else 0)
        if not result:
            return text[:max_len - 3] + '...'
        return '\n'.join(result) + '\n...'

    def generate_step_comment(self, image_base64, context=None):
        """Generate structured comment for a single step."""
        context = context or {}
        product_name = context.get('product_name', '未知产品')
        flow_name = context.get('flow_name', '未知流程')
        step_order = context.get('step_order', '?')
        step_title = context.get('step_title', '')
        previous_steps = context.get('previous_steps', '')

        system_prompt = (
            "你是一位专业的产品体验评审专家，擅长从UI截图中分析用户体验质量。"
            "请基于截图和上下文信息，给出结构化的评审意见。你必须以JSON格式回复。"
            "每个文字字段必须使用分点描述格式，每个要点独占一行，以'• '开头。"
        )

        user_text = (
            f"产品: {product_name}\n"
            f"流程: {flow_name}\n"
            f"当前步骤: 第{step_order}步"
        )
        if step_title:
            user_text += f" - {step_title}"
        user_text += "\n"
        if previous_steps:
            user_text += f"前面步骤摘要:\n{previous_steps}\n"
        user_text += (
            "\n请分析这张截图，给出以下评审意见（严格以JSON格式返回）：\n\n"
            '1. "ai_interaction": 互动预测 - 识别界面上所有可交互的按钮、链接、输入框等元素，'
            '分点列出每个元素的名称和预测其点击后的功能/行为（不超过300字，每点以"• "开头）\n'
            '2. "ai_experience": 体验感受 - 从用户视角分点评价这个界面/步骤的体验质量，'
            '包括易用性、信息架构、视觉设计等方面（不超过300字，每点以"• "开头）\n'
            '3. "ai_improvement": 改进建议 - 分点提出具体可执行的改进方案'
            '（不超过300字，每点以"• "开头）\n'
            '4. "score": 体验评分 - 1到10的整数，10分为最佳。评分标准：\n'
            '   - 1-3: 严重体验问题，流程受阻\n'
            '   - 4-5: 明显可用性问题\n'
            '   - 6-7: 基本可用，有改进空间\n'
            '   - 8-9: 体验良好\n'
            '   - 10: 优秀体验\n\n'
            'JSON字段: ai_interaction, ai_experience, ai_improvement, score'
        )

        if self._is_omni_model():
            user_content = [
                {
                    "type": "input_image",
                    "input_image": {
                        "type": "base64",
                        "data": [f"data:image/png;base64,{image_base64}"]
                    }
                },
                {"type": "text", "text": user_text}
            ]
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": user_content}
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }}
                ]}
            ]

        content = self._call_chat(messages, with_image=True)

        try:
            text = content.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
                if text.endswith('```'):
                    text = text[:-3]
                text = text.strip()
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            result = {
                'ai_interaction': content[:300],
                'ai_experience': '',
                'ai_improvement': '',
                'score': 5,
            }

        # Validate and truncate with bullet-point awareness
        for field in ('ai_interaction', 'ai_experience', 'ai_improvement'):
            val = result.get(field, '')
            if isinstance(val, list):
                val = '\n'.join(str(item) for item in val)
            result[field] = self._truncate_bullet_text(val, 300)
        try:
            score = int(result.get('score', 5))
            result['score'] = min(10, max(1, score))
        except (TypeError, ValueError):
            result['score'] = 5

        return result

    def generate_flow_summary(self, flow_data):
        """Generate a comprehensive summary for an entire flow."""
        product_name = flow_data['product_name']
        flow_name = flow_data['flow_name']
        steps = flow_data['steps']

        system_prompt = (
            "你是一个产品体验分析专家。请根据用户的完整操作流程记录生成一份详细的分析报告。"
            "报告使用Markdown格式，用中文撰写。"
        )

        steps_text = ""
        for s in steps:
            score_str = f"{s['score'] or '未评分'}/10" if s['score'] else "未评分"
            steps_text += (
                f"### 步骤 {s['order']}\n"
                f"- 描述: {s['description']}\n"
                f"- 体验评分: {score_str} ({s['score'] or '未评分'}/5)\n"
                f"- 备注: {s['notes'] or '无'}\n\n"
            )

        scores = [s['score'] for s in steps if s['score']]
        avg_score = round(sum(scores) / len(scores), 1) if scores else '无'

        user_text = (
            f"# 产品: {product_name}\n"
            f"# 流程: {flow_name}\n"
            f"# 步骤总数: {len(steps)}\n"
            f"# 平均体验评分: {avg_score}/10\n\n"
            f"## 详细步骤记录:\n\n{steps_text}\n"
            "请生成一份分析报告，包含以下章节:\n"
            "1. **流程概述** - 概括整个操作流程\n"
            "2. **关键发现** - 流程中的亮点和问题\n"
            "3. **痛点分析** - 体验不佳的环节及原因分析\n"
            "4. **评分趋势分析** - 各步骤评分的变化趋势和含义\n"
            "5. **改进建议** - 针对性的改进建议\n"
            "6. **统计摘要** - 用Markdown表格总结关键数据\n"
        )

        messages = [
            {"role": "system", "content": self._build_text_content(system_prompt)},
            {"role": "user", "content": self._build_text_content(user_text)}
        ]

        return self._call_chat(messages)

    def test_connection(self):
        """Test if the AI API is reachable."""
        messages = [
            {"role": "user", "content": self._build_text_content("请回复'连接成功'四个字。")}
        ]
        content = self._call_chat(messages, max_tokens=20)
        return {
            'success': True,
            'message': content,
            'model': self.model,
        }
