# debt_agent.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import math

app = FastAPI(title="Debt-Free Manager (Simple)")

# serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory storage (simple) — persisted only while service runs.
# For production, switch to DB (Firestore / Mongo / Postgres)
DB = {
    "incomes": [],
    "expenses": [],
    "debts": []
}

class DebtIn(BaseModel):
    name: str
    balance: float = Field(gt=0)
    apr: float = Field(ge=0)
    min_payment: float = Field(gt=0)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Render single page app
    return templates.TemplateResponse("index.html", {"request": request})

# API endpoints used by frontend
@app.get("/api/status")
def status():
    monthly_income = sum(i["amount"] for i in DB["incomes"])
    fixed_expenses = sum(e["amount"] for e in DB["expenses"])
    available_for_debt = monthly_income - fixed_expenses
    total_debt = round(sum(d["balance"] for d in DB["debts"]),2)
    return {"monthly_income": monthly_income, "fixed_expenses": fixed_expenses,
            "available_for_debt": round(available_for_debt,2), "total_debt": total_debt,
            "debts_count": len(DB["debts"])}

@app.post("/api/income")
def add_income(item: dict):
    DB["incomes"].append({"name": item.get("name","income"), "amount": float(item.get("amount",0))})
    return {"ok": True, "incomes": DB["incomes"]}

@app.post("/api/expense")
def add_expense(item: dict):
    DB["expenses"].append({"name": item.get("name","expense"), "amount": float(item.get("amount",0))})
    return {"ok": True, "expenses": DB["expenses"]}

@app.post("/api/debt")
def add_debt(item: DebtIn):
    DB["debts"].append({"id": len(DB["debts"])+1,
                        "name": item.name,
                        "balance": round(item.balance,2),
                        "apr": item.apr,
                        "min_payment": round(item.min_payment,2)})
    return {"ok": True, "debts": DB["debts"]}

@app.get("/api/debts")
def list_debts():
    return {"debts": DB["debts"]}

@app.post("/api/plan")
def plan(payload: dict):
    """
    payload example:
    {
      "method": "snowball" or "avalanche",
      "extra_payment": 5000,
      "months_limit": 120
    }
    """
    method = payload.get("method","snowball")
    extra = float(payload.get("extra_payment",0))
    months_limit = int(payload.get("months_limit",120))

    debts = [d.copy() for d in DB["debts"]]
    if not debts:
        return JSONResponse({"error":"No debts added."}, status_code=400)

    if method == "snowball":
        debts.sort(key=lambda x: x["balance"])
    else: # avalanche
        debts.sort(key=lambda x: -float(x["apr"]))

    # simulation (monthly)
    monthly_income = sum(i["amount"] for i in DB["incomes"])
    fixed_expenses = sum(e["amount"] for e in DB["expenses"])
    pool = max(0.0, monthly_income - fixed_expenses)
    if pool <= 0 and extra <= 0:
        return JSONResponse({"error":"No available money for debt payments. Add income or reduce expenses."}, status_code=400)

    months = []
    total_paid = 0.0
    month = 0
    while month < months_limit:
        month += 1
        monthly_pool = pool + extra
        # apply interest first
        active = [d for d in debts if d["balance"] > 0.009]
        if not active:
            break
        for d in active:
            monthly_rate = d["apr"] / 100.0 / 12.0
            interest = d["balance"] * monthly_rate
            d["balance"] = round(d["balance"] + interest, 10)
        # pay minimums first (or scale down if not enough)
        active = [d for d in debts if d["balance"] > 0.009]
        min_sum = sum(d["min_payment"] for d in active)
        factor = 1.0
        if monthly_pool < min_sum and min_sum > 0:
            factor = monthly_pool / min_sum
        payments = []
        month_paid = 0.0
        for d in active:
            pay = round(d["min_payment"] * factor,2)
            pay = min(pay, d["balance"])
            d["balance"] = round(d["balance"] - pay,2)
            payments.append({"debt_id": d["id"], "name": d["name"], "type":"min", "amount": pay})
            month_paid += pay
            monthly_pool -= pay
        # extra to target debt based on method
        active = sorted([d for d in debts if d["balance"] > 0.009],
                        key=(lambda x: x["balance"]) if method=="snowball" else (lambda x: -x["apr"]))
        while monthly_pool > 0.009 and active:
            target = active[0]
            pay = round(min(monthly_pool, target["balance"]),2)
            if pay < 0.01:
                break
            target["balance"] = round(target["balance"] - pay,2)
            payments.append({"debt_id": target["id"], "name": target["name"], "type":"extra", "amount": pay})
            month_paid += pay
            monthly_pool -= pay
            active = sorted([d for d in debts if d["balance"] > 0.009],
                            key=(lambda x: x["balance"]) if method=="snowball" else (lambda x: -x["apr"]))
        remaining = round(sum(d["balance"] for d in debts),2)
        months.append({"month": month, "payments": payments, "paid": round(month_paid,2), "remaining": remaining})
        total_paid += month_paid
        if remaining <= 0.01:
            break

    return {"months": months, "total_months": len(months), "total_paid": round(total_paid,2)}

# simple endpoints to clear DB (dev)
@app.post("/api/clear")
def clear_all():
    DB["incomes"].clear()
    DB["expenses"].clear()
    DB["debts"].clear()
    return {"ok": True}
