# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from typing import List

app = FastAPI(title="ЕГЭ 2026: профильная математика - тренажёр")

class Task(BaseModel):
    id: int
    topic: str
    question: str
    answer: float
    explanation: str  # подробное объяснение ошибки/решения
    tip: str          # подсказка

# Примеры задач можно расширять
TASKS: List[Task] = [
    Task(
        id=1,
        topic="Алгебра",
        question="Найдите корень уравнения: 2x - 3 = 7",
        answer=5.0,
        explanation="Правильно: x = 5. Уравнение линейное: перенесём 3 в правую часть: 2x = 10; x = 5.",
        tip="Соберите подобные члены и разделите на коэффициент перед x."
    ),
    Task(
        id=2,
        topic="Анализ",
        question="Найдите предел: lim_{x→0} (sin x)/x",
        answer=1.0,
        explanation="Известный предел sin x / x → 1 при x → 0.",
        tip="Используйте стандартный предел или экспонентный подход через серию Тейлора."
    ),
    Task(
        id=3,
        topic="Геометрия",
        question="Даны две параллельные прямые, расстояние между ними равно 5. Найдите площадь трапеции, образованной двумя пересекающимися диагоналями и боковыми сторонами, если высота трапеции 6.",
        answer=30.0,  # произвольный пример
        explanation="Площадь трапеции = ((a + b) / 2) * h. В примере сторонами являются основания, их сумма взята условно для демонстрации.",
        tip="Используйте формулу площади трапеции."
    ),
    Task(
        id=4,
        topic="Вероятность",
        question="Вероятность выпадения орла на честной монете: P(орёл) = ?",
        answer=0.5,
        explanation="Монета имеет два равновероятных исхода: орел и решка.",
        tip="Учитывайте число благоприятных исходов разделить на общее число исходов."
    ),
]

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<title>Тренажёр ЕГЭ 2026</title>
<style>
body { font-family: Arial, sans-serif; padding: 20px; background: #f5f7fa; }
.container { max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.1); }
h1 { color: #2c3e50; }
.task { border: 1px solid #e1e4e8; padding: 14px; border-radius: 6px; margin-bottom: 12px; }
.input { margin-top: 8px; }
.error { color: #c0392b; font-weight: bold; }
.ok { color: #27ae60; font-weight: bold; }
.explanation { margin-top: 8px; padding: 8px; background: #f0f4f8; border-radius: 6px; }
.btn { padding: 8px 12px; border: none; border-radius: 4px; background: #2d8cff; color: white; cursor: pointer; }
.btn.secondary { background: #95a5a6; }
</style>
</head>
<body>
<div class="container">
  <h1>Тренажёр: профильная математика ЕГЭ 2026</h1>
  <div id="tasks"></div>
</div>

<script>
const tasks = %TASKS%;
function render() {
  const container = document.getElementById('tasks');
  container.innerHTML = '';
  tasks.forEach(t => {
    const div = document.createElement('div');
    div.className = 'task';
    div.innerHTML = `
      <div><strong>Тема:</strong> ${t.topic}</div>
      <div><strong>Вопрос:</strong> ${t.question}</div>
      <div class="input">
        <input type="number" id="ans_${t.id}" placeholder="Ваш ответ" />
        <button class="btn" onclick="check(${t.id})">Проверить</button>
        <button class="btn secondary" onclick="hint(${t.id})">Подсказка</button>
      </div>
      <div id="result_${t.id}"></div>
      <div class="explanation" id="exp_${t.id}" style="display:none;">
        <strong>Объяснение:</strong> ${t.explanation}
      </div>
      <div class="explanation" id="tip_${t.id}" style="display:none;">
        <strong>Совет:</strong> ${t.tip}
      </div>
    `;
    container.appendChild(div);
  });
}
function check(id) {
  const t = tasks.find(x => x.id === id);
  const val = parseFloat(document.getElementById('ans_' + id).value);
  const res = document.getElementById('result_' + id);
  const exp = document.getElementById('exp_' + id);
  const tip = document.getElementById('tip_' + id);
  if (isNaN(val)) {
    res.innerHTML = '<span class="error">Введите число.</span>';
    exp.style.display = 'none';
    tip.style.display = 'none';
    return;
  }
  if (Math.abs(val - t.answer) < 1e-6) {
    res.innerHTML = '<span class="ok">Правильно!</span>';
  } else {
    res.innerHTML = '<span class="error">Неправильно.</span>';
  }
  exp.style.display = 'block';
  tip.style.display = 'block';
}
function hint(id){
  const t = tasks.find(x => x.id === id);
  const tip = document.getElementById('tip_' + id);
  tip.style.display = 'block';
}
window.onload = render;
</script>
</body>
</html>
"""

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Подставим задачи в HTML
    tasks_dicts = [t.dict() for t in TASKS]
    page = HTML_PAGE.replace("%TASKS%", str(tasks_dicts))
    return HTMLResponse(content=page, status_code=200)

@app.get("/api/tasks")
async def get_tasks():
    return [t.dict() for t in TASKS]

# Простая API для проверки ответа одного задания (на будущее)
class AnswerPayload(BaseModel):
    id: int
    answer: float

@app.post("/api/check")
async def api_check(payload: AnswerPayload):
    t = next((x for x in TASKS if x.id == payload.id), None)
    if t is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    correct = abs(payload.answer - t.answer) < 1e-6
    return {
        "id": t.id,
        "correct": correct,
        "provided": payload.answer,
        "expected": t.answer,
        "explanation": t.explanation,
        "tip": t.tip
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
