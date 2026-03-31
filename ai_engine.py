"""
Модуль интеллектуального анализа финансовых данных.

Реализует три функции:
  1. run_anomaly_detection  — обнаружение аномальных транзакций
  2. run_forecast           — прогноз баланса на следующие 3 месяца
  3. run_recommendations    — рекомендации по бюджетным лимитам
"""

import math
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any

from db import SessionLocal, Transaction, Category, Budget, AIForecast, AIAnomaly, AIBudgetRecommendation


def run_anomaly_detection(user_id: int) -> Dict[str, Any]:
    """
    Обнаруживает аномальные транзакции методом Z-score по каждой категории.

    Алгоритм:
      - Для каждой категории расходов вычисляются среднее (μ) и
        стандартное отклонение (σ) по суммам транзакций.
      - Транзакция считается аномальной, если её Z-score > 2.0
        (т.е. сумма выше μ + 2σ — редкое событие для данной категории).
      - anomaly_score нормируется в диапазон [0, 1]: score = min(z / 6, 1.0).
      - Дополнительно: если в один день в одной категории две транзакции
        с одинаковой суммой — это возможный дубль (score 0.75).

    Для надёжности требуется минимум 3 транзакции в категории.
    Предыдущие результаты анализа для данного пользователя сбрасываются
    перед каждым запуском.
    """
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()

        if not transactions:
            return {"detected": 0, "message": "Нет транзакций для анализа"}

        tx_ids = [tx.id for tx in transactions]

        db.query(AIAnomaly).filter(AIAnomaly.transaction_id.in_(tx_ids)).delete(synchronize_session=False)
        for tx in transactions:
            tx.is_anomaly = False
            tx.anomaly_score = 0.0
        db.commit()

        by_category: Dict[int, list] = defaultdict(list)
        for tx in transactions:
            if tx.type == "expense":
                by_category[tx.category_id].append(tx)

        anomalies_to_write = []

        for category_id, cat_txs in by_category.items():
            if len(cat_txs) < 3:
                continue

            amounts = [tx.amount for tx in cat_txs]
            mean = sum(amounts) / len(amounts)
            variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
            std = math.sqrt(variance) if variance > 0 else 0

            if std == 0:
                continue

            for tx in cat_txs:
                z = (tx.amount - mean) / std
                if z > 1.5:
                    score = round(min(z / 5.0, 1.0), 4)
                    reason = (
                        f"Сумма {tx.amount:.2f} ₽ превышает среднее по категории "
                        f"({mean:.2f} ₽) на {z:.1f} стандартных отклонений (σ={std:.2f})"
                    )
                    tx.is_anomaly = True
                    tx.anomaly_score = score
                    anomalies_to_write.append((tx.id, score, reason))

        sorted_txs = sorted(transactions, key=lambda t: (t.transaction_date, t.id))
        seen = set()
        for i, tx in enumerate(sorted_txs):
            for prev in sorted_txs[max(0, i - 15):i]:
                key = (prev.category_id, round(prev.amount, 2), prev.transaction_date)
                if (
                    prev.category_id == tx.category_id
                    and abs(prev.amount - tx.amount) < 0.01
                    and prev.transaction_date == tx.transaction_date
                    and tx.id not in seen
                ):
                    score = 0.75
                    reason = (
                        f"Возможная дублирующая транзакция: {tx.amount:.2f} ₽ "
                        f"в той же категории в тот же день ({tx.transaction_date})"
                    )
                    if not tx.is_anomaly:
                        tx.is_anomaly = True
                        tx.anomaly_score = score
                        anomalies_to_write.append((tx.id, score, reason))
                    seen.add(tx.id)
                    break

        db.commit()

        tx_map = {tx.id: tx for tx in transactions}
        cat_ids = {tx.category_id for tx in transactions}
        categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
        cat_name_map = {c.id: c.name for c in categories}

        anomaly_records = []
        for tx_id, score, reason in anomalies_to_write:
            db.add(AIAnomaly(
                transaction_id=tx_id,
                anomaly_score=score,
                reason=reason,
                detected_at=datetime.utcnow(),
            ))
            tx = tx_map[tx_id]
            anomaly_records.append({
                "transaction_id": tx_id,
                "amount": tx.amount,
                "transaction_date": tx.transaction_date,
                "category_name": cat_name_map.get(tx.category_id, "Неизвестно"),
                "transaction_type": tx.type,
                "description": tx.description,
                "anomaly_score": score,
                "reason": reason,
            })
        db.commit()

        anomaly_records.sort(key=lambda x: x["anomaly_score"], reverse=True)

        return {
            "detected": len(anomaly_records),
            "total_analyzed": len(transactions),
            "anomalies": anomaly_records,
            "message": (
                f"Обнаружено {len(anomaly_records)} аномальных транзакций "
                f"из {len(transactions)} проанализированных"
            ),
        }
    finally:
        db.close()


def run_forecast(user_id: int) -> Dict[str, Any]:
    """
    Прогнозирует баланс на следующие 3 месяца.

    Алгоритм:
      - Транзакции группируются по месяцам (YYYY-MM) в доходы/расходы.
      - Берутся данные за последние 6 завершённых месяцев.
      - Вычисляются средние доходы и расходы за этот период.
      - Дополнительно считается линейный тренд изменения баланса
        по последним 3 месяцам: если баланс растёт — прогноз позитивнее,
        если падает — консервативнее.
      - Предыдущие прогнозы пользователя удаляются и заменяются новыми.
      - Требуется минимум 2 месяца исторических данных.
    """
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()

        if not transactions:
            return {"periods": 0, "message": "Нет транзакций для прогноза"}

        monthly: Dict[str, Dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        for tx in transactions:
            month_key = str(tx.transaction_date)[:7]
            if tx.type == "income":
                monthly[month_key]["income"] += tx.amount
            else:
                monthly[month_key]["expense"] += tx.amount

        sorted_months = sorted(monthly.keys())[-6:]

        if len(sorted_months) < 2:
            return {
                "periods": 0,
                "message": "Недостаточно данных: нужно минимум 2 месяца транзакций",
            }

        avg_income = sum(monthly[m]["income"] for m in sorted_months) / len(sorted_months)
        avg_expense = sum(monthly[m]["expense"] for m in sorted_months) / len(sorted_months)
        avg_balance = avg_income - avg_expense

        if len(sorted_months) >= 3:
            last3 = sorted_months[-3:]
            b_first = monthly[last3[0]]["income"] - monthly[last3[0]]["expense"]
            b_last = monthly[last3[-1]]["income"] - monthly[last3[-1]]["expense"]
            trend = (b_last - b_first) / 3
        else:
            trend = 0.0

        today = datetime.utcnow()
        forecast_periods = []
        for i in range(1, 4):
            m = today.month - 1 + i
            year = today.year + m // 12
            month = m % 12 + 1
            forecast_periods.append(f"{year}-{month:02d}")

        db.query(AIForecast).filter(AIForecast.user_id == user_id).delete()

        created = []
        for i, period in enumerate(forecast_periods):
            predicted = round(avg_balance + trend * (i + 1), 2)
            db.add(AIForecast(
                user_id=user_id,
                period=period,
                forecasted_balance=predicted,
                created_at=datetime.utcnow(),
            ))
            created.append({"period": period, "forecasted_balance": predicted})

        db.commit()

        return {
            "periods": len(created),
            "based_on_months": len(sorted_months),
            "avg_monthly_income": round(avg_income, 2),
            "avg_monthly_expense": round(avg_expense, 2),
            "monthly_trend": round(trend, 2),
            "forecasts": created,
            "message": f"Создано {len(created)} прогноза на основе {len(sorted_months)} месяцев данных",
        }
    finally:
        db.close()


def run_recommendations(user_id: int) -> Dict[str, Any]:
    """
    Генерирует рекомендации по бюджетным лимитам на основе реальных расходов.

    Алгоритм:
      - Анализируется период последних 3 завершённых месяцев.
      - Для каждой категории с установленным лимитом вычисляется
        средний расход и отношение к лимиту (ratio):
          * ratio > 0.9  → INCREASE: лимит слишком мал, предлагается +30%.
          * ratio < 0.5  → DECREASE: лимит избыточен, предлагается -30%.
      - Для категорий БЕЗ лимита, по которым были расходы в 2+ из 3 месяцев,
        генерируется рекомендация CREATE с предложенным лимитом = средний * 1.2.
      - Предыдущие рекомендации пользователя перезаписываются.
    """
    db = SessionLocal()
    try:
        expense_txs = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
        ).all()

        budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
        categories = db.query(Category).filter(
            Category.user_id == user_id,
            Category.type == "expense",
        ).all()
        cat_name: Dict[int, str] = {c.id: c.name for c in categories}

        today = datetime.utcnow()
        analysis_periods = []
        for i in range(1, 4):
            m = today.month - i
            year = today.year + (m - 1) // 12 if m < 1 else today.year
            month = ((m - 1) % 12) + 1
            analysis_periods.append(f"{year}-{month:02d}")

        spending: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for tx in expense_txs:
            period = str(tx.transaction_date)[:7]
            if period in analysis_periods:
                spending[tx.category_id][period] += tx.amount

        db.query(AIBudgetRecommendation).filter(
            AIBudgetRecommendation.user_id == user_id
        ).delete()

        items = []
        budgeted_ids = {b.category_id for b in budgets}

        for budget in budgets:
            cat_spending = [spending[budget.category_id].get(p, 0.0) for p in analysis_periods]
            months_active = sum(1 for s in cat_spending if s > 0)

            if months_active == 0:
                continue

            avg_spending = sum(cat_spending) / len(analysis_periods)
            ratio = avg_spending / budget.limit_amount if budget.limit_amount > 0 else 0
            name = cat_name.get(budget.category_id, f"категория #{budget.category_id}")

            if ratio > 0.9:
                proposed = round(budget.limit_amount * 1.3, 2)
                rec_type = "INCREASE"
                justification = (
                    f"Средние расходы по «{name}» за последние 3 месяца "
                    f"составляют {avg_spending:.0f} ₽ — это {ratio * 100:.0f}% "
                    f"от текущего лимита {budget.limit_amount:.0f} ₽. "
                    f"Рекомендуется увеличить лимит до {proposed:.0f} ₽."
                )
            elif ratio < 0.5:
                proposed = round(budget.limit_amount * 0.7, 2)
                rec_type = "DECREASE"
                justification = (
                    f"Средние расходы по «{name}» за последние 3 месяца "
                    f"составляют {avg_spending:.0f} ₽ — лишь {ratio * 100:.0f}% "
                    f"от лимита {budget.limit_amount:.0f} ₽. "
                    f"Можно снизить лимит до {proposed:.0f} ₽ для точного планирования."
                )
            else:
                continue

            rec = AIBudgetRecommendation(
                user_id=user_id,
                category_id=budget.category_id,
                recommendation_type=rec_type,
                current_limit=budget.limit_amount,
                proposed_limit=proposed,
                justification=justification,
                created_at=datetime.utcnow(),
            )
            db.add(rec)
            items.append({
                "category_name": name,
                "recommendation_type": rec_type,
                "current_limit": budget.limit_amount,
                "proposed_limit": proposed,
                "justification": justification,
            })

        for category in categories:
            if category.id in budgeted_ids:
                continue
            cat_spending = [spending[category.id].get(p, 0.0) for p in analysis_periods]
            months_with_spending = sum(1 for s in cat_spending if s > 0)
            if months_with_spending < 2:
                continue
            avg_spending = sum(cat_spending) / months_with_spending
            proposed = round(avg_spending * 1.2, 2)
            justification = (
                f"Обнаружены регулярные расходы по «{category.name}» "
                f"в {months_with_spending} из 3 последних месяцев "
                f"(в среднем {avg_spending:.0f} ₽/мес). "
                f"Рекомендуется установить бюджетный лимит {proposed:.0f} ₽."
            )
            db.add(AIBudgetRecommendation(
                user_id=user_id,
                category_id=category.id,
                recommendation_type="CREATE",
                current_limit=None,
                proposed_limit=proposed,
                justification=justification,
                created_at=datetime.utcnow(),
            ))
            items.append({
                "category_name": category.name,
                "recommendation_type": "CREATE",
                "current_limit": None,
                "proposed_limit": proposed,
                "justification": justification,
            })

        db.commit()

        return {
            "recommendations_created": len(items),
            "analysis_periods": analysis_periods,
            "items": items,
            "message": f"Создано {len(items)} рекомендаций по бюджету",
        }
    finally:
        db.close()
